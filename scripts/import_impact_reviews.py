import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl, save_json, save_jsonl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('review_json')
    parser.add_argument('--reviewer', required=True)
    args = parser.parse_args()
    submission = read_json(args.review_json)
    source = read_jsonl(OUT / 'open_candidates.jsonl')
    source += [dict(r, qa_id=r['event_id'] + '__category') for r in read_jsonl(OUT / 'category_candidates.jsonl')]
    if (OUT / 'agent_revision_candidates.jsonl').exists():
        source += read_jsonl(OUT / 'agent_revision_candidates.jsonl')
    index = {r['qa_id']: r for r in source}
    accepted, history = [], []
    seen = set()
    for item in submission['reviews']:
        key = item['item_key']
        if key not in index or key in seen:
            raise ValueError(f'review_import: unknown or duplicate item {key}')
        seen.add(key)
        original = index[key]
        if original['prompt_version'] != submission['prompt_version']:
            raise ValueError(f'review_import: prompt version mismatch for {key}')
        run = read_json(OUT / 'runs' / original['prompt_version'] / original['split'] / (original['event_id'] + '.json'))
        if item['source_run_key'] != run['run_key']:
            raise ValueError(f'review_import: stale source run for {key}')
        decision = item['decision']
        if decision not in ['pending_human_review', 'accept', 'edit', 'reject']:
            raise ValueError(f'review_import: invalid decision for {key}')
        if decision in ['edit', 'reject'] and not item.get('reason', '').strip():
            raise ValueError(f'review_import: reason required for {key}')
        if decision in ['accept', 'edit']:
            if not item['question'].strip() or not item['answer'].strip():
                raise ValueError(f'review_import: empty accepted QA {key}')
            answer = json.loads(item['answer']) if key.endswith('__category') else item['answer']
            accepted.append(dict(original, question=item['question'], answer=answer, review_status='human_accepted', reviewer=args.reviewer, review_reason=item.get('reason'), reviewed_at=item['reviewed_at']))
        history.append(dict(item, reviewer=args.reviewer))
    target = OUT / 'human_reviews' / Path(args.review_json).stem
    save_jsonl(target.with_suffix('.jsonl'), history)
    save_jsonl(target.with_name(target.name + '_accepted.jsonl'), accepted)
    save_json(REPORTS / 'human_review_import_summary.json', {'reviewer': args.reviewer, 'submitted': len(history), 'accepted': len(accepted), 'source': args.review_json, 'output': str(target)})
    print('Imported', len(history), 'review records;', len(accepted), 'accepted.')


if __name__ == '__main__':
    main()
