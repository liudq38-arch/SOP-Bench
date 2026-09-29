import asyncio
import copy
import fcntl
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_package import blind_payload, generation_payload
from impact_qa.quality_v16 import decide, source_payload, validate
from impact_qa.reliable_pool import ReliablePool


async def main():
    folder = OUT / 'evidence_v17_generation'
    cases = {c['contract_id']: c for c in read_jsonl(OUT / 'quality_v16_inputs/contracts.jsonl')}
    qualifications = {r['contract_id']: r for r in read_jsonl(OUT / 'evidence_v17_qualification/results.jsonl')}
    packages = [p for p in read_jsonl(OUT / 'evidence_v17_inputs/smoke_packages.jsonl') if qualifications[p['contract_id']]['status'] == 'ready_for_gt_constrained_generation']
    prompts = {s: (ROOT / 'prompts/impact_qa/v16' / (s + '.txt')).read_text() for s in ['generate', 'blind', 'visual_audit', 'source_audit']}
    guidance = '\nPublic reference images and the illustrated procedure help identify actions but are NOT target evidence or mandatory constraints. Target evidence IDs are separate. Use only allowed target IDs in claims. Extra boundary frames may be context before/after the original question interval; do not change the target interval or cutoff. Execution context is private source information and does not prove visibility. Time fields containing frame are frame numbers, never seconds. Context cannot authorize claims beyond the canonical answer contract.\n'
    prompts = {s: p + guidance for s, p in prompts.items()}
    source_files = [Path(__file__), ROOT / 'impact_qa/evidence_package.py', ROOT / 'impact_qa/quality_v16.py', ROOT / 'impact_qa/api.py', ROOT / 'impact_qa/reliable_pool.py', ROOT / 'impact_qa/common.py'] + list((ROOT / 'prompts/impact_qa/v16').glob('*.txt'))
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    frozen = {'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}, 'packages_hash': fingerprint(packages), 'qualifications_hash': fingerprint(qualifications), 'model_revision': pool.model_revision}
    if (folder / 'frozen.json').exists() and read_json(folder / 'frozen.json') != frozen:
        await pool.close()
        raise ValueError('generate_v17:changed_version')
    save_json(folder / 'frozen.json', frozen)
    gate = asyncio.Semaphore(12)

    async def process(p):
        async with gate:
            c = copy.deepcopy(cases[p['contract_id']])
            c['image_refs'] = p['target_visual']['images']
            images = c['image_refs'] + p['public_reference']['action_examples']
            path = folder / 'runs' / (c['contract_id'] + '.json')
            if path.exists():
                r = read_json(path)
                if r['status'] != 'running':
                    return r
            else:
                r = {'contract_id': c['contract_id'], 'kind': c['kind'], 'status': 'running', 'stages': {}, 'cache_keys': {}}
            async def stage(name, payload, refs, tokens):
                if name not in r['stages']:
                    response = await pool.call('evidence_v17_' + name, prompts[name], payload, refs, max_tokens=tokens)
                    r['cache_keys'][name] = response['cache_key']
                    r['stages'][name] = validate(name, response['result'], c, r['stages'].get('generate'))
                    save_json(path, r)
                return r['stages'][name]
            try:
                enriched = generation_payload(p)
                enriched['eligibility'] = {**enriched['eligibility'], 'visual_sufficiency': 'blind_model_qualified_not_independently_validated', 'new_generation_allowed': True}
                source = {**source_payload(c), 'evidence_package': enriched}
                g = await stage('generate', source, images, 800)
                public = blind_payload(p, g['open_question'])
                b = await stage('blind', public, images, 550)
                v_payload = {**public, 'proposed_qa': {k: g[k] for k in ['open_question', 'answer', 'mcq_question']}, 'claims': [{'claim': cl['claim'], 'image_ids': cl['image_ids']} for cl in g['claims']], 'options': c['options'], 'blind_answer': b}
                both = await asyncio.gather(stage('visual_audit', v_payload, images, 1100), stage('source_audit', {**source, 'proposed_qa': g, 'blind_answer': b}, [], 600), return_exceptions=True)
                errors = [str(v) for v in both if isinstance(v, Exception)]
                if errors:
                    raise ValueError(';'.join(errors))
                r['decision'] = decide(c, r['stages'])
                r['status'] = r['decision']['disposition']
            except Exception as exc:
                r.update(status='schema_or_runtime_error', error=f'{type(exc).__name__}:{exc}')
            save_json(path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'kind', 'status', 'error']}), flush=True)
            return r
    try:
        results = await asyncio.gather(*(process(p) for p in packages))
    finally:
        await pool.close()
    save_jsonl(folder / 'results.jsonl', results)
    exports = []
    public_rows = []
    lookup = {p['contract_id']: p for p in packages}
    for r in results:
        if r['status'] != 'model_passed_unvalidated':
            continue
        c, p = cases[r['contract_id']], lookup[r['contract_id']]
        g = r['stages']['generate']
        exports.append({'contract_id': c['contract_id'], 'kind': c['kind'], **g, 'options': c['options'], 'correct_option': c['correct_option'], 'quality': r['decision'], 'package_path': str(OUT / 'evidence_v17_inputs/packages' / (c['contract_id'] + '.json'))})
        media = [{k: im[k] for k in ['evidence_id', 'path', 'sha256', 'requested_time_s', 'view', 'time_scope']} for im in p['target_visual']['images'] + p['public_reference']['action_examples']]
        for form in ['open', 'mcq']:
            row = {'id': c['contract_id'] + ':' + form, 'format': form, **blind_payload(p, g['open_question'] if form == 'open' else g['mcq_question']), 'images': media}
            if form == 'mcq':
                row['options'] = c['options']
            public_rows.append(row)
    save_jsonl(folder / 'model_passed_candidates.jsonl', exports)
    save_jsonl(folder / 'evaluation_inputs.jsonl', public_rows)
    save_json(folder / 'summary.json', {'qualified_events': len(packages), 'counts': dict(Counter(r['status'] for r in results)), 'open_qa': len(exports), 'mcq_qa': len(exports), 'GT_plus_visual_plus_procedure_plus_context_supplied': True, 'public_references_identical_in_generation_blind_review_and_export': True, 'formal_release': False})


if __name__ == '__main__':
    lock = (OUT / 'quality_v16_runner.lock').open('w')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('generate_v17:another_runner_is_active')
    asyncio.run(main())
