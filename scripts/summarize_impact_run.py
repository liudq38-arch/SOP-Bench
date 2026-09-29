import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, save_json
from impact_qa.validation import qualifies_for_review_pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--split', default='development')
    args = parser.parse_args()
    rows = [read_json(p) for p in sorted((OUT / 'runs' / args.version / args.split).glob('*.json'))]
    examples = []
    decisions = Counter()
    counts = Counter()
    for r in rows:
        counts[r['status']] += 1
        if r['status'] != 'ok':
            examples.append({'event_id': r['event_id'], 'error': r.get('error')})
            continue
        counts['structural_issue_events'] += bool(r['structural_issues'])
        counts['refined_events'] += 'refined_observation' in r
        counts['conflict_events'] += bool(r['facts'].get('conflicts'))
        for i, pair in enumerate(r['generation'].get('qa_pairs', [])):
            review = next((x for x in r['review'].get('reviews', []) if x.get('qa_index') == i), {})
            decisions[review.get('decision', 'missing')] += 1
            pair_issues = r.get('pair_structural_issues', {}).get(str(i), r['structural_issues'])
            passed = qualifies_for_review_pass(pair, review, pair_issues)
            counts['strict_machine_pass'] += passed
            examples.append({'event_id': r['event_id'], 'phase': r['event']['phase'], 'types': r['event']['anomaly_types'], 'qa_index': i, 'question': pair['question'], 'answer': pair['answer'], 'answerability': pair.get('answerability'), 'review': review, 'structural_issues': r['structural_issues'], 'strict_machine_pass': passed})
    report = {'version': args.version, 'split': args.split, 'counts': dict(counts), 'decisions': dict(decisions), 'examples': examples, 'metric_limit': 'Same-model independent-call audit; not human accuracy, not independent-model verification.'}
    save_json(REPORTS / f'{args.split}_{args.version}_audit.json', report)
    text = [f'# {args.split} {args.version} 自动审核', '', json.dumps(report['counts'], ensure_ascii=False), '', json.dumps(report['decisions'], ensure_ascii=False), '', report['metric_limit'], '']
    for e in examples:
        text.append('## ' + e['event_id'] + ' / ' + str(e.get('qa_index', 'error')))
        text.append(json.dumps(e, ensure_ascii=False, indent=2))
    (REPORTS / f'{args.split}_{args.version}_audit.md').write_text('\n\n'.join(text))
    print(json.dumps({k: v for k, v in report.items() if k != 'examples'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
