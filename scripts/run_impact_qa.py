import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_jsonl, save_json
from impact_qa.pipeline import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['development', 'pilot'], required=True)
    parser.add_argument('--version', default='v1')
    parser.add_argument('--concurrency', type=int, default=2)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000/v1', help='Comma-separated equivalent vLLM endpoints; concurrency is per service')
    args = parser.parse_args()
    rows = read_jsonl(OUT / f'{args.split}_events.jsonl')
    if args.limit:
        rows = rows[:args.limit]
    results = asyncio.run(run(rows, args.version, args.concurrency, args.base_url))
    report = {'split': args.split, 'version': args.version, 'events': len(results), 'ok': sum(r['status'] == 'ok' for r in results), 'error': sum(r['status'] != 'ok' for r in results), 'pairs': sum(len(r.get('generation', {}).get('qa_pairs', [])) for r in results), 'machine_pass': sum(v.get('decision') == 'pass' for r in results for v in r.get('review', {}).get('reviews', [])), 'structural_issues': {r['event_id']: r['structural_issues'] for r in results if r.get('structural_issues')}, 'human_reviewed': 0}
    save_json(REPORTS / f'{args.split}_{args.version}_summary.json', report)
    print(report)
    if report['error']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
