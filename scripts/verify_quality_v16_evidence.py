import asyncio
import fcntl
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.reliable_pool import ReliablePool
from impact_qa.tool_review_v15 import validate


async def main():
    folder = OUT / 'quality_v16_evidence'
    sources = [ROOT / 'scripts/verify_quality_v16_evidence.py', ROOT / 'prompts/impact_qa/v16_evidence/evidence_pair.txt', ROOT / 'impact_qa/tool_review_v15.py', ROOT / 'impact_qa/evidence_ids.py', ROOT / 'impact_qa/api.py', ROOT / 'impact_qa/common.py', ROOT / 'impact_qa/reliable_pool.py']
    snapshot = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    prompt = (ROOT / 'prompts/impact_qa/v16_evidence/evidence_pair.txt').read_text()
    cases = {c['contract_id']: c for path in [OUT / 'quality_v16_inputs/contracts.jsonl', OUT / 'quality_v16_training_inputs/contracts.jsonl'] for c in read_jsonl(path)}
    rows = [r for batch in ['quality_v16_batch001', 'quality_v16_batch002'] for r in read_jsonl(OUT / batch / 'results.jsonl') if r['disposition'] == 'model_passed_unvalidated']
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    gate = asyncio.Semaphore(12)
    frozen = {'sources': snapshot, 'parent_results_hash': fingerprint(rows), 'model_revision': pool.model_revision}
    if (folder / 'frozen.json').exists() and read_json(folder / 'frozen.json') != frozen:
        await pool.close()
        raise ValueError('evidence_v16:changed_version')
    save_json(folder / 'frozen.json', frozen)

    async def process(r):
        async with gate:
            c = cases[r['contract_id']]
            path = folder / 'runs' / (c['contract_id'] + '.json')
            if path.exists():
                return read_json(path)
            out = {'contract_id': c['contract_id'], 'kind': c['kind'], 'status': 'pending_specialist_review', 'formal_release': False}
            if c['kind'] != 'tool_identity':
                out['reason'] = 'Component identity/action timing requires dedicated evidence qualification; four-role agreement is insufficient.'
            else:
                v = r['stages']['visual_audit']
                by_id = {im['evidence_id']: im for im in c['image_refs']}
                images = [by_id[v['before_id']], by_id[v['after_id']]]
                out['image_refs'] = images
                payload = {'question': r['stages']['generate']['open_question'], 'allowed_image_ids': [im['evidence_id'] for im in images]}
                try:
                    response = await pool.call('quality_v16_evidence_pair', prompt, payload, images, max_tokens=350)
                    value, normalizations, answerable = validate(response['result'], images, 'transition8')
                    out.update(visual_review=value, normalizations=normalizations, cache_key=response['cache_key'], status='evidence_screened_unvalidated' if answerable and value['tool'] == c['tool'] else 'quarantine_evidence', reason='Same-object two-frame evidence agrees with GT.' if answerable and value['tool'] == c['tool'] else 'Cited pair does not independently establish the GT pickup.')
                except Exception as exc:
                    out.update(status='evidence_schema_or_runtime_error', error=f'{type(exc).__name__}:{exc}')
            save_json(path, out)
            print(json.dumps({k: out.get(k) for k in ['contract_id', 'status', 'error']}), flush=True)
            return out
    try:
        result = await asyncio.gather(*(process(r) for r in rows))
    finally:
        await pool.close()
    save_jsonl(folder / 'results.jsonl', result)
    save_json(folder / 'summary.json', {'parent_model_passed': len(rows), 'counts': dict(Counter(r['status'] for r in result)), 'formal_release': False, 'same_model_roles': True, 'designed_after_batch001_inspection': True})


if __name__ == '__main__':
    lock = (OUT / 'quality_v16_runner.lock').open('w')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('evidence_v16:another_runner_is_active')
    asyncio.run(main())
