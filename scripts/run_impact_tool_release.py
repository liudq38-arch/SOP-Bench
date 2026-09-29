import argparse
import asyncio
import hashlib
import html
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.reliable_pool import ReliablePool


FOLDER = OUT / 'gt_v14_tools'


async def main(limit=0):
    cases = read_jsonl(OUT / 'gt_v14_tool_inputs/contracts.jsonl')
    if limit:
        cases = cases[:limit]
    prompts = {name: (ROOT / ('prompts/impact_qa/v14/tool_' + name + '.txt')).read_text() for name in ['generate', 'visual']}
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), FOLDER / 'request_audit')
    gate = asyncio.Semaphore(12)
    code_hash = fingerprint({p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ['scripts/run_impact_tool_release.py', 'impact_qa/reliable_pool.py']})

    async def process(c):
        async with gate:
            path = FOLDER / 'runs' / (c['contract_id'] + '.json')
            run_key = fingerprint([c['input_hash'], prompts, code_hash, pool.model_revision])
            if path.exists():
                previous = read_json(path)
                assert previous['run_key'] == run_key, 'tool_run:version_changed'
                if previous['status'] == 'ok':
                    return previous
            record = {'contract_id': c['contract_id'], 'run_key': run_key, 'status': 'running'}
            try:
                private = {k: c[k] for k in ['question', 'canonical_answer', 'source_label', 'hand', 'target_interval_exclusive']}
                gen = await pool.call('gt_v14_tool_generate', prompts['generate'], private, c['image_refs'], max_tokens=180)
                assert gen['result'] == {'question': c['question'], 'answer': c['canonical_answer']}, 'generation:canonical_wording_mismatch'
                public = {'question': gen['result']['question'], 'clip_start_original_s': c['start_frame'] / 30, 'clip_end_original_s_exclusive': (c['end_frame_inclusive'] + 1) / 30}
                visual = await pool.call('gt_v14_tool_visual', prompts['visual'], public, c['image_refs'], max_tokens=300)
                v = visual['result']
                assert v['tool'] in ['screwdriver', 'wrench', 'pliers', 'unknown']
                assert v['answerability'] in ['answerable', 'uncertain']
                assert isinstance(v['pickup_visible'], bool)
                ids = {im['evidence_id'] for im in c['image_refs']}
                assert set(v['evidence_image_ids']) <= ids, 'visual:invalid_evidence_id'
                assert len(v['visible_evidence'].split()) <= 45, 'visual:overlong_evidence'
                verdict = 'abstain' if v['answerability'] != 'answerable' or not v['pickup_visible'] or v['tool'] == 'unknown' else ('short_answer_match' if v['tool'] == c['tool'] else 'short_answer_conflict')
                record.update(status='ok', generation=gen['result'], visual_review=v, short_answer_comparison=verdict, cache_keys=[gen['cache_key'], visual['cache_key']])
            except Exception as exc:
                record.update(status='error', error=f'tool_run:{type(exc).__name__}:{exc}')
            save_json(path, record)
            print(json.dumps({k: record.get(k) for k in ['contract_id', 'status', 'short_answer_comparison', 'error']}), flush=True)
            return record

    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(FOLDER / 'results.jsonl', records)
    candidates, evaluation, cards = [], [], []
    for c, r in zip(cases, records):
        if r['status'] == 'ok':
            candidates.append(dict(r, video_id=c['video_id'], kind=c['kind'], references=c['references'], options=c['options'], correct_option=c['correct_option'], human_review_status='pending_human_review', quality_acceptance=False))
            for form in ['open', 'mcq']:
                evaluation.append({'qa_id': fingerprint([c['contract_id'], form])[:24], 'format': form, 'question': c['question'], 'image_paths': [im['path'] for im in c['image_refs']], 'original_times_s': [im['requested_time_s'] for im in c['image_refs']], 'annotation_assisted_sampling': True, **({'options': c['options']} if form == 'mcq' else {})})
        rel = os.path.relpath(c['contact_sheet'], FOLDER)
        cards.append('<article><h2>' + html.escape(c['contract_id']) + '</h2><p>' + html.escape(c['question']) + '</p><img loading="lazy" src="' + html.escape(rel) + '"><details><summary>揭示GT与模型复核</summary><pre>' + html.escape(json.dumps({'gt': c['canonical_answer'], 'options': c['options'], 'result': r}, ensure_ascii=False, indent=2)) + '</pre></details></article>')
    save_jsonl(FOLDER / 'candidates.jsonl', candidates)
    save_jsonl(FOLDER / 'evaluation_inputs.jsonl', evaluation)
    (FOLDER / 'review.html').write_text('<!doctype html><meta charset="utf-8"><title>v14工具开发复查</title><style>body{max-width:1200px;margin:auto;font:16px sans-serif}img{max-width:100%}pre{white-space:pre-wrap}article{border-bottom:2px solid #aaa}</style><h1>开发复查，非独立验收</h1>' + ''.join(cards))
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    asyncio.run(main(parser.parse_args().limit))
