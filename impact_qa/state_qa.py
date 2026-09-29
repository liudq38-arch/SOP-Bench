import hashlib
import json
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from .common import ANNOTATIONS, OUT, REPORTS, ROOT, fingerprint, read_json, save_json


STATE_OUT = OUT / 'state_qa_inputs_v10'
FRONT = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/front')
COMMIT = '4fed5faa5f05f7aece55712e458defa1f372b248'
UPSTREAM = f'https://github.com/Kratos-Wen/IMPACT/blob/{COMMIT}/'
STEPS = [
    ('rotor', 'Install the rotor assembly', ['install_rotor_assembly'], ['gearbox_housing', 'drive_shaft', 'bevel_gear', 'M6_nut']),
    ('adapter', 'Attach the adapter plate', ['attach_adapter_plate'], ['adapter_plate', 'screw_adaptor_topleft', 'screw_adaptor_lowright', 'M4_nut_plate_topleft', 'M4_nut_plate_lowright']),
    ('bearing', 'Insert the bearing plate assembly', ['insert_bearing_plate_assembly'], ['bearing_plate', 'bearing_screw_topleft', 'bearing_screw_lowright']),
    ('lever', 'Install the locking lever assembly', ['install_locking_lever_assembly'], ['screw_lever', 'spring', 'lever', 'washer']),
    ('handle', 'Screw on the anti-vibration handle', ['screw_on_anti_vibration_handle'], ['anti_vibration_handle']),
]


def source_id(kind, video, index):
    return f'{kind}:{video}:{index}'


def make_procedure():
    graph_path = ROOT / 'sources/impact_code/tasks/PSR/gemini_3_1_pro/configs/procedure_graph.json'
    graph = read_json(graph_path)
    manual = ROOT / 'sources/impact_docs/Manual_Book.svg'
    steps = [{'id': sid, 'name': name, 'action_classes': actions, 'component_group_candidate': components, 'receiver': None, 'expected_result': name + ' completed', 'requirement': 'shown_in_reference', 'source_ids': ['official_manual', 'official_step_dictionary'], 'mapping_status': 'research_agent_interpretation_of_illustration_and_names'} for sid, name, actions, components in STEPS]
    edges = [{'id': f'illustrated_{a[0]}_before_{b[0]}', 'before': a[0], 'after': b[0], 'authority': 'illustrated_reference_only', 'provenance': 'research_agent_transcription_of_official_illustration', 'condition': 'comparison_with_displayed_sequence_only', 'source_ids': ['official_manual']} for a, b in zip(STEPS, STEPS[1:])]
    return {
        'procedure_id': 'impact_model_a_illustrated_reference_v10', 'variant': 'CG15-125BL development; illustration variant association is research-agent interpretation', 'workflow': 'assemble',
        'coverage': 'all_five_displayed_coarse_assembly_stages; partial_engineering_constraints',
        'procedure_text': 'The supplied official reassembly illustration shows the rotor and gearbox operation first, followed by fitting and fastening the adapter plate, inserting and fastening the bearing plate assembly, installing the locking lever assembly, and screwing on the anti-vibration handle. Retrieve the needed parts and store tools as appropriate. This describes the full displayed example, not a uniquely mandatory ordering. The diagram shows component placement and screw operations, but gives no explicit torque, duration, or exhaustive prerequisite specification. Component state 1 refers to correct assembly of that component at the stated time, not completion of the whole device. The ordered stages may be used to compare the observed sequence with this supplied guide; a difference alone must not be called an operator error.',
        'steps': steps, 'prerequisites': edges, 'state_mappings': [],
        'candidate_graph': {'authority': 'mined_candidate_not_normative', 'use': 'development inspection only; do not use for correctness or final test protocol', 'source_ids': ['official_mined_graph'], 'metadata': graph['meta'], 'nodes': graph['nodes'], 'edges': graph['edges']},
        'source_catalog': [
            {'id': 'official_manual', 'path': str(manual.relative_to(ROOT)), 'sha256': hashlib.sha256(manual.read_bytes()).hexdigest(), 'url': UPSTREAM + 'website/assets/figures/Manual_Book.svg', 'location': 'bottom Reassembly row, left to right; all three rendered panels inspected by research agent', 'authority': 'official_illustration_with_agent_transcription'},
            {'id': 'official_step_dictionary', 'path': 'annotations/impact/IMPACT-v1.1/annotations/TAS-S/mapping_TAS-S.txt', 'location': 'assembly action labels 13-25; dictionary order is not normative order'},
            {'id': 'official_mined_graph', 'path': str(graph_path.relative_to(ROOT)), 'url': UPSTREAM + 'tasks/PSR/gemini_3_1_pro/configs/procedure_graph.json', 'authority': 'mined_on_92_videos'},
        ],
        'unresolved': ['No authoritative exhaustive AND/OR prerequisite graph has been located.', 'No source-verified component-to-receiver mapping supplied.', 'Do not promote an illustrated sequence or mined edge to a mandatory constraint.'],
    }


