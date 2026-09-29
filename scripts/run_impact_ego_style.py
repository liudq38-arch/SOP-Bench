import asyncio
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl


ARGS = argparse.ArgumentParser()
ARGS.add_argument('--version', choices=['v8', 'v9'], default='v8')
PROMPT_VERSION = ARGS.parse_args().version
VERSION = 'ego_style_' + PROMPT_VERSION
FIELDS = ['annotation.action', 'annotation.hand', 'annotation.phase', 'annotation.anomaly_types', 'visual_note.answer']


def make_input(event, note):
    return {
        'task': 'angle grinder disassembly' if 'Disassembly' in event['video_id'] else 'angle grinder reassembly',
        'target_interval_s': [event['start_s'], event['end_s_exclusive']],
        'annotation': {key: event[key] for key in ['hand', 'action', 'phase', 'anomaly_types']},
        'visual_note': {key: note[key] for key in ['question', 'answer', 'limits', 'creation_method', 'reviewed_artifact']},
        'allowed_source_fields': FIELDS,
    }


def validate(record):
    pairs = record['generation'].get('qa_pairs', [])
    reviews = record['review'].get('reviews', [])
    issues = []
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= 2:
        return ['invalid_pair_count']
    if sorted(r.get('qa_index', -1) for r in reviews) != list(range(len(pairs))):
        issues.append('review_indices_mismatch')
    for i, pair in enumerate(pairs):
        if not all(isinstance(pair.get(k), str) and pair[k].strip() for k in ['question', 'answer']):
            issues.append(f'{i}:invalid_text')
        refs = pair.get('source_fields', [])
        if not refs or any(x not in FIELDS for x in refs):
            issues.append(f'{i}:invalid_source_fields')
        if pair.get('evidence_basis') not in ['annotation', 'visual_note', 'mixed']:
            issues.append(f'{i}:invalid_evidence_basis')
        if pair.get('dimension') in ['correctness', 'corrective_action'] and 'annotation.phase' not in refs:
            issues.append(f'{i}:missing_phase_source')
        if pair.get('dimension') == 'error_description' and 'annotation.anomaly_types' not in refs:
            issues.append(f'{i}:missing_anomaly_source')
    return issues


async def process(pool, event, note, prompts):
    previous = read_json(OUT / 'runs/v7/development' / (event['event_id'] + '.json'))
    payload = make_input(event, note)
    key = fingerprint({'payload': payload, 'prompts': prompts, 'model_revision': pool.model_revision, 'evidence': previous['evidence'], 'pipeline': 'ego_style_2_per_pair_review'})
    path = OUT / VERSION / (event['event_id'] + '.json')
    if path.exists():
        cached = read_json(path)
        if cached.get('run_key') == key and cached.get('status') == 'ok':
            return cached
    record = {'event_id': event['event_id'], 'event': event, 'version': VERSION, 'run_key': key, 'input': payload, 'creation_method': 'annotation_and_research_agent_note_assisted_text_generation', 'human_review_status': 'pending_human_review'}
    try:
        generated = await pool.call(VERSION + '_generate', prompts['generate'], payload, max_tokens=1200)
        record['generation'] = generated['result']
        reviews, conflicts = [], []
        record['cache_keys'] = [generated['cache_key']]
        for i, pair in enumerate(generated['result'].get('qa_pairs', [])):
            reviewed = await pool.call(VERSION + '_review_pair', prompts['review'], dict(payload, qa_pairs=[pair]), previous['evidence'], max_tokens=1000)
            result = reviewed['result']
            single = result.get('reviews', [])
            if len(single) != 1 or single[0].get('qa_index') != 0:
                raise ValueError(f'review_pair_{i}: invalid_single_review')
            reviews.append(dict(single[0], qa_index=i))
            conflicts.extend(result.get('source_conflicts', []))
            record['cache_keys'].append(reviewed['cache_key'])
        record['review'] = {'reviews': reviews, 'source_conflicts': conflicts, 'human_review_required': True}
        record['structural_issues'] = validate(record)
        record['status'] = 'ok'
    except Exception as exc:
        record.update(status='error', error=f'{type(exc).__name__}: {exc}')
    save_json(path, record)
    print(json.dumps({'event_id': event['event_id'], 'status': record['status'], 'issues': record.get('structural_issues'), 'error': record.get('error')}), flush=True)
    return record


async def main():
    events = read_jsonl(OUT / 'development_events.jsonl')
    notes = {r['event_id']: r for r in read_jsonl(OUT / 'agent_proposed_revisions.jsonl')}
    prompts = {stage: (ROOT / 'prompts/impact_qa' / PROMPT_VERSION / (stage + '.txt')).read_text() for stage in ['generate', 'review']}
    save_json(REPORTS / (VERSION + '_first10.json'), [make_input(e, notes[e['event_id']]) for e in events[:10]])
    urls = [f'http://127.0.0.1:{port}/v1' for port in [8000, 8001, 8002]]
    pool = Pool(urls, 4)
    gate = asyncio.Semaphore(12)
    async def guarded(event):
        async with gate:
            return await process(pool, event, notes[event['event_id']], prompts)
    try:
        records = await asyncio.gather(*(guarded(e) for e in events))
    finally:
        await pool.close()
    candidates = []
    for r in records:
        if r['status'] != 'ok':
            continue
        for i, pair in enumerate(r['generation']['qa_pairs']):
            review = next((x for x in r['review']['reviews'] if x.get('qa_index') == i), {})
            candidates.append(dict(pair, qa_id=r['event_id'] + f'__{PROMPT_VERSION}_{i}', event_id=r['event_id'], phase=r['event']['phase'], source_run_key=r['run_key'], source_annotation=r['event']['annotation_ref'], creation_method=r['creation_method'], machine_review=review, structural_issues=r['structural_issues'], review_status='pending_human_review'))
    save_jsonl(OUT / VERSION / 'candidates.jsonl', candidates)
    summary = {'events': len(records), 'status': dict(Counter(r['status'] for r in records)), 'qa_pairs': len(candidates), 'decisions': dict(Counter(r['machine_review'].get('decision', 'missing') for r in candidates)), 'dimensions': dict(Counter(r['dimension'] for r in candidates)), 'structural_issue_events': sum(bool(r.get('structural_issues')) for r in records), 'human_reviewed': 0, 'limits': 'Development-only; supplied research-agent visual notes; same-model screening is not accuracy or human validation.'}
    save_json(REPORTS / (VERSION + '_summary.json'), summary)
    lines = ['# EgoErrorVQA 风格开发对照 ' + PROMPT_VERSION, '', '原标注与研究代理目视描述辅助生成，全部待真人审核；自动 pass 不是准确率。', '', '```json', json.dumps(summary, ensure_ascii=False, indent=2), '```']
    for r in candidates:
        lines.extend(['', '## ' + r['qa_id'], '', r['question'], '', r['answer'], '', '```json', json.dumps({'phase': r['phase'], 'sources': r['source_fields'], 'review': r['machine_review']}, ensure_ascii=False, indent=2), '```'])
    (REPORTS / (VERSION + '.md')).write_text('\n'.join(lines) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
