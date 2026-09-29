import asyncio
import fcntl
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import torch
from vllm.multimodal.media.image import ImageMediaIO
from vllm.multimodal.media.video import VideoMediaIO

from impact_qa.common import ROOT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.descriptive_v21 import digest
from impact_qa.history_v23 import CONFIG, FOLDER, process
from impact_qa.structured_video_client import StructuredVideoPool


def precheck(records):
    if not torch.cuda.is_available():
        raise RuntimeError('history_v23:cuda_unavailable')
    for url in CONFIG['base_urls']:
        r = httpx.get(url + '/models', timeout=10, trust_env=False)
        r.raise_for_status()
        if CONFIG['model'] not in [m['id'] for m in r.json()['data']]:
            raise ValueError('history_v23:model_missing')
    first = []
    for record in records:
        all_ids = [f['frame_id'] for c in record['clips'] for f in c['core_frames']]
        if all_ids != [f['frame_id'] for f in record['frames']]:
            raise ValueError('history_v23:timeline_gap_or_duplicate')
        for clip in record['clips']:
            video = clip['video']
            if digest(video['path']) != video['sha256']:
                raise ValueError('history_v23:media_changed')
            decoded, meta = VideoMediaIO(ImageMediaIO(), **video['media_io_kwargs']['video']).load_file(Path(video['path']))
            if [clip['media_frames'][i]['frame_id'] for i in meta['frames_indices']] != [f['frame_id'] for f in video['sampled_frames']]:
                raise ValueError('history_v23:sample_mapping_changed')
            first.append({'case_id': record['case']['case_id'], 'clip_id': clip['clip_id'], 'core_frames': len(clip['core_frames']), 'video_frames': len(decoded), 'first_source_pts_s': clip['core_frames'][0]['source_pts_s'], 'last_source_pts_s': clip['core_frames'][-1]['source_pts_s']})
    result = {'torch': torch.__version__, 'cuda': torch.version.cuda, 'device_count': torch.cuda.device_count(), 'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used', '--format=csv,noheader'], text=True), 'cases': len(records), 'clips': len(first), 'core_frame_coverage': 'all native target indices exactly once', 'video_sampling': '8fps, at most 64 frames per window, actual decoder manifest verified', 'gt_provided_to_local_describe': False, 'full_source_video_processed': False}
    save_json(FOLDER / 'precheck.json', result)
    save_jsonl(FOLDER / 'first10_inputs.jsonl', first[:10])
    print(json.dumps(result), flush=True)


async def main():
    records = [r for r in read_jsonl(ROOT / CONFIG['source_cases']) if r['case']['pair_id'] == CONFIG['pair_id']]
    precheck(records)
    sources = ['impact_qa/history_v23.py', 'impact_qa/structured_video_client.py', 'scripts/run_history_v23.py', 'configs/impact_qa/history_v23.json', *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'prompts/impact_qa/v23').glob('*.txt'))]]
    frozen = {'source_hashes': {p: digest(ROOT / p) for p in sources}, 'cases_sha256': digest(ROOT / CONFIG['source_cases'])}
    frozen_path = FOLDER / 'frozen.json'
    if frozen_path.exists() and read_json(frozen_path) != frozen:
        raise ValueError('history_v23:frozen_sources_changed')
    save_json(frozen_path, frozen)
    pool = StructuredVideoPool(CONFIG, FOLDER)
    start = time.monotonic()
    try:
        results = await asyncio.gather(*(process(pool, r) for r in records))
        save_json(FOLDER / 'results.json', results)
        selected = {r['case_id'] for r in results}
        mcq = [r for r in read_jsonl(ROOT / 'outputs/impact_qa/descriptive_v21/fixed_mcq.jsonl') if r.get('case_id') in selected]
        save_jsonl(FOLDER / 'fixed_mcq.jsonl', mcq)
        summary = {'cases': len(results), 'completed': sum(r['status'] == 'completed_pending_review' for r in results), 'described_clips': sum(len(r['ledger']) for r in results), 'open_qa': sum(len(r.get('qa', {}).get('items', [])) for r in results), 'fixed_mcq': len(mcq), 'elapsed_s': time.monotonic() - start, 'new_requests': len(pool.calls), 'request_errors': sum(r['status'] != 'ok' for r in pool.calls), 'input_tokens': sum((r.get('usage') or {}).get('prompt_tokens', 0) for r in pool.calls), 'output_tokens': sum((r.get('usage') or {}).get('completion_tokens', 0) for r in pool.calls), 'formal_release': False}
        save_json(FOLDER / 'summary.json', summary)
        save_json(FOLDER / 'new_requests.json', pool.calls)
        print(json.dumps(summary), flush=True)
    finally:
        await pool.close()


if __name__ == '__main__':
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main())
