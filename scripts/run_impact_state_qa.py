import argparse
import asyncio
import html
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.state_qa import STATE_OUT, deterministic_plan, evaluation_input, validate_pair, writer_payload


async def process(pool, packet, prompts, version, planner):
    key_data = {'input_hash': packet['input_hash'], 'prompts': prompts, 'model': pool.model_revision, 'pipeline': 'state_qa_1'}
    if planner != 'model':
        key_data['planner'] = planner
    key = fingerprint(key_data)
    path = OUT / version / 'runs' / (packet['event_id'] + '.json')
    if path.exists():
        existing = read_json(path)
        if existing.get('run_key') == key and existing.get('status') == 'ok':
            return existing
        if existing.get('run_key') != key:
            raise ValueError('process:changed_input_or_prompt_use_new_version:' + packet['event_id'])
    payload = writer_payload(packet)
    record = {'event_id': packet['event_id'], 'run_key': key, 'input_hash': packet['input_hash'], 'version': version, 'creation_method': 'source_annotation_and_public_reference_text_generation_with_video_review', 'human_review_status': 'pending_human_review', 'cache_keys': []}
    try:
        if planner == 'deterministic':
            record['plan'] = deterministic_plan(packet)
        else:
            planned = await pool.call(version + '_plan', prompts['plan'], payload, max_tokens=1800)
            record['plan'] = planned['result']
            record['cache_keys'].append(planned['cache_key'])
        selected = [s for s in record['plan'].get('selected', []) if s.get('reference_support') == 'sufficient'][:2]
        known = {x['id'] for x in packet['evidence_catalog']} | {'comparison_predecessor_state'}
        allowed_rules = {x['id'] for x in packet['procedure']['prerequisites']}
        for intent in selected:
            if not set(intent.get('support_ids', [])) <= known or not set(intent.get('rule_ids', [])) <= allowed_rules:
                raise ValueError('planner:unknown_evidence_or_rule')
        record['selected_intents'] = selected
        if not selected:
            record.update(generation={'qa_pairs': []}, reviews=[], structural_issues=[], status='ok')
        else:
            generated = await pool.call(version + '_generate', prompts['generate'], dict(payload, selected_intents=selected), max_tokens=2200)
            record['generation'] = generated['result']
            record['cache_keys'].append(generated['cache_key'])
            pairs = generated['result'].get('qa_pairs', [])
            if len(pairs) > 2:
                raise ValueError('generate:more_than_two_qa')
            record['structural_issues'] = [validate_pair(packet, pair) for pair in pairs]
            for pair, issues in zip(pairs, record['structural_issues']):
                if pair.get('type') not in {s['type'] for s in selected}:
                    issues.append('type_not_selected')
            record['reviews'] = []
            for pair in pairs:
                reviewed = await pool.call(version + '_review', prompts['review'], dict(payload, qa=pair), packet['image_refs'], max_tokens=1500)
                record['cache_keys'].append(reviewed['cache_key'])
                record['reviews'].append(reviewed['result'])
            record['status'] = 'ok'
    except Exception as exc:
        record.update(status='error', error=f'{type(exc).__name__}:{exc}')
    save_json(path, record)
    print(json.dumps({'event_id': packet['event_id'], 'status': record['status'], 'qa_count': len(record.get('generation', {}).get('qa_pairs', [])), 'decisions': [r.get('decision') for r in record.get('reviews', [])], 'error': record.get('error')}), flush=True)
    return record


