import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, read_json, read_jsonl, save_json
from impact_qa.validation import qualifies_for_review_pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    errors = []
    event_lists = {s: read_jsonl(OUT / f'{s}_events.jsonl') for s in ['development', 'pilot']}
    executions = [r['execution_id'] for rows in event_lists.values() for r in rows]
    if len(executions) != len(set(executions)):
        errors.append('execution_video_overlap')
    records = {}
    for split, events in event_lists.items():
        for event in events:
            path = OUT / 'runs' / args.version / split / (event['event_id'] + '.json')
            if not path.exists():
                errors.append(f'missing_run:{event["event_id"]}')
                continue
            record = read_json(path)
            records[event['event_id']] = record
            if record['status'] != 'ok':
                errors.append(f'failed_run:{event["event_id"]}')
                continue
            category = record['category_qa']['answer']
            expected = event['anomaly_types'] if event['phase'] == 'anomaly' else []
            if category != {'phase': event['phase'], 'anomaly_types': expected}:
                errors.append(f'category_label_mutation:{event["event_id"]}')
            if record['human_review_status'] != 'pending_human_review':
                errors.append(f'unexpected_review_status:{event["event_id"]}')
            for frame in record['evidence']:
                if not Path(frame['path']).is_file():
                    errors.append(f'missing_frame:{event["event_id"]}:{frame["evidence_id"]}')
            if not (OUT / 'review/clips' / (event['event_id'] + '.mp4')).is_file():
                errors.append(f'missing_clip:{event["event_id"]}')
    candidates = read_jsonl(OUT / 'open_candidates.jsonl')
    categories = read_jsonl(OUT / 'category_candidates.jsonl')
    passed = read_jsonl(OUT / 'open_machine_pass_pending_human.jsonl')
    inputs = read_jsonl(OUT / 'evaluation_inputs.jsonl')
    expected_keys = {'qa_id', 'video_id', 'hand', 'start_s', 'end_s', 'question', 'split'}
    if any(set(row) != expected_keys for row in inputs):
        errors.append('evaluation_input_field_leakage')
    if len(inputs) != len(candidates) + len(categories):
        errors.append('evaluation_input_count')
    if len({r['qa_id'] for r in inputs}) != len(inputs):
        errors.append('duplicate_qa_id')
    if len(categories) != len(records):
        errors.append('category_event_count')
    for row in passed:
        if not qualifies_for_review_pass(row, row['machine_review'], row['structural_issues']):
            errors.append(f'invalid_machine_pass:{row["qa_id"]}')
    frozen_path = REPORTS / f'frozen_{args.version}.json'
    if frozen_path.exists():
        frozen = read_json(frozen_path)
        for relative, expected in frozen['files'].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            if actual != expected:
                errors.append(f'frozen_file_changed:{relative}')
    else:
        errors.append('missing_frozen_manifest')
    report = {'version': args.version, 'events': len(records), 'open_candidates': len(candidates), 'categories': len(categories), 'machine_pass_pending_human': len(passed), 'input_rows': len(inputs), 'errors': errors, 'status': 'pass' if not errors else 'fail', 'scope': 'Artifact completeness, source-label preservation, split isolation, machine-pass gating and input field checks; not semantic correctness.', 'first_ten_inputs': inputs[:10]}
    save_json(REPORTS / 'release_validation.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'first_ten_inputs'}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
