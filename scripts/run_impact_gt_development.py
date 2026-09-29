import argparse
import asyncio
import hashlib
import html
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_jsonl, save_json, save_jsonl
from run_impact_gt_qa import process


def public_input(c, question):
    return {'question': question, 'public_procedure': c['public_procedure'], 'clip_start_s': c['start_frame'] / 30, 'clip_end_s_exclusive': (c['end_frame_inclusive'] + 1) / 30, 'evidence_description': 'Native target clip sampled to 16 video frames plus four exact original frames. Continuous review clip available; model does not observe all video frames.'}


def export(records, contracts, version):
    lookup = {c['contract_id']: c for c in contracts}
    rows, mcqs, evaluation = [], [], []
    cards = ['<!doctype html><meta charset="utf-8"><title>IMPACT GT review</title><style>body{font:16px sans-serif;max-width:1150px;margin:auto}article{border-top:1px solid #888;padding:20px 0}video,img{max-width:100%}pre{white-space:pre-wrap}textarea{width:95%;min-height:90px}</style><h1>IMPACT review: answer before revealing GT</h1><p>Research candidates; not human-approved. Record independent answer and evidence time before opening GT. Text typed here is not saved automatically.</p>']
    for r in records:
        if r['status'] != 'ok':
            continue
        c, g = lookup[r['contract_id']], r['generation']
        source = r['source_review']
        passed = source.get('decision') == 'pass' and not source.get('unsupported_claims') and all(source.get(k) is True for k in ['source_supported', 'answer_equivalent_to_gt', 'open_question_answer_match', 'mcq_unique_answer', 'scope_valid'])
        qa_id = c['contract_id'] + '_open'
        row = {'qa_id': qa_id, 'contract_id': c['contract_id'], 'video_id': c['video_id'], 'kind': c['kind'], 'question': g['question'], 'answer': g['answer'], 'gt_reference_answer': c['canonical_answer'], 'answer_polarity': c['answer_polarity'], 'source_gate_passed': passed, 'source_review': source, 'blind_visual_review': r['visual_review'], 'generator_visibility': g['visual_support'], 'generator_visual_limitation': g.get('visual_limitation'), 'human_review_status': 'pending_human_review', 'source_references': c['references'], 'S': 'machine_pass' if passed else 'needs_review', 'V': 'pending_direct_review', 'T': 'pending_direct_review', 'Q': 'pending_direct_review', 'M': 'pending_direct_review', 'D': 'machine_pass', 'agent_decision': 'pending_direct_review'}
        rows.append(row)
        choices = c['choice_texts'][:]
        shift = int(fingerprint(c['contract_id'])[:8], 16) % 3
        choices = choices[shift:] + choices[:shift]
        options = dict(zip('ABC', choices))
        mcq = {'qa_id': c['contract_id'] + '_mcq', 'contract_id': c['contract_id'], 'question': g['mcq_question'], 'options': options, 'correct_answer': next(k for k, v in options.items() if v == c['choice_texts'][0]), 'answer_text': c['choice_texts'][0], 'human_review_status': 'pending_human_review'}
        mcqs.append(mcq)
        for form, item in [('open', row), ('mcq', mcq)]:
            public = dict(public_input(c, item['question']), qa_id='qa_' + fingerprint(item['qa_id'])[:20], format=form, video_path=c['clip_path'], frame_paths=[im['path'] for im in c['image_refs'] if im.get('media_type') != 'video'], frame_times_s=[im['requested_time_s'] for im in c['image_refs'] if im.get('media_type') != 'video'])
            if form == 'mcq':
                public['options'] = options
            evaluation.append(public)
        rel_clip = os.path.relpath(c['clip_path'], OUT / version)
        rel_sheet = os.path.relpath(c['contact_sheet'], OUT / version)
        cards.append('<article><h2>' + html.escape(c['contract_id']) + '</h2><p>' + html.escape(g['question']) + '</p><video controls preload="none" src="' + html.escape(rel_clip) + '"></video><p>Original interval: ' + f'{c["start_frame"] / 30:.3f}–{(c["end_frame_inclusive"] + 1) / 30:.3f}s' + '</p><textarea placeholder="Independent answer, evidence timestamps, uncertainty. Save separately."></textarea><details><summary>Show timestamped frame sheet</summary><img loading="lazy" src="' + html.escape(rel_sheet) + '"></details><details><summary>Reveal GT, generated answer and review</summary><p>Generated: ' + html.escape(g['answer']) + '</p><p>GT: ' + html.escape(c['canonical_answer']) + '</p><p>' + html.escape(g['mcq_question']) + '</p><pre>' + html.escape(json.dumps({'options': options, 'correct': mcq['correct_answer'], 'facts': c['facts'], 'source': source, 'blind_visual': r['visual_review']}, ensure_ascii=False, indent=2)) + '</pre></details></article>')
    folder = OUT / version
    save_jsonl(folder / 'open_candidates.jsonl', rows)
    save_jsonl(folder / 'mcq_candidates.jsonl', mcqs)
    save_jsonl(folder / 'evaluation_inputs.jsonl', evaluation)
    save_jsonl(folder / 'review_records_template.jsonl', [{'contract_id': r['contract_id'], 'reviewer_kind': None, 'independent_answer': None, 'evidence_times_s': [], 'S': None, 'V': None, 'T': None, 'Q': None, 'M': None, 'D': None, 'decision': None, 'reason': None} for r in rows])
    (folder / 'review.html').write_text('\n'.join(cards))
    summary = {'version': version, 'status': dict(Counter(r['status'] for r in records)), 'contracts': len(rows), 'mcq': len(mcqs), 'participants': len({c['video_id'].split('_')[0] for c in contracts}), 'kinds': dict(Counter(r['kind'] for r in rows)), 'source_gate_pass': sum(r['source_gate_passed'] for r in rows), 'generator_visibility': dict(Counter(r['generator_visibility'] for r in rows)), 'blind_visual_answerability': dict(Counter(r['blind_visual_review'].get('answerability') for r in rows)), 'answer_polarities': dict(Counter(r['answer_polarity'] for r in rows)), 'mcq_positions': dict(Counter(r['correct_answer'] for r in mcqs)), 'unique_questions': len({r['question'] for r in rows}), 'human_reviewed': 0, 'independent_acceptance_passed': False}
    save_json(REPORTS / (version + '_summary.json'), summary)
    print(json.dumps(summary, indent=2), flush=True)


async def main(args):
    contracts = read_jsonl(args.input)
    if args.limit:
        contracts = contracts[:args.limit]
    prompts = {s: (ROOT / 'prompts/impact_qa/v12' / (s + '.txt')).read_text() for s in ['generate', 'source_review', 'visual_review']}
    code_hash = fingerprint({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), ROOT / 'scripts/run_impact_gt_qa.py', ROOT / 'impact_qa/gt_development.py']})
    import run_impact_gt_qa
    run_impact_gt_qa.public_payload = public_input
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
    parser.add_argument('--input', type=Path, default=OUT / 'gt_v12_inputs/contracts.jsonl')
    parser.add_argument('--version', default='gt_v12_development')
    parser.add_argument('--limit', type=int, default=0)
    asyncio.run(main(parser.parse_args()))
