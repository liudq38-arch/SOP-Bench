import asyncio
import fcntl
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.descriptive_v21 import CONFIG, FOLDER, ClientPool, digest


def public_frame(frame):
    return {k: frame[k] for k in ['frame_id', 'source_pts_s', 'source_frame_index']}


def video_payload(case, clip):
    return {'case_id': case['case_id'], 'view': case['view'], 'output_language': 'en', 'window_id': clip['clip_id'], 'target_interval_s': [clip['core_frames'][0]['source_pts_s'], clip['core_frames'][-1]['source_pts_s']], 'sampled_frames': [public_frame(f) for f in clip['video']['sampled_frames']], 'video_start_source_pts_s': clip['media_frames'][0]['source_pts_s'], 'video_time_mapping': 'source_pts_s = video-local time + video_start_source_pts_s; use manifest PTS and IDs', 'window_scope': 'Only describe the target core; overlap frames supply continuity. No before/after outside the original ATR target is supplied.'}


def compact_cards(cards):
    result = []
    for index, card in enumerate(cards):
        copy = dict(card)
        if index:
            copy.pop('scene_description', None)
        result.append(copy)
    return result


def gt_payload(case, clip):
    a, b = clip['core_frames'][0]['source_pts_s'], clip['core_frames'][-1]['source_pts_s']
    original_a = case['interval_s'][0]
    shared = case['shared_gt']
    context = [f for f in shared['atomic_context'] if f['source_id'].startswith(case['view'] + '_') and original_a + f['relative_start_s'] <= b and original_a + f['relative_end_s'] >= a]
    return {'atr_labels': shared['atr_labels'], 'target_hand': shared['target_hand'], 'annotation_interval_s': case['interval_s'], 'atomic_context': [{k: v for k, v in f.items() if k != 'source'} for f in context], 'normative_tool': None, 'normative_sequence': None, 'warning': 'Labels describe the annotation scope, not necessarily a visually recognizable error in each shorter clip.'}


