import csv
from hashlib import sha256
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import TYPES, fingerprint, read_json, read_jsonl, save_json
from impact_qa.evidence_audit import verify_native_action
from impact_qa.front_rule_metrics import evaluate, metric, rule_masks
from impact_qa.review_frames import render_case


OUT = ROOT / 'outputs/impact_qa/front_rule_coverage_v1'
BASE = ['H_hand_spin', 'S_place_prev_loosen', 'T_null_8', 'P_reassembly_dismount']
STAGE_TOOLS = {
    ('A', 'attach_adapter_plate'): 'phillips_screwdriver',
    ('A', 'detach_adapter_plate'): 'phillips_screwdriver',
    ('A', 'insert_bearing_plate_assembly'): 'torx_screwdriver',
    ('A', 'extract_bearing_plate_assembly'): 'torx_screwdriver',
    ('A', 'install_locking_lever_assembly'): 'torx_screwdriver',
    ('A', 'remove_locking_lever_assembly'): 'torx_screwdriver',
    ('B', 'insert_bearing_plate_assembly'): 'flat_head_screwdriver',
    ('B', 'extract_bearing_plate_assembly'): 'flat_head_screwdriver',
}


def union_result(rules, labels, durations, take):
    predictions = np.zeros_like(labels)
    for key in BASE:
        predictions[:, TYPES.index(rules[key]['category'])] |= rules[key]['mask']
    p, y = predictions[take], labels[take]
    tp = int(np.sum(p & y))
    return dict(rules={k: rules[k]['category'] for k in BASE},
                any_anomaly=metric(p.any(axis=1), y.any(axis=1), durations[take]),
                typed_precision=tp / int(p.sum()) if p.any() else None,
                typed_recall_all_six=tp / int(y.sum()) if y.any() else None,
                typed_TP=tp, predicted_labels=int(p.sum()), positive_labels_all_six=int(y.sum()))


