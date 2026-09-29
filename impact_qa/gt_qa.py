import hashlib
from pathlib import Path

from .common import ANNOTATIONS, ROOT, fingerprint, read_json


def reference(path, pointer):
    path = Path(path)
    value = read_json(path)
    for part in pointer.strip('/').split('/'):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'pointer': pointer, 'value': value}


def verify_reference(ref):
    actual = reference(ROOT / ref['path'], ref['pointer'])
    if actual != ref:
        raise ValueError('gt_reference:mismatch:' + ref['path'] + ':' + ref['pointer'])


def state_fact(video, component, frame):
    path = ANNOTATIONS / 'ASR/annotations' / (video + '_asr.json')
    d = read_json(path)
    ci = next(i for i, c in enumerate(d['components']) if c['name'] == component)
    si = max(i for i, s in enumerate(d['state_sequence']) if s['frame'] <= frame)
    return {'component': component, 'frame': frame, 'state': d['state_sequence'][si]['state'][ci], 'references': [reference(path, f'/components/{ci}'), reference(path, f'/state_sequence/{si}')]}


def build_contracts(packets):
    contracts = []
    groups = {}
    for packet in packets:
        video, case = packet['event_id'].split('__')
        groups.setdefault(video, {})[case] = packet
    for trial, (video, group) in enumerate(sorted(groups.items())):
        coarse_path = ANNOTATIONS / 'TAS-S/front' / (video + '.json')
        atomic_path = ANNOTATIONS / 'TAS-B/front' / (video + '.json')
        coarse, atomic = read_json(coarse_path), read_json(atomic_path)
        labels = {r['id']: r['name'] for r in atomic['action_labels']}
        label_indices = {r['id']: i for i, r in enumerate(atomic['action_labels'])}
        procedure = group['adapter_done']['procedure']['procedure_text']

        def add(kind, start, end, facts, refs, question, answer, alternatives, mcq_question, polarity='descriptive', forbidden=None):
            identifier = fingerprint({'video': video, 'kind': kind, 'facts': facts})[:20]
            contract = {'contract_id': 'gt_' + identifier, 'video_id': video, 'kind': kind, 'view': 'front', 'fps': 30, 'start_frame': start, 'end_frame_inclusive': end, 'source_video': group['adapter_done']['media_profile']['path'], 'public_procedure': procedure, 'facts': facts, 'references': refs, 'question_proposition': question, 'canonical_answer': answer, 'answer_polarity': polarity, 'mcq_question_proposition': mcq_question, 'choice_texts': alternatives, 'correct_choice_index': 0, 'forbidden_claims': forbidden or ['torque or internal fit', 'a uniquely mandatory order', 'an unsourced cause, correction, receiver or error mechanism'], 'human_review_status': 'pending_human_review', 'development_only': True}
            contract['contract_hash'] = fingerprint(contract)
            contracts.append(contract)

        for case, component, state, kind in [('adapter_done', 'adapter_plate', 1, 'component_installed'), ('adapter_done', 'bearing_plate', 0, 'component_unassembled'), ('handle_done', 'anti_vibration_handle', 1, 'handle_installed')]:
            target = group[case]['target']
            fact = state_fact(video, component, target['end_frame_inclusive'])
            assert fact['state'] == state
            name = component.replace('_', ' ').replace('anti vibration', 'anti-vibration')
            choices = ['Correctly installed.', 'Not installed.', 'Incorrectly installed.'] if state == 1 else ['Not installed.', 'Correctly installed.', 'Incorrectly installed.']
            answer = f'Yes, the {name} was correctly installed by the end of the clip.' if state == 1 else f'No, the {name} had not been installed by the end of the clip.'
            add(kind, target['start_frame'], target['end_frame_inclusive'], {'component_state': {k: v for k, v in fact.items() if k != 'references'}, 'state_definitions': {'0': 'unassembled', '1': 'correctly assembled', '-1': 'misassembled; not automatically an action error'}}, fact['references'], f'Had I correctly installed the {name} by the end of this clip?', answer, choices, f'What was the installation status of the {name} at the end of this clip?', 'yes' if state == 1 else 'no')

        target = group['bearing_incomplete']['target']
        end = target['end_frame_inclusive']
        ci, segment = next((i, s) for i, s in enumerate(coarse['segments']) if s['f_start'] <= end < s['f_end'] and s['label'] == 'insert_bearing_plate_assembly')
        fact = state_fact(video, 'bearing_plate', end)
        assert fact['state'] == -1
        add('ongoing_step', max(segment['f_start'], end - 180), end, {'action': segment['label'], 'endpoint_inside_action_interval': True, 'component_state': {k: v for k, v in fact.items() if k != 'references'}, 'interpretation': 'Action segment is still active at cutoff, component is not correctly assembled; no operator-error claim.'}, [reference(coarse_path, f'/segments/{ci}')] + fact['references'], 'Had I finished installing the bearing plate by the end of this clip?', 'No, I was still working on installing the bearing plate when the clip ended.', ['Installation was still in progress.', 'Installation had not started.', 'Installation was complete.'], 'How far had I got with installing the bearing plate when this clip ended?', 'no')

        rotor = [(i, s) for i, s in enumerate(coarse['segments']) if s['label'] == 'install_rotor_assembly']
        adapter = [(i, s) for i, s in enumerate(coarse['segments']) if s['label'] == 'attach_adapter_plate']
        assert max(s['f_end'] for _, s in rotor) < min(s['f_start'] for _, s in adapter)
        first = min(s['f_start'] for _, s in rotor)
        end = adapter[0][1]['f_end']
        if trial == 0:
            question, answer, polarity = 'Did I work on installing the rotor assembly before attaching the adapter plate?', 'Yes, I worked on installing the rotor assembly before attaching the adapter plate.', 'yes'
        elif trial == 1:
            question, answer, polarity = 'Did I attach the adapter plate before working on installing the rotor assembly?', 'No, I worked on installing the rotor assembly first, then attached the adapter plate.', 'no'
        else:
            question, answer, polarity = 'Which did I work on first: installing the rotor assembly or attaching the adapter plate?', 'I worked on installing the rotor assembly first, then attached the adapter plate.', 'descriptive'
        add('observed_order', max(0, first - 15), end, {'first_action': 'install_rotor_assembly', 'second_action': 'attach_adapter_plate', 'first_action_intervals': [[s['f_start'], s['f_end']] for _, s in rotor], 'second_action_first_interval': [adapter[0][1]['f_start'], end], 'relation': 'all first-action segments end before first second-action segment; no correctness or mandatory-order inference'}, [reference(coarse_path, f'/segments/{i}') for i, _ in rotor + adapter[:1]], question, answer, ['Installing the rotor assembly came first.', 'Attaching the adapter plate came first.', 'The two actions started at the same time.'], 'In what order did I work on the rotor assembly and attach the adapter plate?', polarity)

        ti, tool = next((i, s) for i, s in enumerate(atomic['segments']) if labels[s['action_label']] == 'pick_up_phillips_screwdriver' and s['phase'] == 'normal' and s['end_frame'] - s['start_frame'] >= 20)
        refs = [reference(atomic_path, f'/segments/{ti}'), reference(atomic_path, f'/action_labels/{label_indices[tool["action_label"]]}')]
        duration = (tool['end_frame'] - tool['start_frame'] + 1) / 30
        facts = {'action': 'pick_up_phillips_screwdriver', 'hand': tool['entity'], 'start_frame': tool['start_frame'], 'end_frame_inclusive': tool['end_frame'], 'duration_s': duration, 'duration_rule': '(end_frame_inclusive-start_frame+1)/30; annotation action duration, not normative required duration'}
        start, end = max(0, tool['start_frame'] - 30), tool['end_frame'] + 30
        add('tool_identity', start, end, facts, refs, 'Which type of screwdriver did I pick up with my right hand in this clip?', 'I picked up a Phillips screwdriver with my right hand.', ['A Phillips screwdriver.', 'A Torx screwdriver.', 'A flat-head screwdriver.'], 'Which type of screwdriver did I pick up with my right hand in this clip?')
        assert tool['entity'] == 'right'
        add('action_duration', start, end, facts, refs, 'Approximately how long did I take to pick up the screwdriver with my right hand?', f'About {duration:.1f} seconds.', [f'About {duration:.1f} seconds.', f'About {duration + 3:.1f} seconds.', f'About {duration + 7:.1f} seconds.'], 'Approximately how long did I take to pick up the screwdriver with my right hand?')

        ai, anomaly = next((i, s) for i, s in enumerate(atomic['segments']) if s['phase'] == 'anomaly' and s['anomaly_type'] == [0, 0, 1, 0, 0, 0] and s['action_label'] != 0)
        name = labels[anomaly['action_label']]
        action = {'transfer_M4_nut': 'transferring the M4 nut with my right hand', 'hand_spin_drive_shaft': 'turning the drive shaft by hand with my left hand'}[name]
        add('action_error_category', max(0, anomaly['start_frame'] - 30), anomaly['end_frame'] + 30, {'action': name, 'hand': anomaly['entity'], 'phase': 'anomaly', 'error_category': 'handling', 'error_mechanism': None, 'start_frame': anomaly['start_frame'], 'end_frame_inclusive': anomaly['end_frame'], 'interpretation': 'Only action-level error category is known; no physical cause or required correction supplied.'}, [reference(atomic_path, f'/segments/{ai}'), reference(atomic_path, f'/action_labels/{label_indices[anomaly["action_label"]]}'), reference(atomic_path, '/anomaly_types/2')], f'What type of mistake did I make while {action}?', 'An object-handling error.', ['An object-handling error.', 'Using the wrong tool.', 'Using the wrong part.'], f'What type of mistake did I make while {action}?')
    assert len(contracts) == 24 and len({c['contract_id'] for c in contracts}) == 24
    for c in contracts:
        assert c['start_frame'] <= c['end_frame_inclusive']
        assert len(set(c['choice_texts'])) == len(c['choice_texts']) == 3
        for ref in c['references']:
            verify_reference(ref)
    return contracts


def validate_generation(contract, result):
    issues = []
    if result.get('contract_id') != contract['contract_id']:
        issues.append('contract_id_mismatch')
    for field in ['question', 'mcq_question']:
        if not isinstance(result.get(field), str) or not result[field].strip().endswith('?'):
            issues.append('invalid_' + field)
        elif '_' in result[field] or any(t in result[field].lower() for t in ['annotation', 'ground truth', 'asr', 'tas-']):
            issues.append('metadata_in_' + field)
    if not isinstance(result.get('answer'), str) or not result['answer'].strip():
        issues.append('missing_answer')
    if result.get('visual_support') not in {'clear', 'uncertain', 'insufficient'}:
        issues.append('invalid_visual_support')
    if set(result) - {'contract_id', 'question', 'answer', 'mcq_question', 'visual_support', 'visual_limitation'}:
        issues.append('unrequested_output_fields')
    return issues