def export(records, packets, version):
    by_id = {p['event_id']: p for p in packets}
    candidates, evaluation = [], []
    for r in records:
        if r['status'] != 'ok':
            continue
        for index, pair in enumerate(r['generation']['qa_pairs']):
            qa_id = r['event_id'] + f'__{version}_{index}'
            public_input = evaluation_input(by_id[r['event_id']], pair, qa_id)
            row = dict(pair, qa_id=qa_id, evaluation_id=public_input['qa_id'], event_id=r['event_id'], source_run_key=r['run_key'], machine_review=r['reviews'][index], structural_issues=r['structural_issues'][index], review_status='pending_human_review')
            candidates.append(row)
            evaluation.append(public_input)
    folder = OUT / version
    save_jsonl(folder / 'open_candidates.jsonl', candidates)
    save_jsonl(folder / 'evaluation_inputs.jsonl', evaluation)
    save_jsonl(folder / 'machine_keep_pending_human.jsonl', [q for q in candidates if not q['structural_issues'] and q['machine_review'].get('decision') == 'keep_candidate'])
    summary = {'version': version, 'events': len(records), 'videos': len({p['target']['video_id'] for p in packets}), 'status': dict(Counter(r['status'] for r in records)), 'qa_pairs': len(candidates), 'types': dict(Counter(q['type'] for q in candidates)), 'answer_polarities': dict(Counter(q.get('answer_polarity') for q in candidates)), 'machine_decisions': dict(Counter(q['machine_review'].get('decision') for q in candidates)), 'structural_issue_pairs': sum(bool(q['structural_issues']) for q in candidates), 'deferred_types': dict(Counter(d['type'] for r in records for d in r.get('plan', {}).get('deferred', []))), 'human_reviewed': 0, 'limits': 'Development only. Same-model screening is not accuracy. Illustrated sequence is not an exhaustive mandatory-order graph. All pending_human_review.'}
    save_json(REPORTS / (version + '_summary.json'), summary)
    lines = ['# ' + version + ' 开放题开发样本', '', f"{summary['videos']} 个 front 装配视频；源标注辅助文本生成，视频单独核验；全部待真人审核。", '', '```json', json.dumps(summary, ensure_ascii=False, indent=2), '```']
    cards = ['<!doctype html><meta charset="utf-8"><title>IMPACT state QA review</title><style>body{font:16px sans-serif;max-width:1100px;margin:auto}article{border-top:1px solid #aaa;padding:20px 0}video,img{max-width:100%}pre{white-space:pre-wrap}</style><h1>IMPACT state QA — pending human review</h1>']
    for q in candidates:
        packet = by_id[q['event_id']]
        lines.extend(['', '## ' + q['qa_id'], '', q['question'], '', q['answer'], '', '自动审核：' + json.dumps(q['machine_review'], ensure_ascii=False), '', '结构检查：' + json.dumps(q['structural_issues'])])
        relative = '../state_qa_inputs_v10/media/' + q['event_id']
        cards.append('<article><h2>' + html.escape(q['qa_id']) + '</h2><p>' + html.escape(q['question']) + '</p><p>' + html.escape(q['answer']) + '</p><video controls preload="none" src="' + relative + '/clip.mp4"></video><details><summary>Exact frame anchors</summary><img loading="lazy" src="' + relative + '/contact.jpg"></details><pre>' + html.escape(json.dumps({'review': q['machine_review'], 'claims': q['reference_claims'], 'issues': q['structural_issues']}, ensure_ascii=False, indent=2)) + '</pre></article>')
    (REPORTS / (version + '.md')).write_text('\n'.join(lines) + '\n')
    (folder / 'review.html').write_text('\n'.join(cards))
    print(json.dumps(summary, ensure_ascii=False), flush=True)


async def main(args):
    packets = read_jsonl(args.input)
    if args.limit:
        packets = packets[:args.limit]
    prompts = {s: (ROOT / 'prompts/impact_qa' / args.prompt_version / f'{s}.txt').read_text() for s in ['plan', 'generate', 'review']}
    if args.generation_prompt:
        prompts['generate'] = args.generation_prompt.read_text()
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    gate = asyncio.Semaphore(12)
    async def guarded(packet):
        async with gate:
            return await process(pool, packet, prompts, args.version, args.planner)
    try:
        records = await asyncio.gather(*(guarded(p) for p in packets))
    finally:
        await pool.close()
    export(records, packets, args.version)
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='state_v10')
    parser.add_argument('--prompt-version', default='v10')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--input', type=Path, default=STATE_OUT / 'packets.jsonl')
    parser.add_argument('--planner', choices=['model', 'deterministic'], default='model')
    parser.add_argument('--generation-prompt', type=Path)
    asyncio.run(main(parser.parse_args()))