def main():
    rows = read_jsonl(OUT / 'rows.jsonl')
    cases = read_jsonl(OUT / 'cases.jsonl')
    reviews = read_jsonl(OUT / 'visual_reviews.jsonl')
    frozen = read_json(OUT / 'frozen.json')
    if fingerprint(rows) != frozen['rows_fingerprint'] or fingerprint(cases) != frozen['cases_fingerprint']:
        raise ValueError('front_summary:frozen_inputs_changed')
    if len({r['row_id'] for r in rows}) != len(rows) or len(rows) != 13512:
        raise ValueError('front_summary:corpus_rows')
    documents, pointers = {}, set()
    for row in rows:
        if row['view'] != 'front' or '/front/' not in row['source_video']:
            raise ValueError('front_summary:wrong_view')
        pointers.add(verify_native_action(row['action'], documents))
    sources = read_json(OUT / 'sources.json')
    for path, digest in sources['auxiliary_documents'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('front_summary:auxiliary_changed:' + path)
    rules = rule_masks(rows)
    metrics = evaluate(rows, rules)
    if metrics != read_json(OUT / 'metrics.json'):
        raise ValueError('front_summary:metrics_not_reproducible')
    labels = np.array([r['action']['labels'] for r in rows], dtype=bool)
    durations = np.array([r['duration_s'] for r in rows])
    save_json(OUT / 'four_rule_union.json', union_result(rules, labels, durations, durations >= 0))
    sensitivity = []
    for minimum in [0, 1.5, 5]:
        take = durations >= minimum
        sensitivity.append(dict(minimum_atomic_duration_s=minimum, atomic_rows=int(take.sum()),
                               class_totals={t: int(labels[take, i].sum()) for i, t in enumerate(TYPES)},
                               rules={key: metric(rules[key]['mask'][take], labels[take, TYPES.index(rules[key]['category'])], durations[take]) for key in BASE + ['W_tool_pick_align']},
                               union=union_result(rules, labels, durations, take)))
    save_json(OUT / 'duration_sensitivity.json', dict(note='Atomic-duration sensitivity only; not production anomaly-event filtering. All denominators are recomputed within each eligible subset.', results=sensitivity))
    candidates = []
    candidate_mask = np.zeros(len(rows), dtype=bool)
    for i, row in enumerate(rows):
        required = STAGE_TOOLS.get((row['model'], row['stage']))
        action, inferred = row['action'], row['inferred_same_hand_tool']
        if required and inferred and required != inferred and action['noun'] == 'screw' and action['verb'] in {'align', 'tighten', 'loosen'}:
            candidate_mask[i] = True
            candidates.append(dict(row_id=row['row_id'], trial_id=row['trial_id'], action=action,
                                   required_tool_reference=required, inferred_tool=inferred, stage=row['stage']))
    save_json(OUT / 'stage_tool_candidate.json', dict(rule='screw align/tighten/loosen + known coarse-stage tool reference + differing inferred tool',
              GT_metric=metric(candidate_mask, labels[:, TYPES.index('wrong_tool')], durations),
              limitations=['coarse stage may contain several targets', 'tool state inferred, not visually confirmed',
                           'B assembly tool mapping provisional symmetry from observed disassembly', 'no performance validation or production activation'], rows=candidates))
    fields = ['rule_id', 'category', 'description', 'triggered', 'TP', 'FP', 'FN', 'GT_precision', 'GT_recall', 'GT_duration_recall', 'lift']
    with (OUT / 'metrics.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(metrics['rules'])
    reviews_by_id = {r['case_id']: r for r in reviews}
    if len(reviews_by_id) != len(cases) or set(reviews_by_id) != {c['case_id'] for c in cases}:
        raise ValueError('front_summary:review_coverage')
    unique_frames, frame_entries, maximum_error = set(), 0, 0.0
    for case in cases:
        folder = OUT / 'frames' / case['case_id']
        paths = list(folder.glob('*.jpg'))
        before = {str(p): p.stat().st_mtime_ns for p in paths}
        manifest = render_case(case, OUT)
        if before != {str(p): p.stat().st_mtime_ns for p in paths}:
            raise ValueError('front_summary:cache_miss:' + case['case_id'])
        review = reviews_by_id[case['case_id']]
        if review['view'] != 'front' or review['formal_release'] or review['human_review'] != 'unreviewed':
            raise ValueError('front_summary:review_status')
        if review['source_action'] != case['source_action'] or review['target_interval_frames'] != case['target_interval_frames']:
            raise ValueError('front_summary:review_target')
        frame_ids = {f['frame_id'] for f in manifest['frames']}
        if not set(review['frame_ids']).issubset(frame_ids):
            raise ValueError('front_summary:frame_reference')
        a, b = case['target_interval_frames']
        ca, cb = case['context_interval_frames']
        for frame in manifest['frames']:
            idx = frame['source_frame_index']
            scope = 'TARGET' if a <= idx < b else 'BEFORE' if idx < a else 'AFTER'
            if not ca <= idx < cb or frame['scope'] != scope:
                raise ValueError('front_summary:frame_scope')
            maximum_error = max(maximum_error, abs(frame['pts_s'] - idx / case['fps']))
            unique_frames.add((case['source_video'], idx))
            frame_entries += 1
    if maximum_error > 1 / 30:
        raise ValueError('front_summary:PTS_mismatch')
    for hit in read_jsonl(OUT / 'rule_hits.jsonl'):
        expected = [r['row_id'] for r, match in zip(rows, rules[hit['rule_id']]['mask']) if match]
        if hit['row_ids'] != expected:
            raise ValueError('front_summary:hit_mismatch')
    hardware = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,driver_version', '--format=csv,noheader'], text=True, capture_output=True, check=True).stdout.strip().splitlines()
    code = ['impact_qa/front_rule_metrics.py', 'scripts/audit_front_rule_coverage.py', 'scripts/summarize_front_rule_evidence.py', 'impact_qa/review_frames.py', 'impact_qa/source_frames.py']
    audit = dict(status='passed', view='front', atomic_rows=len(rows), unique_source_segments=len(pointers),
                 TASB_source_files=len(documents), auxiliary_source_files=len(sources['auxiliary_documents']),
                 rule_count=len(rules), GT_positive_atoms=int(labels.any(axis=1).sum()), GT_positive_labels=int(labels.sum()),
                 video_count=len({r['trial_id'] for r in rows}), case_count=len(cases), reviewed_cases=len(reviews),
                 diagnostic_video_count=len({c['trial_id'] for c in cases}), frame_entries=frame_entries,
                 unique_source_frames=len(unique_frames), maximum_PTS_difference_s=maximum_error,
                 cache_unchanged=True, model_API_requests=0, formal_QA_added=0,
                 accuracy_estimate=None, accuracy_reason='GT fallible; diagnostic sample GT-stratified, GT-visible, no independent reference labels',
                 hardware=hardware, code_sha256={p: sha256((ROOT / p).read_bytes()).hexdigest() for p in code})
    save_json(OUT / 'audit.json', audit)
    print(audit)
    for item in sensitivity:
        print('duration', item['minimum_atomic_duration_s'], item['atomic_rows'], {k: (m['triggered'], m['TP']) for k, m in item['rules'].items()})


if __name__ == '__main__':
    main()
