import argparse
import asyncio
import fcntl
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl, save_json
from impact_qa.descriptive_v21 import digest
from impact_qa.event_v22 import CONFIG, FOLDER, Pool, process_clip, verify_events


async def challenge(pool, records):
    source = read_json(FOLDER / 'challenge_reference.json')
    by_id = {r['case']['case_id']: r for r in records}
    async def run(row):
        record = by_id[row['case_id']]
        clip = next(c for c in record['clips'] if c['clip_id'] == row['clip_id'])
        clean = [{k: v for k, v in e.items() if k not in ['expected', 'basis']} for e in row['claims']]
        result = {'case_id': row['case_id'], 'status': 'error'}
        try:
            result['verification'] = await verify_events(pool, record['case'], clip, clean, 'challenge/' + clip['clip_id'])
            labels = {e['event_id']: e['expected'] for e in row['claims']}
            result['scored'] = [dict(v, expected=labels[v['claim_id']], decision_correct=(v['verdict'] == 'supported') == (labels[v['claim_id']] == 'supported')) for v in result['verification']['verdicts']]
            result['status'] = 'ok'
        except Exception as exc:
            result['error'] = str(exc)
        save_json(FOLDER / 'challenge' / f'{row["clip_id"]}.json', result)
        return result
    results = await asyncio.gather(*(run(row) for row in source['cases']))
    scored = [s for r in results for s in r.get('scored', [])]
    negative = [s for s in scored if s['expected'] == 'reject']
    positive = [s for s in scored if s['expected'] == 'supported']
    summary = {'results': results, 'reference_type': source['reference_type'], 'human_gold': False, 'negative_count': len(negative), 'negative_false_accept': sum(s['verdict'] == 'supported' for s in negative), 'positive_count': len(positive), 'positive_accepted': sum(s['verdict'] == 'supported' for s in positive), 'failed_cases': sum(r['status'] != 'ok' for r in results)}
    save_json(FOLDER / 'challenge_summary.json', summary)
    return summary


async def main(mode):
    precheck = read_json(FOLDER / 'precheck.json')
    if not precheck['server_sampling_reproduced']:
        raise ValueError('run_v22:precheck_missing')
    sources = ['impact_qa/event_v22.py', 'scripts/prepare_event_v22.py', 'scripts/run_event_v22.py', 'configs/impact_qa/event_v22.json', *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'prompts/impact_qa/v22').glob('*.txt'))]]
    frozen = {'sources': {p: digest(ROOT / p) for p in sources}, 'cases_sha256': digest(ROOT / CONFIG['source_cases']), 'challenge_sha256': digest(FOLDER / 'challenge_reference.json')}
    path = FOLDER / (CONFIG['version'] + '_frozen.json')
    if path.exists() and read_json(path) != frozen:
        raise ValueError('run_v22:frozen_inputs_changed')
    save_json(path, frozen)
    records = read_jsonl(ROOT / CONFIG['source_cases'])
    pool = Pool()
    started = time.monotonic()
    results = []
    try:
        if mode in ['pilot', 'all']:
            results = await asyncio.gather(*(process_clip(pool, r, r['clips'][3 if '403f880f' in r['case']['case_id'] else 0]) for r in records))
            save_json(FOLDER / 'pilot_results.json', results)
        if mode in ['long', 'all']:
            selected = [r for r in records if '403f880f' in r['case']['case_id']]
            results = await asyncio.gather(*(process_clip(pool, r, c, 'long_local') for r in selected for c in r['clips']))
            save_json(FOLDER / 'long_results.json', results)
        if mode in ['challenge', 'all']:
            await challenge(pool, records)
    finally:
        await pool.close()
        save_json(FOLDER / f'last_requests_{mode}.json', pool.calls)
        summary = {'mode': mode, 'new_requests': len(pool.calls), 'elapsed_s': time.monotonic() - started, 'request_errors': sum(c['status'] != 'ok' for c in pool.calls), 'input_tokens': sum((c.get('usage') or {}).get('prompt_tokens', 0) for c in pool.calls), 'output_tokens': sum((c.get('usage') or {}).get('completion_tokens', 0) for c in pool.calls), 'results': len(results), 'qa_drafts': sum(bool(r.get('qa')) for r in results), 'formal_release': False, 'human_validated': 0}
        save_json(FOLDER / f'summary_{mode}.json', summary)
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['pilot', 'long', 'challenge', 'all'], default='pilot')
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main(args.mode))
