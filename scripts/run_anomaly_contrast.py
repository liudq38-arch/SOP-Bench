import argparse
import asyncio
from collections import Counter
import fcntl
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.anomaly_contrast import FOLDER, prepare
from impact_qa.common import fingerprint, read_json, save_json, save_jsonl
from impact_qa.mcq_grouped_media import prepare_window_media
from impact_qa.mcq_grouped_review import array, enum, obj
from impact_qa.structured_video_client import StructuredVideoPool


def schema(media):
    evidence = array(enum(f['frame_id'] for f in media['sampled_frames']), 0, 8)
    a, b = media['target_interval_frames']
    def segment(scope):
        frames = [f['frame_id'] for f in media['sampled_frames'] if scope == 'all' or scope == 'before' and f['source_frame_index'] < a or scope == 'target' and a <= f['source_frame_index'] < b or scope == 'after' and f['source_frame_index'] >= b]
        refs = array(enum(frames), 0, 8) if frames else array({'type': 'string'}, 0, 0)
        return obj({'description': {'type': 'string'}, 'evidence_frame_ids': refs})
    return obj({'target_hand_identity': enum(['clear', 'unclear']), 'before': segment('before'), 'target': segment('target'), 'other_hand_during_target': segment('target'), 'after': segment('after'), 'tool_contact_during_target': enum(['contact_visible', 'held_without_visible_contact', 'no_tool_visible', 'mixed', 'unclear']), 'placement': obj({'object': {'type': 'string'}, 'destination': {'type': 'string'}, 'release': enum(['visible', 'not_visible', 'not_applicable']), 'evidence_frame_ids': evidence}), 'tool_switch': segment('all'), 'uncertainties': array({'type': 'string'}, 0, 6)})


def prepare_media(case, config, folder):
    fps = case['clip']['fps']
    a, b = case['start_frame'], case['end_frame_exclusive']
    sample_fps = 8 if case['duration_s'] < 1.5 else 4
    cfg = dict(config, sample_fps=sample_fps)
    if case['duration_s'] > 40:
        cfg['sample_fps'] = 2
    a_context = max(0, a - round(4 * fps))
    b_context = min(case['clip']['frame_count'], b + round(6 * fps))
    event = {'event_id': case['case_id'], 'hand': case['target_hand'], 'start_frame': a, 'end_frame_exclusive': b}
    window = {'start_frame': a_context, 'end_frame_exclusive': b_context, 'events': [event]}
    media = prepare_window_media(case, window, cfg, folder)
    target_frames = [r for r in media['sampled_frames'] if a <= r['source_frame_index'] < b]
    if len(target_frames) < 2:
        raise ValueError('anomaly_contrast:target_sampling_under2:' + case['case_id'])
    media['target_interval_frames'] = [a, b]
    return media


def check_observation(value, case, media):
    mapped = {r['frame_id']: r['source_frame_index'] for r in media['sampled_frames']}
    a, b = case['start_frame'], case['end_frame_exclusive']
    for key in ['target', 'other_hand_during_target']:
        if any(not a <= mapped[fid] < b for fid in value[key]['evidence_frame_ids']):
            raise ValueError('anomaly_contrast:target_citation_outside:' + key)
    if any(mapped[fid] >= a for fid in value['before']['evidence_frame_ids']):
        raise ValueError('anomaly_contrast:before_citation_outside')
    if any(mapped[fid] < b for fid in value['after']['evidence_frame_ids']):
        raise ValueError('anomaly_contrast:after_citation_outside')


async def run(args):
    import torch
    assert torch.cuda.is_available(), 'anomaly_contrast:CUDA_unavailable'
    cases = prepare()
    folder = FOLDER / args.split / args.round
    folder.mkdir(parents=True, exist_ok=True)
    if args.split == 'validation' and not (FOLDER / 'rulebook_frozen_v1.json').exists():
        raise ValueError('anomaly_contrast:freeze_rules_before_validation')
    selected = [c for c in cases if c['split'] == args.split]
    if args.limit:
        selected = selected[:args.limit]
    config = read_json(ROOT / 'configs/impact_qa/mcq_grouped_v1.json')
    config.update(workers=4, per_service_concurrency=4, video_width=960, sample_fps=4, detail_crop=[0.04, 0.2, 0.96, 1.0], context_layout='side_panel', target_overlay=True, seed=20260928)
    prompt = (ROOT / 'prompts/impact_qa/anomaly_contrast_observe.txt').read_text()
    version = fingerprint([config, prompt, (ROOT / 'scripts/run_anomaly_contrast.py').read_text(), read_json(FOLDER / 'selection_frozen.json')])
    frozen = folder / 'run_frozen.json'
    if frozen.exists() and read_json(frozen)['version'] != version:
        raise ValueError('anomaly_contrast:changed_run_requires_new_version')
    save_json(frozen, {'version': version, 'config': config, 'prompt': prompt, 'torch': torch.__version__, 'cuda': torch.version.cuda, 'visible_gpus': torch.cuda.device_count()})
    pool = StructuredVideoPool(config, folder)
    semaphore = asyncio.Semaphore(config['workers'])

    async def process(case):
        path = folder / 'results' / (case['case_id'] + '.json')
        if path.exists() and read_json(path).get('status') == 'ok':
            return read_json(path)
        async with semaphore:
            result = {'case_id': case['case_id'], 'status': 'error'}
            try:
                media = await asyncio.to_thread(prepare_media, case, config, folder)
                payload = {'case_id': case['case_id'], 'view': 'front', 'target_hand': case['target_hand'], 'target_interval_source_frames': [case['start_frame'], case['end_frame_exclusive']], 'fps_of_source': case['clip']['fps'], 'frame_map': media['sampled_frames']}
                response = await pool.call('contrast_observe', prompt, payload, schema(media), 1800, video=media, validator=lambda value: check_observation(value, case, media))
                result.update(status='ok', media=media, observation=response['result'], api_cache_key=response['cache_key'])
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}:{exc}'
            save_json(path, result)
            print({k: result.get(k) for k in ['case_id', 'status', 'error']}, flush=True)
            return result

    try:
        results = await asyncio.gather(*(process(c) for c in selected))
    finally:
        await pool.close()
    save_jsonl(folder / 'observations.jsonl', results)
    summary = {'cases': len(selected), 'status': dict(Counter(r['status'] for r in results)), 'errors': [r for r in results if r['status'] != 'ok'], 'new_API_requests': len(pool.calls), 'labels_in_blind_payload': False, 'formal_release': False}
    save_json(folder / 'summary.json', summary)
    print(summary, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['discovery', 'validation'], default='discovery')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--round', default='observe_r1')
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.prepare_only:
            prepare()
            print(read_json(FOLDER / 'selection_frozen.json'))
        else:
            asyncio.run(run(args))


if __name__ == '__main__':
    main()
