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
from impact_qa.evidence_package import blind_payload
from impact_qa.quality_v16 import ids, require, short
from impact_qa.reliable_pool import ReliablePool


def validate(value, payload):
    require(set(value) == {'answerable', 'visual_grade', 'answer', 'observations', 'needs', 'limitation'}, 'qualify_schema')
    require(type(value['answerable']) is bool and type(value['visual_grade']) is int and value['visual_grade'] in range(4), 'qualify_types')
    short(value['answer'], 60)
    short(value['limitation'], 60)
    require(isinstance(value['observations'], list) and len(value['observations']) <= 3, 'qualify_observations')
    for row in value['observations']:
        require(set(row) == {'fact', 'target_image_ids', 'reference_image_ids'}, 'qualify_fact_schema')
        short(row['fact'], 40)
        ids(row['target_image_ids'], payload['allowed_target_image_ids'], not value['answerable'])
        ids(row['reference_image_ids'], payload['allowed_reference_image_ids'])
    ids(value['needs'], ['boundary', 'identity_reference', 'wider_context', 'synchronized_view', 'normative_source', 'none'], False)
    if value['answerable']:
        require(value['visual_grade'] == 3 and value['needs'] == ['none'] and bool(value['observations']), 'qualify_inconsistent_pass')
    else:
        require(value['visual_grade'] < 3 and 'none' not in value['needs'], 'qualify_inconsistent_hold')
    return value


async def main():
    folder = OUT / 'evidence_v17_qualification'
    path = OUT / 'evidence_v17_inputs/smoke_packages.jsonl'
    packages = read_jsonl(path)
    prompt_path = ROOT / 'prompts/impact_qa/v17/qualify.txt'
    prompt = prompt_path.read_text()
    sources = [Path(__file__), prompt_path, ROOT / 'impact_qa/evidence_package.py', ROOT / 'impact_qa/quality_v16.py', ROOT / 'scripts/prepare_evidence_v17.py', ROOT / 'impact_qa/api.py', ROOT / 'impact_qa/reliable_pool.py']
    snapshot = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    frozen = {'sources': snapshot, 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'model_revision': pool.model_revision}
    if (folder / 'frozen.json').exists() and read_json(folder / 'frozen.json') != frozen:
        await pool.close()
        raise ValueError('qualify_v17:changed_frozen_run')
    save_json(folder / 'frozen.json', frozen)
    gate = asyncio.Semaphore(12)

    async def process(p):
        async with gate:
            record_path = folder / 'runs' / (p['contract_id'] + '.json')
            if record_path.exists():
                return read_json(record_path)
            payload = blind_payload(p, p['answer_contract']['question_proposition'])
            images = p['target_visual']['images'] + p['public_reference']['action_examples']
            for im in images:
                require(hashlib.sha256(Path(im['path']).read_bytes()).hexdigest() == im['sha256'], 'qualify_media_hash')
            r = {'contract_id': p['contract_id'], 'kind': p['kind'], 'formal_release': False}
            try:
                response = await pool.call('evidence_v17_qualify', prompt, payload, images, max_tokens=850)
                r['cache_key'] = response['cache_key']
                r['qualification'] = validate(response['result'], payload)
                r['status'] = 'ready_for_gt_constrained_generation' if r['qualification']['answerable'] else 'needs_evidence'
            except Exception as exc:
                r.update(status='schema_or_runtime_error', error=f'{type(exc).__name__}:{exc}')
            save_json(record_path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'kind', 'status', 'error']}), flush=True)
            return r
    try:
        results = await asyncio.gather(*(process(p) for p in packages))
    finally:
        await pool.close()
    save_jsonl(folder / 'results.jsonl', results)
    save_json(folder / 'summary.json', {'events': len(results), 'counts': dict(Counter(r['status'] for r in results)), 'needs': dict(Counter(need for r in results for need in r.get('qualification', {}).get('needs', []) if need != 'none')), 'not_accuracy': True, 'QA_generated_by_this_stage': 0, 'formal_release': False})


if __name__ == '__main__':
    lock = (OUT / 'quality_v16_runner.lock').open('w')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('qualify_v17:another_runner_is_active')
    asyncio.run(main())