def profile_video(video_id, annotation):
    path = FRONT / f'{video_id}.mp4'
    cache = STATE_OUT / 'profiles' / f'{video_id}.json'
    if cache.exists():
        old = read_json(cache)
        if old.get('file_bytes') == path.stat().st_size and old.get('file_mtime_ns') == path.stat().st_mtime_ns and old.get('annotation_frames') == annotation['frame_count']:
            return old
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        pts = np.asarray([float(frame.pts * frame.time_base) for frame in container.decode(video=0)], dtype=np.float64)
        result = {'video_id': video_id, 'path': str(path), 'codec': stream.codec_context.name, 'width': stream.width, 'height': stream.height, 'fps': float(stream.average_rate), 'decoded_frames': len(pts), 'first_pts_s': float(pts[0]), 'last_pts_s': float(pts[-1]), 'annotation_frames': annotation['frame_count'], 'max_nominal_time_error_s': float(np.max(np.abs(pts - np.arange(len(pts)) / annotation['fps']))), 'file_bytes': path.stat().st_size, 'file_mtime_ns': path.stat().st_mtime_ns}
    assert len(pts) == annotation['frame_count'], f'profile_video:{video_id}:frame_count_mismatch'
    assert result['max_nominal_time_error_s'] < 1e-5, f'profile_video:{video_id}:non_nominal_pts'
    save_json(cache, result)
    return result


def state_at(sequence, frame):
    index = max(i for i, row in enumerate(sequence) if row['frame'] <= frame)
    return index, sequence[index]['state']


