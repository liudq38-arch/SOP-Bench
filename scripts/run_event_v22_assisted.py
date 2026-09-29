import asyncio
import fcntl
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, fingerprint, read_json, read_jsonl, save_json
from impact_qa.event_v22 import CONFIG, FOLDER, Pool, base_payload, gt_rows, render_answer, verify_events


async def process(pool, record, source):
    case = record['case']
    clip = next(c for c in record['clips'] if c['clip_id'] == source['clip_id'])
    output = {'case_id': source['case_id'], 'clip_id': source['clip_id'], 'branch': 'agent_assisted', 'human_gold': False, 'autonomous_generation': False, 'reference_hash': fingerprint(source), 'status': 'error', 'formal_release': False}
    try:
        events = source['events']
        verification = await verify_events(pool, case, clip, events, 'assisted/' + clip['clip_id'])
        output['verification'] = verification
        supported = {v['claim_id'] for v in verification['verdicts'] if v['verdict'] == 'supported'}
        accepted = [e for e in events if e['event_id'] in supported]
        output['events'] = events
        output['accepted_events'] = accepted
        if not accepted:
            output['status'] = 'held'
            return output
        ids = {i for e in accepted for i in e['evidence_frame_ids']}
        images = [f for f in clip['core_frames'] if f['frame_id'] in ids]
        payload = dict(base_payload(case, clip, images), events=accepted, allowed_event_ids=[e['event_id'] for e in accepted], gt_rows=gt_rows(case, clip), reconciliation={'provenance': 'No verified normative answer; agent-reviewed visual observations only.'})
        response = await pool.call('compose', payload, clip['video'], images, 'assisted/' + clip['clip_id'])
        output['selection'] = response['result']
        output['qa'] = render_answer(response['result'], accepted)
        output['reference_event_coverage'] = len(response['result']['ordered_event_ids']) / len(events)
        output['status'] = 'assisted_draft_pending_human' if output['qa'] else 'held'
    except Exception as exc:
        output['error'] = str(exc)
    finally:
        save_json(FOLDER / 'assisted' / (clip['clip_id'] + '.json'), output)
    return output


async def main():
    records = {r['case']['case_id']: r for r in read_jsonl(ROOT / CONFIG['source_cases'])}
    reference = read_json(FOLDER / 'agent_event_reference.json')
    pool = Pool()
    start = time.monotonic()
    try:
        results = await asyncio.gather(*(process(pool, records[r['case_id']], r) for r in reference['cases']))
        summary = {'cases': len(results), 'qa_drafts': sum(bool(r.get('qa')) for r in results), 'results': results, 'reference_events': sum(len(r['events']) for r in reference['cases']), 'new_requests': len(pool.calls), 'elapsed_s': time.monotonic() - start, 'human_gold': False, 'autonomous_generation': False, 'formal_release': False}
        save_json(FOLDER / 'assisted_summary.json', summary)
        print(json.dumps({k: v for k, v in summary.items() if k != 'results'}), flush=True)
    finally:
        await pool.close()


if __name__ == '__main__':
    with (FOLDER / 'assisted.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main())
