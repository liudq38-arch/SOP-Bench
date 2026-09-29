import asyncio
import hashlib
import json
from collections import Counter

from .api import Pool
from .common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from .reliable_pool import ReliablePool
from .tool_review_v15 import validate


async def run(cases, folder, parent, prompt_path, source_files, condition, phase):
    prompt = prompt_path.read_text()
    snapshot = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    gate = asyncio.Semaphore(12)

    async def process(c):
        async with gate:
            images = c['image_refs']
            payload = {'question': c['question'], 'clip_start_original_s': c['start_frame'] / 30, 'clip_end_original_s_exclusive': (c['end_frame_inclusive'] + 1) / 30}
            key = fingerprint([snapshot, prompt, payload, images, pool.model_revision])
            path = folder / 'runs' / (c['contract_id'] + '.json')
            if path.exists():
                previous = read_json(path)
                assert previous['run_key'] == key, 'tool_batch:changed_version'
                if previous['status'] == 'ok':
                    return previous
            r = {'contract_id': c['contract_id'], 'run_key': key, 'status': 'running', 'phase': phase, 'condition': condition, 'previous_comparison': parent[c['contract_id']]['comparison'], 'generation': parent[c['contract_id']]['generation'], 'image_refs': images}
            try:
                response = await pool.call('gt_v15_tool_transition', prompt, payload, images, max_tokens=350)
                value, changes, answerable = validate(response['result'], images, 'transition8')
                comparison = 'abstain' if not answerable else ('short_answer_match' if value['tool'] == c['tool'] else 'short_answer_conflict')
                r.update(status='ok', raw_visual_review=response['result'], visual_review=value, normalizations=changes, answerable=answerable, comparison=comparison, proposed_retain=comparison == 'short_answer_match', cache_key=response['cache_key'])
            except Exception as exc:
                r.update(status='error', proposed_retain=False, error=f'tool_batch:{type(exc).__name__}:{exc}')
            save_json(path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'status', 'comparison', 'error']}), flush=True)
            return r

    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(folder / 'full_results.jsonl', records)
    summary = {'condition': condition, 'phase': phase, 'events': len(cases), 'counts': dict(Counter(r.get('comparison', 'error') for r in records)), 'gains': [r['contract_id'] for r in records if r['proposed_retain'] and r['previous_comparison'] != 'short_answer_match'], 'regressions': [r['contract_id'] for r in records if not r['proposed_retain'] and r['previous_comparison'] == 'short_answer_match'], 'independent_acceptance': False, 'source_snapshot': snapshot, 'prompt_hash': hashlib.sha256(prompt.encode()).hexdigest(), 'model_revision': pool.model_revision}
    save_json(folder / 'full_summary.json', summary)
    print(json.dumps(summary), flush=True)
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


def parents(phase):
    path = OUT / ('gt_v14_frozen_' + ('development' if phase == 'development' else 'acceptance')) / 'results.jsonl'
    return {r['contract_id']: r for r in read_jsonl(path)}
