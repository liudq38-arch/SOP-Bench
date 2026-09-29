import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from refine_impact_gt_development import phrase
from run_impact_gt_development import export
import run_impact_gt_qa


VERSION = 'gt_v12_2_development'
ORIGINAL_PRIVATE = run_impact_gt_qa.private_payload


def time_basis(c):
    start = c['start_frame'] / c['fps']
    return {'native_video_timestamps': 'relative to this clip, starting at zero', 'original_recording_time_formula': 'original_time_s = clip_start_s + native_video_time_s', 'clip_start_s': start, 'clip_duration_s': (c['end_frame_inclusive'] - c['start_frame'] + 1) / c['fps'], 'exact_anchor_images_in_order': [{'image_number': i + 1, 'original_time_s': im['requested_time_s'], 'clip_relative_time_s': im['requested_time_s'] - start} for i, im in enumerate(im for im in c['image_refs'] if im.get('media_type') != 'video')]}


def public_input(c, question):
    return {'question': question, 'public_procedure': c['public_procedure'], 'media_time_basis': time_basis(c), 'clip_start_s': c['start_frame'] / c['fps'], 'clip_end_s_exclusive': (c['end_frame_inclusive'] + 1) / c['fps'], 'evidence_description': 'Target clip sampled into 16 frames and four exact anchor images; native video timestamps are clip-relative; anchors and public interval are original recording times.'}


def private_input(c):
    return dict(ORIGINAL_PRIVATE(c), media_time_basis=time_basis(c))


async def main():
    base = read_jsonl(OUT / 'gt_v12_inputs/contracts.jsonl')
    refined = {c['contract_id']: c for c in read_jsonl(OUT / 'gt_v12_1_inputs/contracts.jsonl')}
    contracts = []
    for b in base:
        c = copy.deepcopy(refined.get(b['contract_id'], b))
        c['generation_parent_version'] = 'gt_v12_1_development' if b['contract_id'] in refined else 'gt_v12_development'
        if c['kind'] == 'observed_order':
            x, y = sorted([phrase(c['facts']['first_action']), phrase(c['facts']['second_action'])])
            q = f'Which did I start first: {x} or {y}?'
            c['mcq_question_proposition'] = q
            if c['answer_polarity'] == 'descriptive':
                c['question_proposition'] = q
            c['question_pair_order'] = 'alphabetical_action_phrase_independent_of_temporal_order'
        c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
        contracts.append(c)
    save_jsonl(OUT / 'gt_v12_2_inputs/contracts.jsonl', contracts)
    prompts = {s: (ROOT / 'prompts/impact_qa/v12_2' / (s + '.txt')).read_text() for s in ['generate', 'source_review', 'visual_review']}
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    run_impact_gt_qa.public_payload = public_input
    run_impact_gt_qa.private_payload = private_input
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    gate = asyncio.Semaphore(12)

    async def process(c):
        async with gate:
            if c['kind'] == 'observed_order':
                return await run_impact_gt_qa.process(pool, c, prompts, VERSION, code_hash)
            parent = OUT / c['generation_parent_version'] / 'runs' / (c['contract_id'] + '.json')
            record = read_json(parent)
            assert record['status'] == 'ok'
            path = OUT / VERSION / 'runs' / parent.name
            key = fingerprint({'parent': record['run_key'], 'input': c['input_hash'], 'prompt': prompts['visual_review'], 'code': code_hash, 'model': pool.model_revision})
            if path.exists():
                old = read_json(path)
                if old['run_key'] != key:
                    raise ValueError('v12_2:changed_run_use_new_version:' + c['contract_id'])
                if old['status'] == 'ok':
                    return old
            record.update(parent_run_path=str(parent), run_key=key, status='running', generation_and_source_reused=True)
            try:
                visual = await pool.call(VERSION + '_visual_review', prompts['visual_review'], public_input(c, record['generation']['question']), c['image_refs'], max_tokens=750)
                record['previous_visual_review'] = record['visual_review']
                record['visual_review'] = visual['result']
                record['cache_keys'] = record['cache_keys'][:2] + [visual['cache_key']]
                record['status'] = 'ok'
            except Exception as exc:
                record.update(status='error', error=f'v12_2_visual:{type(exc).__name__}:{exc}')
            save_json(path, record)
            print(json.dumps({'id': c['contract_id'], 'status': record['status'], 'visual': record.get('visual_review', {}).get('answerability')}), flush=True)
            return record

    try:
        records = await asyncio.gather(*(process(c) for c in contracts))
    finally:
        await pool.close()
    export(records, contracts, VERSION)
    save_jsonl(OUT / VERSION / 'evaluation_inputs.jsonl', [dict(public_input(c, r['generation']['question' if form == 'open' else 'mcq_question']), qa_id='qa_' + fingerprint(c['contract_id'] + '_' + form)[:20], format=form, video_path=c['clip_path'], frame_paths=[im['path'] for im in c['image_refs'] if im.get('media_type') != 'video'], **({'options': mcqs[c['contract_id']]['options']} if form == 'mcq' else {})) for mcqs in [{x['contract_id']: x for x in read_jsonl(OUT / VERSION / 'mcq_candidates.jsonl')}] for c, r in zip(contracts, records) if r['status'] == 'ok' for form in ['open', 'mcq']])
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
