import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.reliable_pool import ReliablePool
from impact_qa.tool_review_v15 import select_images, validate


async def main(phase, condition, smoke):
    name = 'gt_v14_1_tools' if phase == 'development' else 'gt_v14_acceptance_inputs'
    cases = read_jsonl(OUT / name / 'contracts.jsonl')
    old = {r['contract_id']: r for r in read_jsonl(OUT / ('gt_v14_frozen_' + ('development' if phase == 'development' else 'acceptance')) / 'results.jsonl')}
    if smoke:
        assert phase == 'development'
        failed = [c for c in cases if not old[c['contract_id']]['proposed_retain']]
        controls = [c for c in cases if old[c['contract_id']]['proposed_retain']]
        cases = failed + sum([sorted([c for c in controls if c['tool'] == tool], key=lambda c: fingerprint(c['contract_id']))[:2] for tool in ['wrench', 'screwdriver']], [])
    folder = OUT / 'gt_v15_tools' / condition / phase
    prompt_path = ROOT / ('prompts/impact_qa/v14/tool_track.txt' if condition == 'chronological20' else 'prompts/impact_qa/v15/tool_transition.txt')
    prompt = prompt_path.read_text()
    code_hash = fingerprint({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), ROOT / 'impact_qa/tool_review_v15.py', ROOT / 'impact_qa/reliable_pool.py', ROOT / 'impact_qa/api.py']})
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    gate = asyncio.Semaphore(12)
    label = 'smoke' if smoke else 'full'
    save_jsonl(folder / (label + '_first10.jsonl'), [{'contract_id': c['contract_id'], 'question': c['question'], 'images': select_images(c, condition)} for c in cases[:10]])

    async def process(c):
        async with gate:
            images = select_images(c, condition)
            payload = {'question': c['question'], 'clip_start_original_s': c['start_frame'] / 30, 'clip_end_original_s_exclusive': (c['end_frame_inclusive'] + 1) / 30}
            key = fingerprint([code_hash, prompt, payload, images, pool.model_revision])
            path = folder / 'runs' / (c['contract_id'] + '.json')
            if path.exists():
                previous = read_json(path)
                assert previous['run_key'] == key, 'v15:changed_version'
                if previous['status'] == 'ok':
                    return previous
            r = {'contract_id': c['contract_id'], 'run_key': key, 'status': 'running', 'phase': phase, 'condition': condition, 'previous_comparison': old[c['contract_id']]['comparison'], 'generation': old[c['contract_id']]['generation'], 'image_refs': images}
            try:
                stage = 'gt_v14_1_tool_track' if condition == 'chronological20' else 'gt_v15_tool_transition'
                response = await pool.call(stage, prompt, payload, images, max_tokens=350)
                value, changes, answerable = validate(response['result'], images, condition)
                comparison = 'abstain' if not answerable else ('short_answer_match' if value['tool'] == c['tool'] else 'short_answer_conflict')
                r.update(status='ok', raw_visual_review=response['result'], visual_review=value, normalizations=changes, answerable=answerable, comparison=comparison, proposed_retain=comparison == 'short_answer_match', cache_key=response['cache_key'])
            except Exception as exc:
                r.update(status='error', proposed_retain=False, error=f'v15:{type(exc).__name__}:{exc}')
            save_json(path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'status', 'comparison', 'error']}), flush=True)
            return r

    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(folder / (label + '_results.jsonl'), records)
    summary = {'phase': phase, 'condition': condition, 'events': len(cases), 'counts': dict(Counter(r.get('comparison', 'error') for r in records)), 'gains': [r['contract_id'] for r in records if r['proposed_retain'] and r['previous_comparison'] != 'short_answer_match'], 'regressions': [r['contract_id'] for r in records if not r['proposed_retain'] and r['previous_comparison'] == 'short_answer_match'], 'independent_acceptance': False, 'code_hash': code_hash, 'prompt_hash': hashlib.sha256(prompt.encode()).hexdigest(), 'model_revision': pool.model_revision}
    save_json(folder / (label + '_summary.json'), summary)
    print(json.dumps(summary), flush=True)
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['development', 'exposed_regression'], required=True)
    parser.add_argument('--condition', choices=['chronological20', 'transition8'], required=True)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    asyncio.run(main(args.phase, args.condition, args.smoke))