def make_packets(video_id, procedure, profile):
    asr_path = ANNOTATIONS / 'ASR/annotations' / f'{video_id}_asr.json'
    tas_path = ANNOTATIONS / 'TAS-S/front' / f'{video_id}.json'
    atomic_path = ANNOTATIONS / 'TAS-B/front' / f'{video_id}.json'
    asr, tas, atomic = read_json(asr_path), read_json(tas_path), read_json(atomic_path)
    fps, sequence = asr['fps'], asr['state_sequence']
    components = [c['name'] for c in asr['components']]
    definitions = [('adapter_done', 'adapter_plate', 1, 'adapter', 'rotor'), ('bearing_incomplete', 'bearing_plate', -1, 'bearing', 'adapter'), ('bearing_done', 'bearing_plate', 1, 'bearing', 'adapter'), ('handle_done', 'anti_vibration_handle', 1, 'handle', 'lever')]
    packets = []
    for case, component, wanted_state, stage, predecessor in definitions:
        ci = components.index(component)
        si = next(i for i, row in enumerate(sequence) if row['state'][ci] == wanted_state)
        end_frame = min(sequence[si]['frame'] + 15, asr['frame_count'] - 1, sequence[si + 1]['frame'] - 1 if si + 1 < len(sequence) else asr['frame_count'] - 1)
        action_names = next(s[2] for s in STEPS if s[0] in [stage])
        predecessor_names = next(s[2] for s in STEPS if s[0] == predecessor)
        starts = [s['f_start'] for s in tas['segments'] if s['label'] in action_names + predecessor_names and s['f_start'] <= end_frame]
        start_frame = max(0, min(starts) - 15)
        catalog = list(procedure['source_catalog'])
        states = []
        related = set(next(s[3] for s in STEPS if s[0] == stage) + next(s[3] for s in STEPS if s[0] == predecessor))
        for i, row in enumerate(sequence):
            if row['frame'] > end_frame:
                continue
            until = sequence[i + 1]['frame'] if i + 1 < len(sequence) else asr['frame_count']
            if until <= start_frame:
                continue
            sid = source_id('asr', video_id, i)
            selected = {name: row['state'][components.index(name)] for name in components if name in related}
            states.append({'id': sid, 'frame': row['frame'], 'valid_from_s': row['frame'] / fps, 'valid_to_s_exclusive': until / fps, 'states': selected, 'view': 'front'})
            catalog.append({'id': sid, 'kind': 'source_component_state', 'path': str(asr_path.relative_to(ROOT)), 'pointer': f'/state_sequence/{i}', 'view': 'front', 'frame': row['frame']})
        observed = []
        for i, row in enumerate(tas['segments']):
            if row['f_start'] > end_frame or row['f_end'] < start_frame or row['label'] == 'null':
                continue
            sid = source_id('tas_s', video_id, i)
            observed.append({'id': sid, 'action': row['label'], 'start_s': row['f_start'] / fps, 'end_s_exclusive': (row['f_end'] + 1) / fps, 'has_anomaly': row['has_anomaly'], 'meta_activity': row['meta_activity'], 'full_action_visible': row['f_start'] >= start_frame and row['f_end'] <= end_frame})
            catalog.append({'id': sid, 'kind': 'coarse_action', 'path': str(tas_path.relative_to(ROOT)), 'pointer': f'/segments/{i}', 'view': 'front'})
        labels = {r['id']: r['name'] for r in atomic['action_labels']}
        atomic_rows = []
        for i, row in enumerate(atomic['segments']):
            label = labels[row['action_label']]
            if row['start_frame'] > end_frame or row['end_frame'] < start_frame or component not in label:
                continue
            sid = source_id('tas_b', video_id, i)
            atomic_rows.append({'id': sid, 'action': label, 'hand': row['entity'], 'start_s': row['start_frame'] / fps, 'end_s_exclusive': (row['end_frame'] + 1) / fps, 'phase': row['phase'], 'anomaly_types': [a['name'] for a, present in zip(atomic['anomaly_types'], row['anomaly_type']) if present]})
            catalog.append({'id': sid, 'kind': 'atomic_action', 'path': str(atomic_path.relative_to(ROOT)), 'pointer': f'/segments/{i}', 'view': 'front'})
        prior_component = next(s[3][0] for s in STEPS if s[0] == predecessor)
        target_actions = [s for s in tas['segments'] if s['label'] in action_names and s['f_start'] <= end_frame]
        target_start = min(s['f_start'] for s in target_actions)
        prior_si, vector = state_at(sequence, target_start)
        predecessor_state = vector[components.index(prior_component)]
        initial_i, initial = state_at(sequence, start_frame)
        event_id = f'{video_id}__{case}'
        packets.append({
            'event_id': event_id, 'task': {'name': 'angle grinder reassembly', 'variant': asr['meta_data']['model_type'], 'workflow': asr['workflow']}, 'procedure': procedure,
            'target': {'event_id': event_id, 'video_id': video_id, 'component_id': component, 'receiver_id': None, 'step_id': stage, 'view': 'front', 'start_frame': start_frame, 'end_frame_inclusive': end_frame, 'start_s': start_frame / fps, 'end_s_exclusive': (end_frame + 1) / fps, 'target_action_start_s': target_start / fps, 'state_at_end': wanted_state, 'initial_target_state': initial[ci], 'initial_state_source_id': source_id('asr', video_id, initial_i), 'end_state_source_id': source_id('asr', video_id, si)},
            'state_definitions': {'-1': 'misassembled; does not by itself establish an operator mistake, a specific physical mechanism, or PPR phase', '0': 'unassembled', '1': 'correctly assembled'},
            'component_states': states, 'reference_annotations': atomic_rows, 'observed_events': observed,
            'computed_comparisons': [{'id': 'comparison_predecessor_state', 'predecessor_component': prior_component, 'target_step': stage, 'predecessor_state_at_first_target_action': predecessor_state, 'time_s': target_start / fps, 'source_ids': [source_id('asr', video_id, prior_si)] + [e['id'] for e in observed if e['start_s'] == target_start / fps], 'rule_id': f'illustrated_{predecessor}_before_{stage}', 'interpretation': 'State at first target action; not a normative correctness label and not proof of whole predecessor subassembly completion.'}],
            'coverage': {'history_until_target': 'continuous video window; annotations limited to that window plus state valid at start', 'initial_state': 'source state at window start, not original video start', 'cross_view_sync': 'not needed: source video and annotations are front', 'sampling': '16 native-video frames plus six exact-frame anchors; not exhaustive visual observation'},
            'evidence_catalog': catalog, 'visual_facts': [], 'media_profile': profile, 'human_review_status': 'pending_human_review', 'development_only': True,
        })
    return packets


