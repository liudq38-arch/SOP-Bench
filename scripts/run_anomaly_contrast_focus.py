import argparse
import asyncio
from collections import Counter
import fcntl
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.anomaly_contrast import FOLDER
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_grouped_media import prepare_window_media
from impact_qa.mcq_grouped_review import array, enum, obj
from impact_qa.structured_video_client import StructuredVideoPool


def schema(media):
    evidence = array(enum(x['frame_id'] for x in media['sampled_frames']), 1, 5)
    return obj({'target_hand_clear': {'type': 'boolean'}, 'target_summary': {'type': 'string'}, 'other_hand_summary': {'type': 'string'}, 'observations': array(obj({'fact': {'type': 'string'}, 'evidence_frame_ids': evidence}), 1, 3), 'tool_appearance': {'type': 'string'}, 'tool_tip_contact': enum(['visible', 'not_visible', 'unclear', 'not_applicable']), 'placement': obj({'object': {'type': 'string'}, 'destination': {'type': 'string'}, 'release': enum(['visible', 'not_visible', 'unclear', 'not_applicable'])}), 'unknowns': array({'type': 'string'}, 0, 4)})


def media_for(case, config, folder):
    cfg = dict(config, sample_fps=max(1, min(8, int(24 / case['duration_s']))))
    event = {'event_id': case['case_id'], 'hand': case['target_hand'], 'start_frame': case['start_frame'], 'end_frame_exclusive': case['end_frame_exclusive']}
    return prepare_window_media(case, dict(event, events=[event]), cfg, folder)


async def run(args):
    import torch
    assert torch.cuda.is_available(), 'contrast_focus:CUDA_unavailable'
    rule_path = FOLDER / 'rulebook_frozen_v1.json'
    if args.split == 'validation' and not rule_path.exists():
        raise ValueError('contrast_focus:freeze_before_validation')
    cases = [c for c in read_jsonl(FOLDER / 'cases.jsonl') if c['split'] == args.split]
    if args.case_ids:
        cases = [c for c in cases if c['case_id'] in args.case_ids.split(',')]
    folder = FOLDER / args.split / 'focus_r1'
    folder.mkdir(parents=True, exist_ok=True)
    config = read_json(ROOT / 'configs/impact_qa/mcq_grouped_v1.json')
    config.update(workers=4, per_service_concurrency=4, video_width=960, video_pixel_budget=16777216, detail_crop=[.10, .35, .90, 1.0], context_layout='side_panel', target_overlay=True, seed=20260928)
    prompt = (ROOT / 'prompts/impact_qa/anomaly_contrast_focus.txt').read_text()
    version = fingerprint([config, prompt, Path(__file__).read_text(), read_json(FOLDER / 'selection_frozen.json')])
    frozen = folder / 'run_frozen.json'
    if frozen.exists() and read_json(frozen)['version'] != version:
        raise ValueError('contrast_focus:changed_frozen_run')
    save_json(frozen, {'version': version, 'config': config, 'prompt': prompt, 'torch': torch.__version__, 'cuda': torch.version.cuda, 'visible_gpus': torch.cuda.device_count(), 'rulebook_hash': fingerprint(read_json(rule_path)) if rule_path.exists() else None})
    pool = StructuredVideoPool(config, folder)
    sem = asyncio.Semaphore(4)

    async def process(case):
        path = folder / 'results' / (case['case_id'] + '.json')
        if path.exists() and read_json(path)['status'] == 'ok':
            return read_json(path)
        async with sem:
            result = {'case_id': case['case_id'], 'status': 'error'}
            try:
                media = await asyncio.to_thread(media_for, case, config, folder)
                payload = {'case_id': case['case_id'], 'target_hand': case['target_hand'], 'view': 'front', 'entire_video_is_target': True, 'source_frames': [{'frame_id': x['frame_id'], 'source_time_s': x['source_pts_s']} for x in media['sampled_frames']]}
                response = await pool.call('contrast_focus', prompt, payload, schema(media), 900, video=media)
                result.update(status='ok', media=media, observation=response['result'], api_cache_key=response['cache_key'])
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}:{exc}'
            save_json(path, result)
            print({k: result.get(k) for k in ['case_id', 'status', 'error']}, flush=True)
            return result
    try:
        results = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(folder / 'observations.jsonl', results)
    summary = {'cases': len(results), 'status': dict(Counter(r['status'] for r in results)), 'new_API_requests': len(pool.calls), 'formal_release': False}
    save_json(folder / 'summary.json', summary)
    print(summary, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['discovery', 'validation'], default='discovery')
    parser.add_argument('--case-ids')
    args = parser.parse_args()
    with (FOLDER / 'focus_runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(run(args))


if __name__ == '__main__':
    main()
