import argparse
import asyncio
import copy
import fcntl
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_package import blind_payload, generation_payload
from impact_qa.evidence_validation import validate_qualification, validate_stage
from impact_qa.quality_v16 import decide, require, source_payload
from impact_qa.reliable_pool import ReliablePool
from impact_qa.tool_review_v15 import validate as validate_pair


GUIDANCE = '\nPublic reference images and the illustrated procedure help identify actions but are NOT target evidence or mandatory constraints. Target evidence IDs are separate. Use only allowed target IDs in claims. Extra boundary frames may be context before/after the original question interval; do not change the target interval or cutoff. Execution context is private source information and does not prove visibility. Time fields containing frame are frame numbers, never seconds. Context cannot authorize claims beyond the canonical answer contract.\n'


class StageValidationError(ValueError):
    pass


def export(folder, packages, cases, records, elapsed):
    lookup = {p['contract_id']: p for p in packages}
    candidates, public, screened, disposition = [], [], [], []
    kinds = defaultdict(Counter)
    for r in records:
        kinds[r['kind']][r['status']] += 1
        disposition.append({'contract_id': r['contract_id'], 'kind': r['kind'], 'status': r['status'], 'error': r.get('error'), 'decision': r.get('decision'), 'qualification_needs': r['stages'].get('qualify', {}).get('needs'), 'style_warnings': r.get('style_warnings', {})})
        if r.get('decision', {}).get('disposition') != 'model_passed_unvalidated':
            continue
        p, c, g = lookup[r['contract_id']], cases[r['contract_id']], r['stages']['generate']
        row = {'contract_id': r['contract_id'], 'video_id': p['video_id'], 'kind': r['kind'], 'status': r['status'], **g, 'options': c['options'], 'correct_option': c['correct_option'], 'quality': r['decision'], 'package_path': str(OUT / 'evidence_v18_inputs/packages' / (r['contract_id'] + '.json')), 'review_path': str(folder / 'runs' / (r['contract_id'] + '.json')), 'formal_release': False}
        candidates.append(row)
        if r['status'] != 'evidence_screened_unvalidated':
            continue
        screened.append(row)
        images = p['target_visual']['images'] + p['public_reference']['action_examples']
        media = [{k: im[k] for k in ['evidence_id', 'path', 'sha256', 'requested_time_s', 'view', 'time_scope']} for im in images]
        for form in ['open', 'mcq']:
            public_row = {'id': r['contract_id'] + ':' + form, 'format': form, **blind_payload(p, g['open_question'] if form == 'open' else g['mcq_question']), 'images': media}
            if form == 'mcq':
                public_row['options'] = c['options']
            public.append(public_row)
    save_jsonl(folder / 'results.jsonl', records)
    save_jsonl(folder / 'disposition.jsonl', disposition)
    save_jsonl(folder / 'primary_candidates.jsonl', candidates)
    save_jsonl(folder / 'screened_candidates.jsonl', screened)
    save_jsonl(folder / 'evaluation_inputs.jsonl', public)
    save_jsonl(folder / 'hold.jsonl', [r for r in disposition if r['status'] != 'evidence_screened_unvalidated'])
    summary = {'events': len(records), 'counts': dict(Counter(r['status'] for r in records)), 'by_kind': {k: dict(v) for k, v in kinds.items()}, 'qualified_for_generation': sum('generate' in r['cache_keys'] for r in records), 'primary_candidates': len(candidates), 'screened_events': len(screened), 'open_qa': len(screened), 'mcq_qa': len(screened), 'events_with_style_warning': sum(any(r.get('style_warnings', {}).values()) for r in records), 'same_model_roles': True, 'wall_seconds_this_invocation': elapsed, 'formal_release': False, 'independent_acceptance': False}
    save_json(folder / 'summary.json', summary)
    if not (folder / 'initial_completed_summary.json').exists():
        save_json(folder / 'initial_completed_summary.json', summary)
    print(json.dumps(summary), flush=True)


