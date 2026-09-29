from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.anomaly_contrast import FOLDER, HELD_PARTICIPANTS
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl


def need(condition, message):
    if not condition:
        raise ValueError('contrast_audit:' + message)


def references(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'evidence_frame_ids':
                yield from item
            else:
                yield from references(item)
    elif isinstance(value, list):
        for item in value:
            yield from references(item)


def main():
    rows = read_jsonl(FOLDER / 'cases.jsonl')
    cases = {r['case_id']: r for r in rows}
    need(len(cases) == len(rows) == 71, 'case_count_or_duplicates')
    frozen = read_json(FOLDER / 'selection_frozen.json')
    need(fingerprint(rows) == frozen['cases_fingerprint'], 'frozen_selection_changed')
    need(all((r['participant'] in HELD_PARTICIPANTS) == (r['split'] == 'validation') for r in rows), 'participant_leakage')
    rule = read_json(FOLDER / 'rulebook_frozen_v1.json')
    validation_run = read_json(FOLDER / 'validation/focus_r1/run_frozen.json')
    need(validation_run['rulebook_hash'] == fingerprint(rule), 'post_validation_rule_change')
    notes = {}
    frame_count = 0
    for split in ['discovery', 'validation']:
        for r in read_json(FOLDER / split / 'direct_review_notes.json'):
            need(r['case_id'] not in notes, 'duplicate_review')
            notes[r['case_id']] = r
        sheets = read_json(FOLDER / split / 'direct_frames_manifest.json')
        for sheet in sheets:
            case = cases[sheet['case_id']]
            need(Path(sheet['sheet']).exists(), 'missing_sheet')
            for f in sheet['frames']:
                need(Path(f['path']).exists(), 'missing_source_frame')
                need(abs(f['source_frame_index'] / case['clip']['fps'] - f['source_time_s']) < .002, 'source_clock')
            need(sum(f['scope'] == 'TARGET' for f in sheet['frames']) == 12, 'direct_target_frame_count')
            frame_count += len(sheet['frames'])
    need(set(notes) == set(cases), 'missing_direct_review')
    for case in rows:
        need(Path(case['clip']['source_video']).exists(), 'missing_original_video')
        need(case['start_frame'] < case['end_frame_exclusive'], 'empty_target')
        for a in case['target_actions']:
            need(hashlib.sha256((ROOT / a['source']['path']).read_bytes()).hexdigest() == a['source']['sha256'], 'annotation_hash_changed')
            source = read_json(ROOT / a['source']['path'])
            raw = source
            for part in a['source']['pointer'].strip('/').split('/'):
                raw = raw[int(part)] if isinstance(raw, list) else raw[part]
            need(isinstance(raw, dict), 'invalid_source_pointer')
            need(raw['start_frame'] == a['start_frame'] and raw['end_frame'] + 1 == a['end_frame_exclusive'], 'native_boundary_changed')
        if case['role'] == 'normal':
            need(not any(case['gt_labels']) and all(a['phase'] == 'normal' for a in case['target_actions']), 'non_normal_control')
    run_stats = {}
    for split, run, expected in [('discovery', 'observe_r1', 44), ('discovery', 'focus_r1', 8), ('validation', 'focus_r1', 27)]:
        folder = FOLDER / split / run
        results = read_jsonl(folder / 'observations.jsonl')
        need(len(results) == expected and all(r['status'] == 'ok' for r in results), 'run_incomplete:' + split + '/' + run)
        lengths, tokens, output_tokens = [], [], []
        for result in results:
            case = cases[result['case_id']]
            media = result['media']
            need(hashlib.sha256(Path(media['path']).read_bytes()).hexdigest() == media['sha256'], 'media_hash')
            mapped = {f['frame_id']: f['source_frame_index'] for f in media['sampled_frames']}
            need(set(references(result['observation'])) <= set(mapped), 'invalid_citation')
            if run.startswith('focus'):
                need(all(case['start_frame'] <= f < case['end_frame_exclusive'] for f in mapped.values()), 'focus_context_intrusion')
            else:
                for key in ['target', 'other_hand_during_target']:
                    need(all(case['start_frame'] <= mapped[f] < case['end_frame_exclusive'] for f in result['observation'][key]['evidence_frame_ids']), 'out_of_target_citation')
            record = read_json(folder / 'api_cache' / (result['api_cache_key'] + '.json'))
            payload = json.loads(record['request']['messages'][1]['content'][0]['text'])
            allowed = {'case_id', 'view', 'target_hand', 'entire_video_is_target', 'source_frames'} if run.startswith('focus') else {'case_id', 'view', 'target_hand', 'target_interval_source_frames', 'fps_of_source', 'frame_map'}
            need(set(payload) <= allowed, 'unapproved_payload_field')
            need(record['request']['mm_processor_kwargs']['do_sample_frames'] is False, 'server_resampling')
            tokens.append(record['usage']['prompt_tokens'])
            output_tokens.append(record['usage']['completion_tokens'])
            lengths.append(len(mapped))
        run_stats[split + '/' + run] = {'successful_requests': len(results), 'input_frames_range': [min(lengths), max(lengths)], 'prompt_tokens_range': [min(tokens), max(tokens)], 'completion_tokens_range': [min(output_tokens), max(output_tokens)], 'total_tokens': sum(tokens) + sum(output_tokens)}
    pairs = read_jsonl(FOLDER / 'pairs.jsonl')
    pair_audit = []
    for pair in pairs:
        anomaly = cases[pair['anomaly_case']]
        normal = cases.get(pair['normal_case'])
        flags = []
        if normal is None:
            flags.append('no_normal_match')
        elif anomaly['trial_id'] == normal['trial_id']:
            gap = max(anomaly['start_frame'] - normal['end_frame_exclusive'], normal['start_frame'] - anomaly['end_frame_exclusive'], 0) / anomaly['clip']['fps']
            if gap == 0:
                flags.append('adjacent_or_overlapping_boundary_probe')
            elif gap < 5:
                flags.append('under_5s_gap_possible_same_operation')
        if normal:
            flags.append('same_action_name_not_proof_of_same_component_state')
        pair_audit.append(dict(pair, audit_flags=flags, matched_state_equivalence_verified=False, use_as_independent_binary_control=False))
    audit_cases = []
    local = set(rule['rules'][0]['support_cases'] + ['ac_304551d2d3bf3586'])
    for case in rows:
        folder = FOLDER / case['split'] / 'direct_frames' / case['case_id']
        manifest = read_json(folder / 'manifest.json')
        audit_cases.append(dict(case, codex_review=notes[case['case_id']], reviewer='Codex direct source-frame inspection', reviewer_blind_to_GT=False, human_review='unreviewed', source_frame_sheet=str(folder / 'sheet.jpg'), source_frame_manifest=str(folder / 'manifest.json'), evidence_frames=manifest['frames'], local_sequence_candidate=case['case_id'] in local, normative_reason_verified=False, formal_release=False))
    save_jsonl(FOLDER / 'case_audit.jsonl', audit_cases)
    save_jsonl(FOLDER / 'pair_audit.jsonl', pair_audit)
    save_jsonl(FOLDER / 'first10_audit.jsonl', audit_cases[:10])
    summary = {'cases': len(rows), 'anomalies': sum(c['role'] == 'anomaly' for c in rows), 'normal_candidates': sum(c['role'] == 'normal' for c in rows), 'direct_frame_entries_reviewed': frame_count, 'unique_source_frame_keys_reviewed': len({(c['trial_id'], f['source_frame_index']) for c in audit_cases for f in c['evidence_frames']}), 'sampled_frame_review_not_exhaustive_video_review': True, 'splits': dict(Counter(c['split'] + ':' + c['research_category'] + ':' + c['role'] for c in rows)), 'multi_label_anomaly_cases': sum(c['role'] == 'anomaly' and sum(c['gt_labels']) > 1 for c in rows), 'anomaly_under_1_5s': sum(c['role'] == 'anomaly' and c['duration_s'] < 1.5 for c in rows), 'local_sequence_candidates': sorted(local), 'validation_local_sequence_candidates': 1, 'verified_universal_category_rules': 0, 'formal_QA_released': 0, 'pair_audit_flags': dict(Counter(f for p in pair_audit for f in p['audit_flags'])), 'requests': run_stats, 'structural_checks': 'passed', 'blindness': 'VLM payload excludes GT; Codex direct review sees GT; not an anomaly classification benchmark', 'scope': 'Wrong tool and Spatial; other four categories pending', 'selection_fingerprint': frozen['cases_fingerprint'], 'rulebook_fingerprint': fingerprint(rule)}
    save_json(FOLDER / 'final_audit.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