async def process_case(pool, record):
    case = record['case']
    case_id = case['case_id']
    folder = FOLDER / 'runs' / case_id
    selection = CONFIG['pilot_selection']
    clip_index = selection['clip_indices'].get(case['pair_id'], selection['default_clip_index'])
    selected_clips = [record['clips'][clip_index]]
    frames = selected_clips[0]['core_frames']

    async def batch(index):
        target = frames[index:index + 8]
        reference = frames[max(0, index - 1):index]
        payload = {'case_id': case_id, 'view': case['view'], 'output_language': 'en', 'target_frames': [public_frame(f) for f in target], 'reference_frames': [public_frame(f) for f in reference]}
        path = folder / f'frames_{index:04d}.json'
        if path.exists():
            return read_json(path)
        try:
            response = await pool.call('describe_frames', payload, reference + target, images=reference + target, suffix=f'frames_{index:04d}')
            result = {'status': 'ok', 'cache_key': response['cache_key'], 'result': response['result']}
        except Exception as exc:
            result = {'status': 'error', 'error': str(exc), 'frame_ids': [f['frame_id'] for f in target]}
        save_json(path, result)
        return result

    batches = await asyncio.gather(*(batch(i) for i in range(0, len(frames), 8)))
    cards = {c['frame_id']: c for batch_result in batches if batch_result['status'] == 'ok' for c in batch_result['result']['cards']}
    save_jsonl(folder / 'frame_cards.jsonl', sorted(cards.values(), key=lambda c: c['source_pts_s']))

    async def clip_run(clip):
        path = folder / (clip['clip_id'] + '.json')
        if path.exists():
            return read_json(path)
        output = {'case_id': case_id, 'clip_id': clip['clip_id'], 'status': 'error', 'stages': {}}
        try:
            missing = [f['frame_id'] for f in clip['core_frames'] if f['frame_id'] not in cards]
            if missing:
                raise ValueError(f'run_v21:missing_cards:{missing}')
            payload = video_payload(case, clip)
            response = await pool.call('observe_video', payload, clip['video']['sampled_frames'], video=clip['video'], suffix=clip['clip_id'])
            observation = response['result']
            output['stages']['observe_video'] = response['cache_key']
            selected = [cards[f['frame_id']] for f in clip['core_frames']]
            evidence = dict(payload, visual_observation=observation, frame_cards=compact_cards(selected), annotation_gt=gt_payload(case, clip))
            response = await pool.call('describe_event', evidence, clip['media_frames'], video=clip['video'], suffix=clip['clip_id'], prompt_extra='This pilot supplies original GT separately, without an independent reconciliation call. Preserve visual/annotation distinctions yourself; any disagreement stays unresolved. Describe this core clip only, including all meaningful visible changes. Do not invent after-context. Keep atomic claims concise and their frame references specific. All frame cards were created from the actual original frames; video sampling may be sparser.')
            description = response['result']
            output['stages']['describe_event'] = response['cache_key']
            output['observation'] = observation
            output['description'] = description
            qa_payload = dict(payload, description=description, annotation_gt=gt_payload(case, clip), allowed_frame_manifest=[public_frame(f) for f in clip['media_frames']])
            response = await pool.call('generate_open_qa', qa_payload, clip['media_frames'], video=clip['video'], suffix=clip['clip_id'], prompt_extra='Generate the required full event_description question and at most ONE additional question for this pilot. The target scope is the core interval in target_interval_s. All claims must be scoped to supplied evidence. Do not answer about the entire original execution. Preserve uncertainty; no options.')
            output['stages']['generate_open_qa'] = response['cache_key']
            output['qa'] = response['result']
            audit_payload = dict(payload, description=description, qa=output['qa'], actual_audit_image_frames=[public_frame(f) for f in clip['media_frames']])
            claims = [c for item in output['qa']['items'] for c in item['claims']]
            requested = set(f for claim in claims for f in claim['frame_ids'])
            audit_images = [f for f in clip['media_frames'] if f['frame_id'] in requested]
            if len(audit_images) > 8:
                audit_images = [audit_images[round(i * (len(audit_images) - 1) / 7)] for i in range(8)]
            audit_payload['actual_audit_image_frames'] = [public_frame(f) for f in audit_images]
            audit_payload['audit_coverage_note'] = 'Only supplied video samples and attached images are directly inspected. References absent from both cannot be certified and must remain unverifiable. Do not assume text descriptions of other frames prove them.'
            actual_audit = {f['frame_id']: f for f in clip['video']['sampled_frames'] + audit_images}
            response = await pool.call('audit', audit_payload, list(actual_audit.values()), images=audit_images, video=clip['video'], suffix=clip['clip_id'])
            output['stages']['audit'] = response['cache_key']
            output['audit'] = response['result']
            output['audit_visible_frame_ids'] = sorted(actual_audit)
            output['status'] = 'completed_unvalidated'
        except Exception as exc:
            output['error'] = f'{type(exc).__name__}:{exc}'
        save_json(path, output)
        print(json.dumps({'clip_id': clip['clip_id'], 'status': output['status'], 'error': output.get('error')}), flush=True)
        return output

    clips = await asyncio.gather(*(clip_run(c) for c in selected_clips))
    description_sections = [s for c in clips if 'description' in c for s in c['description']['sections']]
    description_sections.sort(key=lambda s: s['source_interval_s'][0])
    result = {'case_id': case_id, 'view': case['view'], 'native_frames': len(frames), 'original_target_frames': len(record['frames']), 'valid_frame_cards': len(cards), 'frame_coverage': len(cards) / len(frames), 'original_target_frame_coverage': len(cards) / len(record['frames']), 'clips': clips, 'chronological_clip_descriptions': description_sections, 'assembly_method': 'Bounded core-clip pilot; no full original-event description claimed.', 'context_included': False, 'status': 'completed_unvalidated' if all(c['status'] == 'completed_unvalidated' for c in clips) else 'partial_or_failed'}
    save_json(folder / 'result.json', result)
    return result


async def main():
    records = read_jsonl(FOLDER / 'cases.jsonl')
    source_paths = ['impact_qa/descriptive_v21.py', 'scripts/prepare_descriptive_v21.py', 'scripts/run_descriptive_v21.py', 'configs/impact_qa/descriptive_v21_pilot.json', *CONFIG['prompts'].values(), CONFIG['few_shots'], CONFIG['schema']]
    frozen = {'source_hashes': {p: digest(ROOT / p) for p in source_paths}, 'cases_sha256': digest(FOLDER / 'cases.jsonl')}
    frozen_path = FOLDER / 'pilot_frozen.json'
    if frozen_path.exists() and read_json(frozen_path) != frozen:
        raise ValueError('run_v21:frozen_sources_changed')
    save_json(frozen_path, frozen)
    pool = ClientPool()
    started = time.monotonic()
    try:
        results = await asyncio.gather(*(process_case(pool, record) for record in records))
    finally:
        save_json(FOLDER / 'new_requests.json', pool.calls)
        await pool.close()
    save_jsonl(FOLDER / 'results.jsonl', results)
    summary = {'cases': len(results), 'native_frames': sum(r['native_frames'] for r in results), 'valid_frame_cards': sum(r['valid_frame_cards'] for r in results), 'clips': sum(len(r['clips']) for r in results), 'completed_clips': sum(c['status'] == 'completed_unvalidated' for r in results for c in r['clips']), 'elapsed_s': time.monotonic() - started, 'new_requests': len(pool.calls), 'max_actual_prompt_tokens': max((c.get('usage', {}).get('prompt_tokens', 0) for c in pool.calls if c.get('usage')), default=0), 'formal_release': False, 'independent_human_validation': False}
    save_json(FOLDER / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main())
