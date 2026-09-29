import argparse
import asyncio
import fcntl
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import torch

from impact_qa.batch_v25 import CONFIG, FOLDER, ROOT, digest, make_manifest, process
from impact_qa.common import read_json, read_jsonl, save_json, save_jsonl
from impact_qa.structured_video_client import StructuredVideoPool


async def main(args):
    if not torch.cuda.is_available():
        raise RuntimeError('batch_v25:cuda_unavailable')
    for url in CONFIG['base_urls']:
        response = httpx.get(url + '/models', trust_env=False, timeout=10)
        response.raise_for_status()
        if CONFIG['model'] not in [r['id'] for r in response.json()['data']]:
            raise RuntimeError('batch_v25:model_missing')
    precheck = {'torch': torch.__version__, 'cuda': torch.version.cuda, 'gpu_count': torch.cuda.device_count(), 'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used', '--format=csv,noheader'], text=True), 'pid': os.getpid()}
    save_json(FOLDER / 'precheck.json', precheck)
    manifest_path = FOLDER / 'manifest.jsonl'
    targets = read_jsonl(manifest_path) if manifest_path.exists() else make_manifest()
    paths = ['impact_qa/batch_v25.py', 'scripts/run_batch_v25.py', 'impact_qa/structured_video_client.py', 'impact_qa/history_v23.py', 'configs/impact_qa/history_v23.json', 'prompts/impact_qa/v23/describe.txt', 'prompts/impact_qa/v25_generate.txt', 'prompts/impact_qa/v25_review.txt']
    frozen = {'config': CONFIG, 'files': {p: digest(ROOT / p) for p in paths}, 'manifest': digest(manifest_path), 'user_authorization': '2026-09-21 user approved v24 approach and requested subsequent generation; does not mark new samples human-approved'}
    path = FOLDER / 'frozen.json'
    if path.exists() and read_json(path) != frozen:
        raise ValueError('batch_v25:frozen_inputs_changed')
    save_json(path, frozen)
    if args.prepare_only:
        print(read_json(FOLDER / 'selection_summary.json'), flush=True)
        return
    if args.limit:
        targets = targets[:args.limit]
    for cached in (FOLDER / 'api_cache').glob('*.json'):
        if not cached.stat().st_size:
            destination = FOLDER / 'interrupted_requests' / cached.name
            destination.parent.mkdir(exist_ok=True)
            cached.replace(destination)
            continue
        record = read_json(cached)
        if record['status'] == 'error' and not record.get('error') and not record.get('result'):
            destination = FOLDER / 'interrupted_requests' / cached.name
            destination.parent.mkdir(exist_ok=True)
            cached.replace(destination)
    pool = StructuredVideoPool(CONFIG, FOLDER)
    queue = asyncio.Queue()
    for target in targets:
        queue.put_nowait(target)
    results = []
    started = time.time()
    def progress(state):
        rows = []
        if (FOLDER / 'results').exists():
            for result_path in (FOLDER / 'results').glob('*.json'):
                try:
                    if result_path.stat().st_size:
                        rows.append(read_json(result_path))
                except (OSError, ValueError):
                    continue
        counts = Counter(r['status'] for r in rows)
        save_json(FOLDER / 'progress.json', {'state': state, 'pid': os.getpid(), 'updated_at_unix': time.time(), 'started_at_unix': started, 'selected': len(targets), 'counts': dict(counts), 'open_qa': sum(len(r.get('qa', {}).get('items', [])) for r in rows), 'held_qa': sum(len(r.get('held_items', [])) for r in rows), 'new_requests_this_run': len(pool.calls), 'input_tokens_this_run': sum((r.get('usage') or {}).get('prompt_tokens', 0) for r in pool.calls), 'output_tokens_this_run': sum((r.get('usage') or {}).get('completion_tokens', 0) for r in pool.calls), 'elapsed_s': time.time() - started, 'formal_release': False})
    async def worker():
        while True:
            try:
                target = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            result = await process(pool, target)
            results.append(result)
            queue.task_done()
            progress('running')
    async def heartbeat():
        while True:
            progress('running')
            await asyncio.sleep(10)
    task = asyncio.create_task(heartbeat())
    finished = False
    try:
        await asyncio.gather(*(worker() for _ in range(CONFIG['workers'])))
        save_jsonl(FOLDER / 'results.jsonl', results)
        save_jsonl(FOLDER / 'open_qa.jsonl', [dict(q, case_id=r['case_id'], human_review='unreviewed') for r in results for q in r.get('qa', {}).get('items', [])])
        save_jsonl(FOLDER / 'fixed_mcq.jsonl', [dict(q, case_id=r['case_id']) for r in results for q in r.get('fixed_mcq', [])])
        save_json(FOLDER / f'run_{int(started)}_requests.json', pool.calls)
        progress('finished')
        finished = True
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await pool.close()
        if not finished:
            progress('interrupted')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main(args))