async def run(args):
    packages = read_jsonl(args.input)
    if args.smoke:
        selected = {r['contract_id'] for r in read_jsonl(OUT / 'quality_v16_inputs/smoke.jsonl')}
        packages = [p for p in packages if p['contract_id'] in selected]
    cases = {c['contract_id']: c for name in ['quality_v16_inputs', 'quality_v16_training_inputs'] for c in read_jsonl(OUT / name / 'contracts.jsonl')}
    require(len({p['contract_id'] for p in packages}) == len(packages), 'batch_duplicate_event')
    media_hashes = {}
    for p in packages:
        require(p['eligibility'].get('media_materialized') is True, 'unmaterialized_package')
        for im in p['target_visual']['images'] + p['public_reference']['action_examples']:
            actual = media_hashes.get(im['path'])
            if actual is None:
                actual = hashlib.sha256(Path(im['path']).read_bytes()).hexdigest()
                media_hashes[im['path']] = actual
            require(actual == im['sha256'], 'batch_media_hash:' + im['path'])
    folder = args.output
    prompts = {s: (ROOT / 'prompts/impact_qa/v16' / (s + '.txt')).read_text() + GUIDANCE for s in ['generate', 'blind', 'visual_audit', 'source_audit']}
    prompts['qualify'] = (ROOT / 'prompts/impact_qa/v17/qualify.txt').read_text()
    prompts['pair'] = (ROOT / 'prompts/impact_qa/v16_evidence/evidence_pair.txt').read_text()
    names = ['impact_qa/evidence_validation.py', 'impact_qa/evidence_package.py', 'impact_qa/quality_v16.py', 'impact_qa/api.py', 'impact_qa/reliable_pool.py', 'impact_qa/common.py', 'impact_qa/tool_review_v15.py', 'impact_qa/evidence_ids.py', 'scripts/qualify_evidence_v17.py', 'scripts/prepare_evidence_v18.py', 'scripts/prepare_evidence_v17.py', 'scripts/run_evidence_v18.py']
    source_files = [ROOT / name for name in names] + [ROOT / 'prompts/impact_qa/v17/qualify.txt', ROOT / 'prompts/impact_qa/v16_evidence/evidence_pair.txt'] + sorted((ROOT / 'prompts/impact_qa/v16').glob('*.txt'))
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    frozen = {'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}, 'packages_hash': fingerprint(packages), 'model_revision': pool.model_revision, 'events': len(packages), 'prompts': prompts, 'per_service_concurrency': 4, 'semantic_retries': 0, 'private_word_limits_are_style_warnings': True}
    if (folder / 'frozen.json').exists() and read_json(folder / 'frozen.json') != frozen:
        await pool.close()
        raise ValueError('batch_v18:changed_frozen_version')
    if not (folder / 'frozen.json').exists():
        save_json(folder / 'frozen.json', frozen)
    gate = asyncio.Semaphore(12)
    started = time.monotonic()
    progress = Counter()

    async def process(p):
        async with gate:
            c = copy.deepcopy(cases[p['contract_id']])
            c['image_refs'] = p['target_visual']['images']
            images = c['image_refs'] + p['public_reference']['action_examples']
            path = folder / 'runs' / (p['contract_id'] + '.json')
            key = fingerprint([frozen['packages_hash'], p['package_hash'], pool.model_revision])
            if path.exists():
                r = read_json(path)
                require(r['run_key'] == key, 'batch_changed_checkpoint')
                if r['status'] != 'running':
                    progress[r['status']] += 1
                    return r
            else:
                r = {'contract_id': p['contract_id'], 'kind': p['kind'], 'run_key': key, 'status': 'running', 'stages': {}, 'cache_keys': {}, 'style_warnings': {}}

            async def stage(name, payload, refs, tokens):
                if name not in r['stages']:
                    api_stage = 'quality_v16_evidence_pair' if name == 'pair' else 'evidence_v17_' + name
                    response = await pool.call(api_stage, prompts[name], payload, refs, max_tokens=tokens)
                    r['cache_keys'][name] = response['cache_key']
                    save_json(path, r)
                    try:
                        if name == 'qualify':
                            value, warnings = validate_qualification(response['result'], payload)
                        elif name == 'pair':
                            value, normalizations, answerable = validate_pair(response['result'], refs, 'transition8')
                            value = {'review': value, 'normalizations': normalizations, 'answerable': answerable}
                            warnings = []
                        else:
                            value, warnings = validate_stage(name, response['result'], c, r['stages'].get('generate'))
                    except Exception as exc:
                        raise StageValidationError(f'{name}:{type(exc).__name__}:{exc}') from exc
                    r['stages'][name], r['style_warnings'][name] = value, warnings
                    save_json(path, r)
                return r['stages'][name]

            async def pipeline():
                q = await stage('qualify', blind_payload(p, p['answer_contract']['question_proposition']), images, 850)
                if not q['answerable']:
                    return 'needs_evidence'
                enriched = generation_payload(p)
                enriched['eligibility'] = {**enriched['eligibility'], 'visual_sufficiency': 'blind_model_qualified_not_independently_validated', 'new_generation_allowed': True}
                source = {**source_payload(c), 'evidence_package': enriched}
                g = await stage('generate', source, images, 800)
                public = blind_payload(p, g['open_question'])
                b = await stage('blind', public, images, 550)
                vision = {**public, 'proposed_qa': {k: g[k] for k in ['open_question', 'answer', 'mcq_question']}, 'claims': [{'claim': cl['claim'], 'image_ids': cl['image_ids']} for cl in g['claims']], 'options': c['options'], 'blind_answer': b}
                audits = await asyncio.gather(stage('visual_audit', vision, images, 1100), stage('source_audit', {**source, 'proposed_qa': g, 'blind_answer': b}, [], 600), return_exceptions=True)
                errors = [value for value in audits if isinstance(value, Exception)]
                if errors:
                    raise errors[0]
                r['decision'] = decide(c, r['stages'])
                if r['decision']['disposition'] != 'model_passed_unvalidated':
                    return 'quarantine_semantics'
                if c['kind'] != 'tool_identity':
                    return 'pending_specialist_review'
                v = r['stages']['visual_audit']
                by_id = {im['evidence_id']: im for im in c['image_refs']}
                selected = [by_id[v['before_id']], by_id[v['after_id']]]
                paired = await stage('pair', {'question': g['open_question'], 'allowed_image_ids': [im['evidence_id'] for im in selected]}, selected, 350)
                return 'evidence_screened_unvalidated' if paired['answerable'] and paired['review']['tool'] == c['tool'] else 'quarantine_evidence_pair'

            try:
                r['status'] = await pipeline()
            except StageValidationError as exc:
                r.update(status='schema_rejected', error=str(exc))
            except Exception as exc:
                r.update(status='runtime_error', error=f'{type(exc).__name__}:{exc}')
            save_json(path, r)
            progress[r['status']] += 1
            save_json(folder / 'progress.json', {'completed': sum(progress.values()), 'total': len(packages), 'counts': dict(progress), 'wall_seconds': time.monotonic() - started})
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'kind', 'status', 'error']}), flush=True)
            return r
    try:
        records = await asyncio.gather(*(process(p) for p in packages))
    finally:
        await pool.close()
    export(folder, packages, cases, records, time.monotonic() - started)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=OUT / 'evidence_v18_inputs/packages.jsonl')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    lock = (OUT / 'quality_v16_runner.lock').open('w')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('batch_v18:another_runner_is_active')
    asyncio.run(run(args))
