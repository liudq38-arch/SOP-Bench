import argparse
import asyncio
import hashlib
import html
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import validate_generation, verify_reference


def private_payload(c):
    return {k: c[k] for k in ['contract_id', 'kind', 'fps', 'start_frame', 'end_frame_inclusive', 'public_procedure', 'facts', 'references', 'question_proposition', 'canonical_answer', 'answer_polarity', 'mcq_question_proposition', 'choice_texts', 'forbidden_claims']}


def public_payload(c, question):
    return {'question': question, 'public_procedure': c['public_procedure'], 'clip_start_s': c['start_frame'] / c['fps'], 'clip_end_s_exclusive': (c['end_frame_inclusive'] + 1) / c['fps'], 'evidence_description': 'Timestamped original front-view frames, including within-clip action boundaries; sampling is not continuous video.'}


async def process(pool, c, prompts, version, code_hash):
    path = OUT / version / 'runs' / (c['contract_id'] + '.json')
    key = fingerprint({'input': c['input_hash'], 'prompts': prompts, 'model': pool.model_revision, 'code': code_hash})
    if path.exists():
        old = read_json(path)
        if old['run_key'] != key:
            raise ValueError('gt_pipeline:changed_run_use_new_version:' + c['contract_id'])
        if old['status'] == 'ok':
            return old
    record = {'contract_id': c['contract_id'], 'run_key': key, 'status': 'running', 'cache_keys': [], 'human_review_status': 'pending_human_review'}
    try:
        for ref in c['references']:
            verify_reference(ref)
        payload = private_payload(c)
        gen = await pool.call(version + '_generate', prompts['generate'], payload, c['image_refs'], max_tokens=650)
        record['generation'] = gen['result']
        record['cache_keys'].append(gen['cache_key'])
        record['structural_issues'] = validate_generation(c, gen['result'])
        if record['structural_issues']:
            raise ValueError('gt_generation:' + ','.join(record['structural_issues']))
        save_json(path, record)
        source, visual = await asyncio.gather(
            pool.call(version + '_source_review', prompts['source_review'], dict(payload, proposed_qa=gen['result']), max_tokens=700),
            pool.call(version + '_visual_review', prompts['visual_review'], public_payload(c, gen['result']['question']), c['image_refs'], max_tokens=750),
        )
        record.update(source_review=source['result'], visual_review=visual['result'], status='ok')
        record['cache_keys'].extend([source['cache_key'], visual['cache_key']])
    except Exception as exc:
        record.update(status='error', error=f'{type(exc).__name__}:{exc}')
    save_json(path, record)
    print(json.dumps({'id': c['contract_id'], 'status': record['status'], 'source': record.get('source_review', {}).get('decision'), 'visual': record.get('visual_review', {}).get('answerability'), 'error': record.get('error')}), flush=True)
    return record


