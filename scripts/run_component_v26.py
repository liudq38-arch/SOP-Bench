import argparse
import asyncio
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.v26_data import CONFIG, FOLDER, prepare_index
from impact_qa.v26_questions import build_questions, validate_plan


def prepare():
    manifest, summary = prepare_index()
    plans, mcqs, exclusions = [], [], []
    for clip in manifest:
        trial = read_json(FOLDER / 'trials' / (clip['video_id'] + '.json'))
        qs, mcq, excluded = build_questions(trial, clip)
        validate_plan(trial, clip, qs, mcq)
        save_json(FOLDER / 'plans' / (clip['clip_id'] + '.json'), {'clip': clip, 'questions': qs, 'mcq': mcq, 'excluded': excluded})
        plans.extend(qs)
        mcqs.extend(mcq)
        exclusions.extend(excluded)
    save_jsonl(FOLDER / 'question_plans.jsonl', plans)
    save_jsonl(FOLDER / 'fixed_mcq.jsonl', mcqs)
    save_jsonl(FOLDER / 'question_exclusions.jsonl', exclusions)
    save_jsonl(FOLDER / 'first10_questions.jsonl', plans[:10])
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return manifest


def preflight():
    import httpx
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('v26_preflight:cuda_unavailable')
    endpoints = []
    for url in CONFIG['base_urls']:
        r = httpx.get(url + '/models', timeout=10, trust_env=False)
        r.raise_for_status()
        if CONFIG['model'] not in [x['id'] for x in r.json()['data']]:
            raise RuntimeError('v26_preflight:wrong_model:' + url)
        endpoints.append({'url': url, 'status': r.status_code})
    record = {'timestamp': time.time(), 'pid': os.getpid(), 'python': sys.executable, 'torch': torch.__version__, 'cuda': torch.version.cuda, 'gpu_count': torch.cuda.device_count(), 'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used', '--format=csv,noheader'], text=True), 'services': endpoints, 'cuda_le_12_1_verified': False}
    save_json(FOLDER / 'preflight.json', record)
    return record


async def run(args):
    from impact_qa.structured_video_client import StructuredVideoPool
    from impact_qa.v26_pipeline import export_status, freeze, process_clip
    preflight()
    manifest = read_jsonl(FOLDER / 'manifest.jsonl')
    frozen_hash = freeze(manifest)
    selected = manifest[:args.limit] if args.limit else manifest
    pool = StructuredVideoPool(CONFIG, FOLDER)
    queue = asyncio.Queue()
    for c in selected:
        queue.put_nowait(c)
    async def worker():
        while not queue.empty():
            try:
                clip = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                results = await process_clip(pool, clip, frozen_hash)
                print(json.dumps({'clip_id': clip['clip_id'], 'arms': [(r['arm'], r['status']) for r in results]}), flush=True)
            except Exception as exc:
                save_json(FOLDER / 'preparation_errors' / (clip['clip_id'] + '.json'), {'clip_id': clip['clip_id'], 'module': 'process_clip', 'error': f'{type(exc).__name__}:{exc}'})
                print(json.dumps({'clip_id': clip['clip_id'], 'error': str(exc)}), flush=True)
            finally:
                queue.task_done()
            export_status()
    async def heartbeat():
        while True:
            export_status()
            await asyncio.sleep(15)
    task = asyncio.create_task(heartbeat())
    try:
        await asyncio.gather(*(worker() for _ in range(CONFIG['workers'])))
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await pool.close()
        save_json(FOLDER / 'runs' / (str(time.time_ns()) + '.json'), {'limit': args.limit, 'requests': pool.calls})
        print(json.dumps(export_status('smoke_finished' if args.limit else 'pilot_finished')), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.prepare_only:
            prepare()
        else:
            asyncio.run(run(args))