def prepare_frames(packets):
    for video_id in sorted({p['target']['video_id'] for p in packets}):
        selected = [p for p in packets if p['target']['video_id'] == video_id]
        requested = {}
        for packet in selected:
            target = packet['target']
            start, end = target['start_frame'], target['end_frame_inclusive']
            boundary = next(s['frame'] for s in packet['component_states'] if s['id'] == target['end_state_source_id'])
            indices = sorted(set([start, (start + end) // 2, max(start, boundary - 1), boundary, min(end, boundary + 1), end]))
            if len(indices) < 6:
                indices = sorted(set(indices + np.linspace(start, end, 6).astype(int).tolist()))
            packet['frame_indices'] = indices
            for index in indices:
                path = STATE_OUT / 'media' / packet['event_id'] / f'frame_{index:06d}.jpg'
                if not path.exists() or not path.stat().st_size:
                    requested.setdefault(index, []).append(packet['event_id'])
        if requested:
            with av.open(str(FRONT / f'{video_id}.mp4')) as container:
                for index, frame in enumerate(container.decode(video=0)):
                    if index in requested:
                        for event_id in requested[index]:
                            path = STATE_OUT / 'media' / event_id / f'frame_{index:06d}.jpg'
                            path.parent.mkdir(parents=True, exist_ok=True)
                            frame.to_image().save(path, quality=92)
                    if index > max(requested):
                        break
        for packet in selected:
            refs = []
            board = Image.new('RGB', (1280, ((len(packet['frame_indices']) + 1) // 2) * 390), 'white')
            draw = ImageDraw.Draw(board)
            for k, index in enumerate(packet['frame_indices']):
                path = STATE_OUT / 'media' / packet['event_id'] / f'frame_{index:06d}.jpg'
                sid = f"frame:{packet['event_id']}:{index}"
                refs.append({'evidence_id': sid, 'path': str(path), 'requested_time_s': index / packet['media_profile']['fps'], 'frame_index': index, 'view': 'front full frame', 'time_scope': 'same-view exact decoded frame'})
                im = ImageOps.contain(Image.open(path).convert('RGB'), (640, 360))
                x, y = k % 2 * 640, k // 2 * 390
                board.paste(im, (x, y + 25))
                draw.text((x + 4, y + 4), f'{index} | {index / 30:.3f} s', fill='black')
            board.save(STATE_OUT / 'media' / packet['event_id'] / 'contact.jpg', quality=90)
            packet['image_refs'] = refs


def validate_pair(packet, pair):
    issues = []
    known = {s['id'] for s in packet['evidence_catalog']} | {f['evidence_id'] for f in packet['image_refs']} | {'comparison_predecessor_state'}
    rules = {r['id']: r for r in packet['procedure']['prerequisites']}
    for key in ['question', 'answer', 'type', 'reference_claims']:
        if not pair.get(key):
            issues.append('missing_' + key)
    for claim in pair.get('reference_claims', []):
        if not claim.get('source_ids'):
            issues.append('claim_without_source')
        for sid in claim.get('source_ids', []):
            if sid not in known:
                issues.append('unknown_source:' + sid)
        for rid in claim.get('rule_ids', []):
            if rid not in rules:
                issues.append('unknown_rule:' + rid)
            elif pair.get('type') in ['order_compliance', 'omission'] and rules[rid]['authority'] != 'authoritative':
                issues.append('non_authoritative_normative_rule:' + rid)
    if pair.get('type') == 'install_relation':
        mappings = [m for m in packet['procedure']['state_mappings'] if m['component_id'] == packet['target']['component_id'] and m['receiver_id'] == packet['target']['receiver_id']]
        if not mappings:
            issues.append('unverified_receiver_relation')
    if pair.get('type') == 'reference_order' and not any(term in pair.get('question', '').lower() for term in ['guide', 'illustrat', 'reference', 'shown']):
        issues.append('reference_order_not_scoped_to_guide')
    polarity = pair.get('answer_polarity')
    if polarity in ['yes', 'no'] and not pair.get('answer', '').lower().startswith(polarity):
        issues.append('answer_prefix_polarity_mismatch')
    if packet.get('require_state_assertions'):
        assertions = pair.get('state_assertions', [])
        if pair.get('type') in ['completion', 'install_relation', 'reference_order'] and not assertions:
            issues.append('missing_typed_state_assertions')
        fact_name = 'predecessor_at_target_start' if pair.get('type') == 'reference_order' else 'target_at_end'
        if pair.get('type') in ['completion', 'install_relation', 'reference_order'] and packet['answer_contract'][fact_name] not in assertions:
            issues.append('required_contract_fact_missing')
        catalog = {s['id']: s for s in packet['evidence_catalog']}
        for assertion in assertions:
            source = catalog.get(assertion.get('source_id'), {})
            if source.get('kind') != 'source_component_state':
                issues.append('state_assertion_invalid_source')
                continue
            data = read_json(ROOT / source['path'])
            names = [c['name'] for c in data['components']]
            name = assertion.get('component_id')
            frame = assertion.get('at_frame')
            if name not in names or not isinstance(frame, int):
                issues.append('state_assertion_invalid_component_or_frame')
                continue
            si, vector = state_at(data['state_sequence'], frame)
            if vector[names.index(name)] != assertion.get('state'):
                issues.append('state_assertion_value_mismatch:' + name)
            if source['pointer'] != f'/state_sequence/{si}':
                issues.append('state_assertion_time_source_mismatch:' + name)
            if not packet['target']['start_frame'] <= frame <= packet['target']['end_frame_inclusive']:
                issues.append('state_assertion_outside_window:' + name)
        answer = pair.get('answer', '').lower()
        if any(term in answer for term in ['annotation', 'state -1', 'state 1', 'state 0', 'asr', 'final state indicates']):
            issues.append('answer_annotation_jargon')
    return sorted(set(issues))


def writer_payload(packet):
    return {k: v for k, v in packet.items() if k not in ['image_refs', 'frame_indices', 'media_profile', 'input_hash']}


def deterministic_plan(packet):
    target = packet['target']
    mappings = [m for m in packet['procedure']['state_mappings'] if m['component_id'] == target['component_id'] and m['receiver_id'] == target['receiver_id']]
    sources = [target['end_state_source_id']]
    if mappings:
        sources.extend(mappings[0]['source_ids'])
    first = {'type': 'install_relation' if mappings else 'completion', 'focus': target['component_id'], 'receiver': target['receiver_id'], 'scope': 'state_at_end', 'support_ids': sources, 'rule_ids': [], 'label_basis_ids': [target['end_state_source_id']], 'reference_support': 'sufficient', 'visibility': 'uncertain'}
    comparison = packet['computed_comparisons'][0]
    second = {'type': 'reference_order', 'focus': comparison['predecessor_component'] + '_before_' + target['component_id'], 'scope': 'history_until_target', 'support_ids': comparison['source_ids'] + ['official_manual'], 'rule_ids': [comparison['rule_id']], 'label_basis_ids': [comparison['source_ids'][0]], 'reference_support': 'sufficient', 'visibility': 'uncertain'}
    deferred = [{'type': 'order_compliance', 'missing': ['authoritative mandatory prerequisites'], 'requested_evidence': 'Explicit variant-specific engineering rules.'}]
    if not mappings:
        deferred.append({'type': 'install_relation', 'missing': ['verified receiver mapping'], 'requested_evidence': 'A source-linked relation for this component.'})
    return {'selected': [first, second], 'deferred': deferred, 'method': 'deterministic_source_eligibility_for_this_development_scope'}


def evaluation_input(packet, pair, qa_id):
    procedure = packet['procedure']
    opaque = 'qa_' + hashlib.sha256(qa_id.encode()).hexdigest()[:24]
    media = OUT / 'evaluation_media_v10' / (hashlib.sha256(packet['event_id'].encode()).hexdigest()[:24] + '.mp4')
    media.parent.mkdir(exist_ok=True)
    original = STATE_OUT / 'media' / packet['event_id'] / 'clip.mp4'
    if not media.exists():
        media.symlink_to(original)
    return {'qa_id': opaque, 'question': pair['question'], 'video': str(media), 'source_interval_s': [packet['target']['start_s'], packet['target']['end_s_exclusive']], 'public_procedure': {k: procedure[k] for k in ['procedure_id', 'procedure_text', 'coverage', 'steps', 'prerequisites', 'state_mappings']}, 'protocol': 'front-view development; public illustrated procedure, video and question only; no test execution labels, ground-truth states, answers or mined graph', 'review_status': 'pending_human_review'}
