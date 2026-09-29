import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import FFPROBE, OUT, REPORTS, ROOT, read_json, read_jsonl, save_json
from impact_qa.state_qa import STATE_OUT, state_at, validate_pair


def main(args):
    packets = read_jsonl(args.input)
    errors, checks = [], []
    for p in packets:
        target = p['target']
        source = next(e for e in p['evidence_catalog'] if e['id'] == target['end_state_source_id'])
        data = read_json(ROOT / source['path'])
        ci = next(i for i, c in enumerate(data['components']) if c['name'] == target['component_id'])
        _, vector = state_at(data['state_sequence'], target['end_frame_inclusive'])
        if vector[ci] != target['state_at_end']:
            errors.append(p['event_id'] + ':end_state_mismatch')
        clip = STATE_OUT / 'media' / p['event_id'] / 'clip.mp4'
        stream = json.loads(subprocess.check_output([FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames,width,height,avg_frame_rate', '-of', 'json', str(clip)], text=True))['streams'][0]
        expected = target['end_frame_inclusive'] - target['start_frame'] + 1
        if int(stream['nb_frames']) != expected:
            errors.append(p['event_id'] + ':clip_frame_count_mismatch')
        for ref in p['image_refs']:
            if not Path(ref['path']).is_file():
                errors.append(p['event_id'] + ':missing_media:' + ref['path'])
        for s in p['evidence_catalog']:
            if s.get('pointer'):
                v = read_json(ROOT / s['path'])
                for part in s['pointer'].strip('/').split('/'):
                    v = v[int(part)] if isinstance(v, list) else v[part]
        checks.append({'event_id': p['event_id'], 'clip_frames': expected, 'end_state': vector[ci], 'clip_stream': stream})
    frozen = read_json(REPORTS / 'frozen_v7.json')
    for path, digest in frozen['files'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            errors.append('frozen_v7_modified:' + path)
    if args.version:
        folder = OUT / args.version
        candidates = read_jsonl(folder / 'open_candidates.jsonl')
        evaluation = read_jsonl(folder / 'evaluation_inputs.jsonl')
        by_id = {p['event_id']: p for p in packets}
        if len({q['qa_id'] for q in candidates}) != len(candidates):
            errors.append('duplicate_qa_ids')
        if {q.get('evaluation_id', q['qa_id']) for q in candidates} != {q['qa_id'] for q in evaluation}:
            errors.append('evaluation_pair_ids_mismatch')
        for q in candidates:
            current = validate_pair(by_id[q['event_id']], q)
            if current != q['structural_issues']:
                errors.append(q['qa_id'] + ':structural_report_mismatch')
            if q['review_status'] != 'pending_human_review':
                errors.append(q['qa_id'] + ':unreviewed_truth_claim')
        forbidden = {'answer', 'reference_claims', 'correct_answer', 'answer_polarity', 'reference_annotations', 'component_states', 'state_at_end', 'computed_comparisons', 'candidate_graph', 'machine_review', 'answer_contract', 'state_assertions'}
        def inspect(value, path):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in forbidden:
                        errors.append(path + ':evaluation_leak:' + key)
                    inspect(item, path + '/' + key)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    inspect(item, path + '/' + str(i))
        for row in evaluation:
            inspect(row, row['qa_id'])
            if any(marker in row['qa_id'] or marker in row['video'] for marker in ['__adapter_done', '__bearing_done', '__bearing_incomplete', '__handle_done']):
                errors.append(row['qa_id'] + ':outcome_in_identifier_or_media_path')
        fixture = {'question': 'Did I follow the required order?', 'answer': 'Yes.', 'type': 'order_compliance', 'answer_polarity': 'yes', 'reference_claims': [{'source_ids': ['official_manual'], 'rule_ids': ['illustrated_rotor_before_adapter']}]}
        assert any('non_authoritative_normative_rule' in e for e in validate_pair(packets[0], fixture))
        fixture['reference_claims'][0]['source_ids'] = ['made_up_source']
        assert 'unknown_source:made_up_source' in validate_pair(packets[0], fixture)
    result = {'version': args.version, 'input_events': len(packets), 'errors': errors, 'checks': checks, 'result': 'pass' if not errors else 'fail', 'scope': 'media, frame-state mapping, provenance pointers, frozen assets, identifiers and evaluation-field isolation; not semantic accuracy'}
    save_json(REPORTS / ((args.version or 'state_v10_input') + '_validation.json'), result)
    print(json.dumps({'input_events': len(packets), 'errors': errors, 'result': result['result']}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version')
    parser.add_argument('--input', type=Path, default=STATE_OUT / 'packets.jsonl')
    main(parser.parse_args())
