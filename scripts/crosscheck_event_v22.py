import asyncio
import fcntl
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl, save_json
from impact_qa import event_v22 as pipeline


async def main():
    url = 'http://127.0.0.1:8003/v1'
    response = httpx.get(url + '/models', timeout=10, trust_env=False)
    response.raise_for_status()
    if 'impact-qwen3vl8b' not in [r['id'] for r in response.json()['data']]:
        raise RuntimeError('crosscheck_v22:wrong_model')
    pipeline.CONFIG.update(model='impact-qwen3vl8b', model_path='/data_1/ldq/models/Qwen3-VL-8B-Instruct', base_urls=[url], max_model_len=32768)
    records = {r['case']['case_id']: r for r in read_jsonl(ROOT / pipeline.CONFIG['source_cases'])}
    reference = read_json(pipeline.FOLDER / 'challenge_reference.json')
    pool = pipeline.Pool()
    results = []
    started = time.monotonic()
    try:
        for source in reference['cases']:
            record = records[source['case_id']]
            clip = next(c for c in record['clips'] if c['clip_id'] == source['clip_id'])
            claims = [{k: v for k, v in c.items() if k not in ['expected', 'basis']} for c in source['claims']]
            for kind, events in [('challenge', claims), ('candidate', (read_json(pipeline.FOLDER / 'runs/B' / (clip['clip_id'] + '.json')).get('qa') or {}).get('claims', []))]:
                result = {'case_id': source['case_id'], 'kind': kind, 'status': 'error', 'model': pipeline.CONFIG['model']}
                try:
                    result['verification'] = await pipeline.verify_events(pool, record['case'], clip, events, f'crosscheck8b/{kind}/{clip["clip_id"]}')
                    if kind == 'challenge':
                        labels = {c['event_id']: c['expected'] for c in source['claims']}
                        result['scored'] = [dict(v, expected=labels[v['claim_id']]) for v in result['verification']['verdicts']]
                    result['status'] = 'ok'
                except Exception as exc:
                    result['error'] = f'{type(exc).__name__}:{exc}'
                save_json(pipeline.FOLDER / 'crosscheck8b' / f'{kind}_{clip["clip_id"]}.json', result)
                results.append(result)
    finally:
        await pool.close()
        scored = [s for r in results for s in r.get('scored', [])]
        negative = [s for s in scored if s['expected'] == 'reject']
        positive = [s for s in scored if s['expected'] == 'supported']
        summary = {'results': results, 'negative_count': len(negative), 'negative_false_accept': sum(s['verdict'] == 'supported' for s in negative), 'positive_count': len(positive), 'positive_accepted': sum(s['verdict'] == 'supported' for s in positive), 'failed_cases': sum(r['status'] != 'ok' for r in results), 'new_requests': len(pool.calls), 'elapsed_s': time.monotonic() - started, 'model': pipeline.CONFIG['model'], 'human_gold': False, 'formal_release': False}
        save_json(pipeline.FOLDER / 'crosscheck8b_summary.json', summary)
        print(json.dumps({k: v for k, v in summary.items() if k != 'results'}), flush=True)


if __name__ == '__main__':
    with (pipeline.FOLDER / 'crosscheck.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main())
