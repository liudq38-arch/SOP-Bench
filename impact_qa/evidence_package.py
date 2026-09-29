import copy
import hashlib
from pathlib import Path

from .common import ANNOTATIONS, OUT, ROOT, fingerprint, read_json
from .gt_qa import reference, verify_reference
from .state_qa import make_procedure


CUTOFF_KINDS = {'component_installed', 'component_unassembled', 'ongoing_step'}


def public_procedure():
    p = make_procedure()
    p.pop('candidate_graph')
    p['source_catalog'] = [s for s in p['source_catalog'] if s['id'] != 'official_mined_graph']
    p['illustrated_sequence_edges'] = p.pop('prerequisites')
    p['mandatory_prerequisite_edges'] = []
    for s in p['source_catalog']:
        path = ROOT / s['path']
        s['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return p


def anchors(c, asr):
    end = c['end_frame_inclusive']
    kind = c['kind']
    f = c['facts']
    if kind == 'tool_identity':
        a, b = c['target_interval_exclusive']
        wanted = [a - 30, a - 1, a, (a + b) // 2, b - 1, b + 15, b + 30]
    elif kind == 'observed_order':
        wanted = [n + delta for n in f['first_onsets'] for delta in [-15, 0, 15]]
    elif kind in CUTOFF_KINDS:
        component = f['component_state']['component']
        ci = next(i for i, r in enumerate(asr['components']) if r['name'] == component)
        states = [(r['frame'], r['state'][ci]) for r in asr['state_sequence'] if r['frame'] <= end]
        changes = [row for i, row in enumerate(states) if i == 0 or row[1] != states[i - 1][1]]
        transition = changes[-1][0]
        wanted = [max(c['start_frame'], transition - 15), max(c['start_frame'], transition), max(c['start_frame'], transition + 15), end - 15, end]
    else:
        a, b = f.get('target_interval', [c['start_frame'], end])
        wanted = [a - 30, a - 1, a, (a + b) // 2, b - 1, b + 15, b + 30]
    cap = end if kind in CUTOFF_KINDS else asr['frame_count'] - 1
    return sorted({max(0, min(cap, int(n))) for n in wanted})


def clip_action(row, start_key, end_key, cutoff):
    value = copy.deepcopy(row)
    a, b = row[start_key], row[end_key]
    value['start_time_s'] = a / 30
    value['end_boundary_original_s'] = b / 30 if b <= cutoff else None
    value['censored_at_question_cutoff'] = b > cutoff
    if b > cutoff:
        value[end_key] = None
    return value


def build_package(c, procedure, demonstrations):
    video = c['video_id']
    cutoff = c['end_frame_inclusive']
    atomic_path = ANNOTATIONS / 'TAS-B/front' / (video + '.json')
    coarse_path = ANNOTATIONS / 'TAS-S/front' / (video + '.json')
    state_path = ANNOTATIONS / 'ASR/annotations' / (video + '_asr.json')
    atomic, coarse, asr = [read_json(p) for p in [atomic_path, coarse_path, state_path]]
    names = {row['id']: row['name'] for row in atomic['action_labels']}
    evidence = []
    def add_ref(path, pointer):
        ref = reference(path, pointer)
        verify_reference(ref)
        sid = 'ctx_' + fingerprint([ref['path'], pointer])[:16]
        evidence.append({'source_id': sid, **ref})
        return sid
    requested = anchors(c, asr)
    lower = min(c['start_frame'], min(requested))
    upper = max(cutoff, max(requested))
    visible_limit = cutoff if c['kind'] in CUTOFF_KINDS else upper
    coarse_indices = [i for i, s in enumerate(coarse['segments']) if s['f_start'] <= visible_limit and s['f_end'] >= lower]
    coarse_rows = [{'source_id': add_ref(coarse_path, f'/segments/{i}'), **clip_action(coarse['segments'][i], 'f_start', 'f_end', visible_limit)} for i in coarse_indices]
    relevant_atomic = [i for i, s in enumerate(atomic['segments']) if s['start_frame'] <= visible_limit and s['end_frame'] >= lower and names[s['action_label']] != 'null']
    if c['kind'] == 'observed_order':
        onsets = c['facts']['first_onsets']
        relevant_atomic = [i for i in relevant_atomic if any(atomic['segments'][i]['start_frame'] <= onset + 90 and atomic['segments'][i]['end_frame'] >= onset - 60 for onset in onsets)]
    hand = c.get('hand', c['facts'].get('hand'))
    same_hand = [i for i, s in enumerate(atomic['segments']) if hand is None or s['entity'] == hand]
    prior = [i for i in same_hand if atomic['segments'][i]['end_frame'] <= lower]
    subsequent = [i for i in same_hand if upper < atomic['segments'][i]['start_frame'] <= upper + 90]
    chosen = sorted(set(relevant_atomic + sorted(prior, key=lambda i: atomic['segments'][i]['end_frame'])[-2:] + ([] if c['kind'] in CUTOFF_KINDS else sorted(subsequent, key=lambda i: atomic['segments'][i]['start_frame'])[:2])), key=lambda i: atomic['segments'][i]['start_frame'])
    atomic_rows = []
    for i in chosen:
        s = atomic['segments'][i]
        row = clip_action(s, 'start_frame', 'end_frame', cutoff) if c['kind'] in CUTOFF_KINDS else {**s, 'start_time_s': s['start_frame'] / 30, 'end_boundary_original_s': s['end_frame'] / 30}
        atomic_rows.append({'source_id': add_ref(atomic_path, f'/segments/{i}'), 'action_name': names[s['action_label']], 'context_role': 'before' if s['end_frame'] <= lower else 'after' if s['start_frame'] > upper else 'overlapping', **row})
    state_rows = []
    ci = None
    component = c['facts'].get('component_state', {}).get('component')
    if component:
        ci = next(i for i, row in enumerate(asr['components']) if row['name'] == component)
        indices = [i for i, s in enumerate(asr['state_sequence']) if s['frame'] <= visible_limit]
        prior_state = [i for i in indices if asr['state_sequence'][i]['frame'] <= lower]
        selected = ([prior_state[-1]] if prior_state else []) + [i for i in indices if asr['state_sequence'][i]['frame'] > lower]
        for i in dict.fromkeys(selected):
            s = asr['state_sequence'][i]
            state_rows.append({'source_id': add_ref(state_path, f'/state_sequence/{i}'), 'frame': s['frame'], 'time_s': s['frame'] / 30, 'component': component, 'state': s['state'][ci]})
    demo_images = []
    needed_names = set()
    if c['kind'] == 'observed_order':
        needed_names.update([c['facts']['first_action'], c['facts']['second_action']])
    elif c['kind'] in CUTOFF_KINDS:
        needed_names.add({'bearing_plate': 'insert_bearing_plate_assembly', 'adapter_plate': 'attach_adapter_plate', 'anti_vibration_handle': 'screw_on_anti_vibration_handle'}.get(component))
    for demo in demonstrations['examples']:
        if demo['action_name'] not in needed_names or demonstrations['source_video'] == video:
            continue
        verify_reference(demo['source'])
        if hashlib.sha256(Path(demo['image_path']).read_bytes()).hexdigest() != demo['sha256']:
            raise ValueError('evidence_package:demo_hash_mismatch')
        demo_images.append({'evidence_id': 'reference_' + demo['action_name'], 'path': demo['image_path'], 'sha256': demo['sha256'], 'requested_time_s': 0, 'time_scope': 'REFERENCE FROM DIFFERENT EXECUTION. Composite three frames, NOT target time. Action label: ' + demo['action_name'], 'view': 'reference_composite', 'source_video': demonstrations['source_video'], 'source_frames': demo['frames'], 'source_reference': demo['source'], 'role': 'public_action_example_not_pixel_component_label'})
    frame_plans = [{'evidence_id': 'anchor_' + str(n), 'frame_index': n, 'requested_time_s': n / 30, 'role': 'context_before' if n < c['start_frame'] else 'context_after' if n > cutoff else 'target_boundary', 'view': 'front', 'roi_xyxy': [280, 270, 1020, 700], 'canvas': [960, 560], 'path': str(OUT / 'evidence_v17_inputs/frames' / (fingerprint([video, n, 'roi960_v17'])[:24] + '.jpg'))} for n in requested]
    target = sorted(copy.deepcopy(c['image_refs']) + frame_plans, key=lambda im: (im['frame_index'], im['evidence_id']))
    available = 32 - len(demo_images)
    if len(target) > available:
        protected = [im for im in target if im['evidence_id'].startswith('anchor_') or im['frame_index'] in [c['start_frame'], cutoff]]
        candidates = [im for im in target if im not in protected]
        room = available - len(protected)
        if room < 0:
            raise ValueError('evidence_package:anchor_budget_exceeded')
        sampled = [candidates[round(i * (len(candidates) - 1) / max(1, room - 1))] for i in range(room)]
        target = sorted(protected + sampled, key=lambda im: (im['frame_index'], im['evidence_id']))
    missing = ['mandatory_prerequisite_graph', 'source_verified_receiver_relation', 'normative_duration_or_torque']
    if c['kind'] == 'action_error_category':
        missing += ['specific_error_mechanism', 'source_verified_cause_and_correction']
    if needed_names and len(demo_images) < len(needed_names):
        missing += ['disjoint_training_action_example']
    return {'package_id': 'evidence_v17_' + c['contract_id'], 'contract_id': c['contract_id'], 'video_id': video, 'kind': c['kind'], 'task': {'workflow': asr['workflow'], 'metadata': asr.get('meta_data', {}), 'view': 'front', 'fps': asr['fps'], 'frame_count': asr['frame_count']}, 'answer_contract': {'question_proposition': c['question'], 'mcq_question_proposition': c['mcq_question'], 'GT_answer': c['canonical_answer'], 'facts': c['facts'], 'options': c['options'], 'correct_option': c['correct_option'], 'source_references': [{'source_id': 's' + str(i), **r} for i, r in enumerate(c['references'])], 'target_original_frame_interval_inclusive': [c['start_frame'], cutoff]}, 'public_reference': {'procedure': procedure, 'action_examples': demo_images, 'component_identity_status': 'action-labelled examples only; no source-verified pixel component/receiver map'}, 'private_context': {'coarse_steps': coarse_rows, 'atomic_actions': atomic_rows, 'component_states': state_rows, 'state_definitions': {'-1': 'misassembled; does not establish operator error or mechanism', '0': 'unassembled', '1': 'correctly assembled; does not certify hidden torque or whole-device completion'}, 'anomaly_attribute_definitions': atomic['anomaly_types'], 'clock': {'fps': 30, 'timestamps_in': 'original_recording_seconds', 'frame_numbers_are_not_seconds': True, 'source_end_boundary_policy': 'raw annotation boundary preserved; no duration QA before separate endpoint-convention verification'}, 'atomic_context_policy': 'overlapping window plus up to two same-hand neighbours; order questions retrieve only [-2,+3] seconds around both starts', 'source_catalog_for_provenance_only': evidence}, 'target_visual': {'images': target, 'source_video': c.get('source_video', str(Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/front') / (video + '.mp4'))), 'question_cutoff_frame': cutoff if c['kind'] in CUTOFF_KINDS else None, 'target_vs_context_explicit': True}, 'missing_data': missing, 'eligibility': {'current_contract_source_ready': True, 'visual_sufficiency': 'not_yet_verified', 'normative_order_error_enabled': False, 'cause_or_correction_enabled': False, 'receiver_specific_installation_enabled': False, 'new_generation_allowed': False, 'next_action': 'materialize_frames_then_blind_visual_qualification'}, 'max_total_images': 32, 'formal_release': False}


def generation_payload(package):
    context = {k: v for k, v in package['private_context'].items() if k != 'source_catalog_for_provenance_only'}
    return {'task': package['task'], 'answer_contract': package['answer_contract'], 'reference_procedure': package['public_reference']['procedure'], 'reference_example_metadata': [{k: v for k, v in im.items() if k != 'path'} for im in package['public_reference']['action_examples']], 'execution_context': context, 'missing_data': package['missing_data'], 'eligibility': package['eligibility'], 'target_frame_metadata': [{k: im[k] for k in ['evidence_id', 'frame_index', 'requested_time_s'] if k in im} for im in package['target_visual']['images']]}


def blind_payload(package, question):
    return {'question': question, 'kind': package['kind'], 'reference_procedure': package['public_reference']['procedure'], 'reference_examples': [{'evidence_id': im['evidence_id'], 'source_video': im['source_video'], 'role': im['role'], 'label': im['evidence_id'].removeprefix('reference_')} for im in package['public_reference']['action_examples']], 'target_original_frame_interval_inclusive': package['answer_contract']['target_original_frame_interval_inclusive'], 'fps': package['task']['fps'], 'allowed_target_image_ids': [im['evidence_id'] for im in package['target_visual']['images']], 'allowed_reference_image_ids': [im['evidence_id'] for im in package['public_reference']['action_examples']]}
