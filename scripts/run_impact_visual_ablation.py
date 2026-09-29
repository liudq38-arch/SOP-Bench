import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl


def public_payload(c):
    refs = c['image_refs']
    return {'question': c['question'], 'public_procedure': c['public_procedure'], 'original_start_s': c['start_frame'] / 30, 'original_end_s_exclusive': (c['end_frame_inclusive'] + 1) / 30, 'evidence_protocol': 'All event-image timestamps are original recording seconds. The first four images are full-frame context; the next sixteen show the target, with original recording times. They may overlap in time and may be spatial crops, not a second execution. Public annotation-assisted sampling protocol; no action names attached to frames. Generic manual references, when supplied, are not event frames and their placeholder time zero is not a video timestamp.', 'event_images': [{'id': im['evidence_id'], 'original_time_s': im['requested_time_s']} for im in refs if im['view'] == 'front'], 'reference_images': [im['evidence_id'] for im in refs if im['view'] != 'front']}


async def main(args):
    cases = read_jsonl(OUT / 'gt_v13_inputs/cases.jsonl')
    if args.limit:
        cases = cases[:args.limit]
    prompt = (ROOT / 'prompts/impact_qa/v13/visual_review.txt').read_text()
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    gate = asyncio.Semaphore(12)

    async def process(c):
        async with gate:
            path = OUT / 'gt_v13' / 'runs' / (c['contract_id'] + '_' + c['condition'] + '.json')
            key = fingerprint({'input': c['input_hash'], 'prompt': prompt, 'code': code_hash, 'model': pool.model_revision})
            if path.exists():
                previous = read_json(path)
                if previous['run_key'] != key:
                    raise ValueError('visual_ablation:changed_run_use_new_version:' + path.name)
                if previous['status'] == 'ok':
                    return previous
            record = {'contract_id': c['contract_id'], 'condition': c['condition'], 'run_key': key, 'status': 'running'}
            try:
                payload = public_payload(c)
                assert not {'gt_answer', 'facts', 'kind', 'answer_polarity', 'selection_reason'}.intersection(payload)
                result = await pool.call('gt_v13_visual', prompt, payload, c['image_refs'], max_tokens=850)
                answer = result['result']
                assert answer['answerability'] in ['answerable', 'uncertain', 'unanswerable']
                record.update(status='ok', visual_review=answer, cache_key=result['cache_key'])
            except Exception as exc:
                record.update(status='error', error=f'visual_ablation:{type(exc).__name__}:{exc}')
            save_json(path, record)
            print(json.dumps({'id': c['contract_id'], 'condition': c['condition'], 'status': record['status'], 'answer': record.get('visual_review', {}).get('answer'), 'error': record.get('error')}), flush=True)
            return record

    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(OUT / 'gt_v13/results.jsonl', records)
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    asyncio.run(main(parser.parse_args()))
