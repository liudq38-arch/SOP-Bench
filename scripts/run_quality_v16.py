import argparse
import asyncio
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
from impact_qa.quality_v16 import check_integrity, decide, public_payload, source_payload, validate
from impact_qa.reliable_pool import ReliablePool


def export(folder, cases, records, elapsed):
    lookup = {c['contract_id']: c for c in cases}
    passed, public, quarantined = [], [], []
    kinds = defaultdict(Counter)
    for r in records:
        c = lookup[r['contract_id']]
        kinds[c['kind']][r['disposition']] += 1
        if r['disposition'] != 'model_passed_unvalidated':
            quarantined.append(r)
            continue
        g = r['stages']['generate']
        passed.append({'contract_id': c['contract_id'], 'video_id': c['video_id'], 'kind': c['kind'], 'open_question': g['open_question'], 'answer': g['answer'], 'mcq_question': g['mcq_question'], 'options': c['options'], 'correct_option': c['correct_option'], 'quality': r['decision'], 'claims': g['claims'], 'source_references': c['references'], 'review_record': str(folder / 'runs' / (c['contract_id'] + '.json'))})
        media = [{k: im[k] for k in ['evidence_id', 'path', 'sha256', 'frame_index', 'requested_time_s']} for im in c['image_refs']]
        for form, question in [('open', g['open_question']), ('mcq', g['mcq_question'])]:
            row = {'id': c['contract_id'] + ':' + form, 'video_id': c['video_id'], 'kind': c['kind'], 'format': form, 'question': question, 'images': media}
            if form == 'mcq':
                row['options'] = c['options']
            public.append(row)
    save_jsonl(folder / 'results.jsonl', records)
    save_jsonl(folder / 'model_passed_candidates.jsonl', passed)
    save_jsonl(folder / 'evaluation_inputs.jsonl', public)
    save_jsonl(folder / 'quarantine.jsonl', quarantined)
    summary = {'events': len(cases), 'counts': dict(Counter(r['disposition'] for r in records)), 'by_kind': {k: dict(v) for k, v in kinds.items()}, 'open_qa': len(passed), 'mcq_qa': len(passed), 'wall_seconds_this_invocation': elapsed, 'same_model_roles': True, 'formal_release': False, 'independent_acceptance': False, 'confidence_is_uncalibrated_evidence_grade': True}
    save_json(folder / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


async def run(args):
    cases = read_jsonl(args.input)
    if len({c['contract_id'] for c in cases}) != len(cases):
        raise ValueError('run_v16:duplicate_contract')
    for c in cases:
        check_integrity(c)
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    config_path = ROOT / 'configs/impact_qa/quality_v16.json'
    config = read_json(config_path)
    prompts = {stage: (ROOT / 'prompts/impact_qa/v16' / (stage + '.txt')).read_text() for stage in ['generate', 'blind', 'visual_audit', 'source_audit']}
    sources = [Path(__file__), ROOT / 'impact_qa/quality_v16.py', ROOT / 'scripts/prepare_quality_v16.py', ROOT / 'impact_qa/api.py', ROOT / 'impact_qa/reliable_pool.py', ROOT / 'impact_qa/common.py', ROOT / 'impact_qa/gt_qa.py', config_path] + list((ROOT / 'prompts/impact_qa/v16').glob('*.txt'))
    snapshot = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in config['ports']], config['per_service_concurrency']), folder / 'request_audit')
    manifest = {'sources': snapshot, 'input_sha256': hashlib.sha256(Path(args.input).read_bytes()).hexdigest(), 'model_revision': pool.model_revision, 'config': config, 'events': len(cases)}
    manifest_path = folder / 'frozen_run.json'
    if manifest_path.exists() and read_json(manifest_path) != manifest:
        await pool.close()
        raise ValueError('run_v16:changed_frozen_run_use_new_output_directory')
    save_json(manifest_path, manifest)
    gate = asyncio.Semaphore(12)
    started = time.monotonic()

    async def process(c):
        async with gate:
            path = folder / 'runs' / (c['contract_id'] + '.json')
            key = fingerprint([manifest, c])
            if path.exists():
                r = read_json(path)
                if r['run_key'] != key:
                    raise ValueError('run_v16:changed_checkpoint')
                if r['disposition'] != 'running':
                    return r
            else:
                r = {'contract_id': c['contract_id'], 'kind': c['kind'], 'run_key': key, 'disposition': 'running', 'stages': {}, 'cache_keys': {}}
            async def stage(name, payload, images, tokens):
                if name not in r['stages']:
                    response = await pool.call('quality_v16_' + name, prompts[name], payload, images, max_tokens=tokens)
                    r['cache_keys'][name] = response['cache_key']
                    r['stages'][name] = validate(name, response['result'], c, r['stages'].get('generate'))
                    save_json(path, r)
                return r['stages'][name]
            active = 'generate'
            try:
                g = await stage('generate', source_payload(c), c['image_refs'], 800)
                active = 'blind'
                b = await stage('blind', public_payload(c, g['open_question']), c['image_refs'], 550)
                active = 'audits'
                vision = {**public_payload(c, g['open_question']), 'proposed_qa': {k: g[k] for k in ['open_question', 'answer', 'mcq_question']}, 'claims': [{'claim': cl['claim'], 'image_ids': cl['image_ids']} for cl in g['claims']], 'options': c['options'], 'blind_answer': b}
                source = {**source_payload(c), 'proposed_qa': g, 'blind_answer': b}
                results = await asyncio.gather(stage('visual_audit', vision, c['image_refs'], 1100), stage('source_audit', source, [], 600), return_exceptions=True)
                errors = [str(v) for v in results if isinstance(v, Exception)]
                if errors:
                    raise ValueError(';'.join(errors))
                r['decision'] = decide(c, r['stages'], config['required_grade'])
                r['disposition'] = r['decision']['disposition']
            except Exception as exc:
                r.update(disposition='schema_or_runtime_error', error=f'{active}:{type(exc).__name__}:{exc}')
            save_json(path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'kind', 'disposition', 'error']}), flush=True)
            return r
    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    export(folder, cases, records, time.monotonic() - started)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    lock = (OUT / 'quality_v16_runner.lock').open('w')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('run_v16:another_runner_is_active')
    asyncio.run(run(args))
