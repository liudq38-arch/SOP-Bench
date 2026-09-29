import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.model_adapters import local_client
from impact_qa.reliable_pool import ReliablePool
from impact_qa.tool_batch import parents
from impact_qa.tool_review_v15 import select_images, validate


async def main(phase, smoke):
    source = 'gt_v14_1_tools' if phase == 'development' else 'gt_v14_acceptance_inputs'
    cases = read_jsonl(OUT / source / 'contracts.jsonl')
    old = parents(phase)
    if smoke:
        assert phase == 'development'
        failed = [c for c in cases if not old[c['contract_id']]['proposed_retain']]
        controls = [c for c in cases if old[c['contract_id']]['proposed_retain']]
        cases = failed + sum([sorted([c for c in controls if c['tool'] == tool], key=lambda c: fingerprint(c['contract_id']))[:2] for tool in ['wrench', 'screwdriver']], [])
    folder = OUT / 'gt_v15_tools/qwen3vl8b' / phase
    prompt = (ROOT / 'prompts/impact_qa/v14/tool_track.txt').read_text()
    sources = [Path(__file__), ROOT / 'impact_qa/model_adapters.py', ROOT / 'impact_qa/tool_review_v15.py', ROOT / 'impact_qa/api.py']
    code = fingerprint({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    backend = local_client('http://127.0.0.1:8003/v1', 'impact-qwen3vl8b', '/data_1/ldq/models/Qwen3-VL-8B-Instruct', 2)
    pool = ReliablePool(backend, folder / 'request_audit')
    gate = asyncio.Semaphore(2)
    label = 'smoke' if smoke else 'full'
    save_jsonl(folder / (label + '_first10.jsonl'), [{'contract_id': c['contract_id'], 'question': c['question'], 'image_refs': select_images(c, 'chronological20')} for c in cases[:10]])

    async def process(c):
        async with gate:
            images = select_images(c, 'chronological20')
            payload = {'question': c['question'], 'clip_start_original_s': c['start_frame'] / 30, 'clip_end_original_s_exclusive': (c['end_frame_inclusive'] + 1) / 30}
            key = fingerprint([code, prompt, payload, images, pool.model_revision])
            path = folder / 'runs' / (c['contract_id'] + '.json')
            if path.exists():
                previous = read_json(path)
                assert previous['run_key'] == key, 'crossmodel:changed_version'
                if previous['status'] == 'ok':
                    return previous
            r = {'contract_id': c['contract_id'], 'run_key': key, 'status': 'running', 'phase': phase, 'condition': 'qwen3vl8b', 'previous_comparison': old[c['contract_id']]['comparison'], 'generation': old[c['contract_id']]['generation'], 'image_refs': images, 'model': pool.model, 'model_revision': pool.model_revision}
            try:
                response = await pool.call('gt_v15_crossmodel_chronological20', prompt, payload, images, max_tokens=350)
                value, changes, answerable = validate(response['result'], images, 'chronological20')
                comparison = 'abstain' if not answerable else ('short_answer_match' if value['tool'] == c['tool'] else 'short_answer_conflict')
                r.update(status='ok', raw_visual_review=response['result'], visual_review=value, normalizations=changes, answerable=answerable, comparison=comparison, proposed_retain=comparison == 'short_answer_match', cache_key=response['cache_key'])
            except Exception as exc:
                r.update(status='error', proposed_retain=False, error=f'crossmodel:{type(exc).__name__}:{exc}')
            save_json(path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'status', 'comparison', 'error']}), flush=True)
            return r

    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(folder / (label + '_results.jsonl'), records)
    summary = {'condition': 'qwen3vl8b', 'phase': phase, 'events': len(cases), 'counts': dict(Counter(r.get('comparison', 'error') for r in records)), 'gains': [r['contract_id'] for r in records if r['proposed_retain'] and r['previous_comparison'] != 'short_answer_match'], 'regressions': [r['contract_id'] for r in records if not r['proposed_retain'] and r['previous_comparison'] == 'short_answer_match'], 'independent_acceptance': False, 'code_hash': code, 'prompt_hash': hashlib.sha256(prompt.encode()).hexdigest(), 'model': pool.model, 'model_revision': pool.model_revision}
    save_json(folder / (label + '_summary.json'), summary)
    print(json.dumps(summary), flush=True)
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True, choices=['development', 'exposed_regression'])
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    asyncio.run(main(args.phase, args.smoke))
