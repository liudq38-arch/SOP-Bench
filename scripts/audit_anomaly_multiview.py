from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.anomaly_multiview import FOLDER, prepare
from impact_qa.common import read_json, save_json, save_jsonl


def main():
    cases = prepare()
    notes = read_json(FOLDER / 'direct_review_notes.json')
    manifests = {m['case_id']: m for m in read_json(FOLDER / 'frame_manifest.json')}
    grouped = defaultdict(list)
    frame_keys = set()
    raw_documents = {}
    rows = []
    source_intervals = set()
    for case in cases:
        cid = case['case_id']
        aid = case['anchor']['anchor_id']
        note = notes['notes'][aid]
        view = case['view']
        manifest = manifests[cid]
        a, b = case['target_interval_frames']
        ca, cb = case['context_interval_frames']
        assert 0 <= ca <= a < b <= cb <= case['frame_count'], cid
        assert Path(case['source_video']).is_file(), cid
        assert abs(manifest['stream_average_rate'] - case['fps']) < 1e-8, cid
        assert manifest['max_annotation_pts_clock_delta_s'] < .001, cid
        frames = {f['source_frame_index']: f for f in manifest['frames']}
        assert set(note['useful_frames'][view]) <= set(frames), cid
        for frame in manifest['frames']:
            index = frame['source_frame_index']
            assert ca <= index < cb, cid
            assert frame['scope'] == ('TARGET' if a <= index < b else 'BEFORE' if index < a else 'AFTER'), cid
            assert Path(frame['path']).is_file(), frame['path']
            frame_keys.add((case['source_video'], index))
        for action in case['native_context_actions']:
            src = action['source']
            path = ROOT / src['path']
            assert f'/TAS-B/{view}/' in src['path'], cid
            if src['path'] not in raw_documents:
                raw_documents[src['path']] = (read_json(path), sha256(path.read_bytes()).hexdigest())
            doc, digest = raw_documents[src['path']]
            assert digest == src['sha256'], cid
            native = doc['segments'][int(src['pointer'].rsplit('/', 1)[1])]
            names = {r['id']: r['name'] for r in doc['action_labels']}
            assert (native['start_frame'], native['end_frame'] + 1, native['entity'], native['phase'], native['anomaly_type'], names[native['action_label']]) == (action['start_frame'], action['end_frame_exclusive'], action['hand'], action['phase'], action['labels'], action['action']), cid
            source_intervals.add((src['path'], src['pointer']))
        expected_target = [r for r in case['native_context_actions'] if r['hand'] == case['target_hand'] and r['start_frame'] < b and r['end_frame_exclusive'] > a]
        assert expected_target == case['native_target_actions'], cid
        row = {
            'case_id': cid, 'anchor_id': aid, 'trial_id': case['trial_id'], 'view': view,
            'target_hand': case['target_hand'], 'native_fps': case['fps'],
            'target_interval_frames': [a, b], 'target_interval_s': [a / case['fps'], b / case['fps']],
            'mapping': case['mapping'], 'native_GT': case['native_target_actions'],
            'observations': note['views'][view], 'crossview_conclusion': note['conclusion'],
            'reason_status': note['reason_status'], 'limitations': note['limits'], 'decision': note['decision'],
            'useful_frame_evidence': [dict(frames[f], sha256=sha256(Path(frames[f]['path']).read_bytes()).hexdigest()) for f in note['useful_frames'][view]],
            'reviewed_frame_ids': [f['frame_id'] for f in manifest['frames']],
            'sheet': manifest['sheet'], 'reviewer': notes['reviewer'], 'human_review': 'unreviewed',
            'sampling': '4_before_12_target_4_after', 'frame_synchronization_verified': False,
            'visual_correspondence': 'same_local_operation_with_view_specific_boundaries_or_partial_coverage',
            'formal_release': False,
        }
        grouped[aid].append(row)
        rows.append(row)
    assert len(rows) == len(manifests) == len({r['case_id'] for r in rows}) == 36
    assert len(grouped) == len(notes['notes']) == 12
    dense = read_json(FOLDER / 'dense/mv_6a0bcfa0824d_ego/manifest.json')
    dense_case = next(c for c in cases if c['case_id'] == dense['case_id'])
    a, b = dense_case['target_interval_frames']
    assert [f['source_frame_index'] for f in dense['frames']] == list(range(a, b))
    before_dense = len(frame_keys)
    for frame in dense['frames']:
        assert Path(frame['path']).is_file()
        assert abs(frame['pts_s'] - dense['stream_start_s'] - frame['annotation_time_s']) < .001
        frame_keys.add((dense['source_video'], frame['source_frame_index']))
    for row in rows:
        if row['case_id'] == dense['case_id']:
            row['dense_target_manifest'] = str(FOLDER / 'dense/mv_6a0bcfa0824d_ego/manifest.json')
            row['all_target_source_frames_reviewed'] = True
    differences = []
    for aid, group in grouped.items():
        label_sets = {r['view']: sorted({tuple(x['labels']) for x in r['native_GT']}) for r in group}
        action_sets = {r['view']: sorted({x['action'] for x in r['native_GT']}) for r in group}
        if len({str(v) for v in label_sets.values()}) > 1 or len({str(v) for v in action_sets.values()}) > 1:
            differences.append({'anchor_id': aid, 'label_sets': label_sets, 'action_sets': action_sets, 'labels_differ': len({str(v) for v in label_sets.values()}) > 1, 'actions_differ': len({str(v) for v in action_sets.values()}) > 1, 'note': 'Local correspondence only; differences are not adjudicated annotation errors.'})
    details = read_json(FOLDER / 'details/manifest.json')
    assert len(details) == 10 and all(Path(d['sheet']).is_file() for d in details)
    summary = {
        'anchors': len(grouped), 'view_windows': len(rows),
        'trials': len({r['trial_id'] for r in rows}), 'participants': len({r['trial_id'].split('_')[0] for r in rows}),
        'new_front_anchors': sum(not aid.startswith('ac_') for aid in grouped),
        'contact_sheets_reviewed': len(manifests), 'sampled_frame_entries': sum(len(m['frames']) for m in manifests.values()),
        'unique_sampled_source_frames': before_dense, 'detail_sheets_reviewed': len(details),
        'detail_reused_frame_entries': sum(len(d['frames']) for d in details),
        'dense_sheets_reviewed': len(dense['sheets']), 'dense_frame_entries': len(dense['frames']),
        'dense_additional_unique_frames': len(frame_keys) - before_dense, 'unique_source_frames_total': len(frame_keys),
        'mapping_statuses': dict(Counter(c['mapping']['status'] for c in cases)),
        'anchors_with_local_label_differences': sum(d['labels_differ'] for d in differences),
        'anchors_with_local_action_differences': sum(d['actions_differ'] for d in differences),
        'label_order': ['Temporal', 'Spatial', 'Handling', 'Wrong part', 'Wrong tool', 'Procedural'],
        'native_target_view_windows_containing_labels': {name: sum(any(x['labels'][i] for x in c['native_target_actions']) for c in cases) for i, name in enumerate(['Temporal', 'Spatial', 'Handling', 'Wrong part', 'Wrong tool', 'Procedural'])},
        'annotation_files_verified': len(raw_documents), 'context_native_segments_verified': len(source_intervals),
        'max_annotation_pts_clock_delta_s': max(m['max_annotation_pts_clock_delta_s'] for m in manifests.values()),
        'new_model_requests': 0, 'new_formal_QA': 0, 'new_official_class_rules_confirmed': 0,
        'human_expert_review': False, 'independent_holdout': False, 'accuracy': None,
        'validations_passed': ['frozen_selection', 'native_GT_pointer_SHA_and_fields', 'per_view_GT_and_target_hand', 'intervals_and_media', 'frame_index_PTS_and_scopes', 'review_evidence_references', 'all_dense_target_frames', 'review_coverage'],
    }
    save_jsonl(FOLDER / 'visual_reviews.jsonl', rows)
    save_json(FOLDER / 'crossview_differences.json', differences)
    save_json(FOLDER / 'audit.json', summary)
    save_json(FOLDER / 'code_manifest.json', {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), ROOT / 'impact_qa/anomaly_multiview.py', ROOT / 'impact_qa/source_frames.py', ROOT / 'scripts/inspect_anomaly_multiview.py', ROOT / 'scripts/render_anomaly_multiview_details.py', ROOT / 'scripts/render_anomaly_multiview_dense.py', ROOT / 'prompts/impact_qa/anomaly_evidence_rules_v3.txt']})
    print(summary)


if __name__ == '__main__':
    main()