def export(records, contracts, version):
    lookup = {c['contract_id']: c for c in contracts}
    rows, mcqs, evaluation = [], [], []
    cards = ['<!doctype html><meta charset="utf-8"><title>GT-grounded QA</title><style>body{font:16px sans-serif;max-width:1100px;margin:auto}article{border-top:1px solid #aaa;padding:20px 0}img{max-width:100%}pre{white-space:pre-wrap}</style><h1>GT-grounded QA development candidates — pending human review</h1>']
    for r in records:
        if r['status'] != 'ok':
            continue
        c, g = lookup[r['contract_id']], r['generation']
        review = r['source_review']
        passed = review.get('decision') == 'pass' and all(review.get(k) is True for k in ['source_supported', 'answer_equivalent_to_gt', 'open_question_answer_match', 'mcq_unique_answer', 'scope_valid']) and not review.get('unsupported_claims')
        row = {'qa_id': c['contract_id'] + '_open', 'contract_id': c['contract_id'], 'kind': c['kind'], 'question': g['question'], 'answer': g['answer'], 'gt_reference_answer': c['canonical_answer'], 'answer_polarity': c['answer_polarity'], 'source_review': review, 'blind_visual_review': r['visual_review'], 'generator_visibility': g['visual_support'], 'generator_visual_limitation': g.get('visual_limitation'), 'source_gate_passed': passed, 'visual_answer_agreement': 'pending_direct_review', 'human_review_status': 'pending_human_review', 'source_references': c['references']}
        rows.append(row)
        choices = c['choice_texts'][:]
        shift = int(fingerprint(c['contract_id'])[:8], 16) % 3
        choices = choices[shift:] + choices[:shift]
        options = dict(zip('ABC', choices))
        mcq = {'qa_id': c['contract_id'] + '_mcq', 'contract_id': c['contract_id'], 'kind': c['kind'], 'question': g['mcq_question'], 'options': options, 'correct_answer': next(k for k, v in options.items() if v == c['choice_texts'][0]), 'answer_text': c['choice_texts'][0], 'distractor_method': 'fixed_same_dimension_mutually_exclusive_alternatives', 'human_review_status': 'pending_human_review'}
        mcqs.append(mcq)
        for form, item in [('open', row), ('mcq', mcq)]:
            public = dict(public_payload(c, item['question']), qa_id='qa_' + fingerprint(item['qa_id'])[:20], format=form, frame_paths=[im['path'] for im in c['image_refs']], frame_times_s=[im['requested_time_s'] for im in c['image_refs']])
            if form == 'mcq':
                public['options'] = options
            evaluation.append(public)
        cards.append('<article><h2>' + html.escape(c['contract_id'] + ' / ' + c['kind']) + '</h2><p>' + html.escape(g['question']) + '</p><p>' + html.escape(g['answer']) + '</p><p>GT: ' + html.escape(c['canonical_answer']) + '</p><p>' + html.escape(g['mcq_question']) + '</p><pre>' + html.escape(json.dumps(options, ensure_ascii=False)) + '</pre><img loading="lazy" src="../gt_v11_inputs/' + c['contract_id'] + '.jpg"><pre>' + html.escape(json.dumps({'source': review, 'independent_visual': r['visual_review'], 'generator': g}, ensure_ascii=False, indent=2)) + '</pre></article>')
    folder = OUT / version
    save_jsonl(folder / 'open_candidates.jsonl', rows)
    save_jsonl(folder / 'mcq_candidates.jsonl', mcqs)
    save_jsonl(folder / 'evaluation_inputs.jsonl', evaluation)
    (folder / 'review.html').write_text('\n'.join(cards))
    summary = {'version': version, 'status': dict(Counter(r['status'] for r in records)), 'open_count': len(rows), 'mcq_count': len(mcqs), 'types': dict(Counter(q['kind'] for q in rows)), 'answer_polarity': dict(Counter(q['answer_polarity'] for q in rows)), 'unique_questions': len({q['question'] for q in rows}), 'source_gate_pass': sum(q['source_gate_passed'] for q in rows), 'blind_visual_answerability': dict(Counter(q['blind_visual_review'].get('answerability') for q in rows)), 'generator_visibility': dict(Counter(q['generator_visibility'] for q in rows)), 'mcq_answer_positions': dict(Counter(q['correct_answer'] for q in mcqs)), 'human_reviewed': 0, 'accuracy': None, 'note': 'Generation sees visual evidence and GT; blind visual review sees neither GT answer nor source execution labels. A confident visual answer can still disagree; direct review required.'}
    save_json(REPORTS / (version + '_summary.json'), summary)
    print(json.dumps(summary, indent=2))


async def main(args):
    contracts = read_jsonl(OUT / 'gt_v11_inputs/contracts.jsonl')
    if args.limit:
        contracts = contracts[:args.limit]
    prompts = {s: (ROOT / 'prompts/impact_qa/v11' / (s + '.txt')).read_text() for s in ['generate', 'source_review', 'visual_review']}
    code_hash = fingerprint({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), ROOT / 'impact_qa/gt_qa.py']})
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    gate = asyncio.Semaphore(12)
    async def guarded(c):
        async with gate:
            return await process(pool, c, prompts, args.version, code_hash)
    try:
        records = await asyncio.gather(*(guarded(c) for c in contracts))
    finally:
        await pool.close()
    export(records, contracts, args.version)
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='gt_v11')
    parser.add_argument('--limit', type=int, default=0)
    asyncio.run(main(parser.parse_args()))
