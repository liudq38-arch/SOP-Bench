from pathlib import Path
from statistics import median

from impact_qa.common import ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_native import native_trial


FOLDER = ROOT / 'outputs/impact_qa/anomaly_multiview_v2'
OLD = ROOT / 'outputs/impact_qa/anomaly_contrast_v1'
ANCHORS = ['ac_caf796a863e97b95', 'ac_a0df16a2e2d3b4f3', 'ac_5bdf885219e6c3a2', 'ac_2bd6151e86531bc4', 'ac_7fb3e1f7be9b20fe', 'ac_aa972583fdcd01b3']
NEW = [('KI03AR28_Disassembly_A_001', 139.37), ('LE06AS03_Disassembly_A_003', 122.8), ('SS07EL13_Disassembly_B_005', 87.23)]


def anchor(trial, action, purpose):
    return {'anchor_id': 'mv_' + fingerprint([trial['trial_id'], action['source']['pointer']])[:12], 'trial_id': trial['trial_id'], 'hand': action['hand'], 'start_frame': action['start_frame'], 'end_frame_exclusive': action['end_frame_exclusive'], 'fps': trial['fps'], 'actions': [action], 'purpose': purpose}


def map_interval(ref, trial):
    fps = trial['fps']
    a, b = ref['start_frame'] / ref['fps'], ref['end_frame_exclusive'] / ref['fps']
    names = {x['action'] for x in ref['actions']}
    choices = []
    for row in trial['actions']:
        if row['hand'] != ref['hand'] or row['action'] not in names:
            continue
        ta, tb = row['start_frame'] / fps, row['end_frame_exclusive'] / fps
        if max(abs(ta-a), abs(tb-b)) <= 3.5:
            choices.append({'distance_s': abs(ta-a)+abs(tb-b), 'action': row})
    choices.sort(key=lambda x: x['distance_s'])
    if choices and (len(choices) == 1 or choices[1]['distance_s'] - choices[0]['distance_s'] >= .5):
        row = choices[0]['action']
        return row['start_frame'], row['end_frame_exclusive'], {'status': 'native_action_time_candidate', 'candidates': choices, 'not_frame_synchronization': True}
    front = native_trial(ref['trial_id'], 'front')
    offsets = []
    for x in front['actions']:
        xa, xb = x['start_frame']/front['fps'], x['end_frame_exclusive']/front['fps']
        if x['hand'] != ref['hand'] or min(abs(xa-a), abs(xb-b)) > 20 or x['action'] == 'null':
            continue
        nearby = [y for y in trial['actions'] if y['hand'] == x['hand'] and y['action'] == x['action'] and abs(y['start_frame']/fps-xa)<3]
        if len(nearby) == 1:
            y = nearby[0]
            offsets.append(y['start_frame']/fps-xa)
    shift = median(offsets) if offsets else 0
    start, end = max(0, round((a+shift)*fps)), min(trial['frame_count'], round((b+shift)*fps))
    return start, end, {'status': 'approximate_context_window_no_unique_action_match', 'candidate_offsets_s': offsets, 'median_offset_s': shift, 'candidates': choices, 'not_frame_synchronization': True, 'not_a_native_GT_event': True}


def prepare():
    frozen = FOLDER / 'selection_frozen.json'
    if frozen.exists():
        cases = read_jsonl(FOLDER / 'cases.jsonl')
        if fingerprint(cases) != read_json(frozen)['cases_fingerprint']:
            raise ValueError('multiview:changed_frozen_selection')
        return cases
    old = {c['case_id']: c for c in read_jsonl(OLD / 'cases.jsonl')}
    refs = []
    for key in ANCHORS:
        c = old[key]
        refs.append({'anchor_id': key, 'trial_id': c['trial_id'], 'hand': c['target_hand'], 'start_frame': c['start_frame'], 'end_frame_exclusive': c['end_frame_exclusive'], 'fps': c['clip']['fps'], 'actions': c['target_actions'], 'purpose': 'prior_uncertainty_followup'})
    for name, time_s in NEW:
        trial = native_trial(name, 'front')
        row = min((x for x in trial['actions'] if any(x['labels']) and x['action'] in ['store_screw', 'place_screw']), key=lambda x: abs(x['start_frame']/trial['fps']-time_s))
        refs.append(anchor(trial, row, 'new_part_storage_anomaly'))
        normal = [x for x in trial['actions'] if x['hand'] == row['hand'] and x['action'] in ['store_screw','place_screw'] and x['phase'] == 'normal' and not any(x['labels'])]
        purpose='new_part_storage_normal_candidate'
        if not normal:
            normal=[x for x in trial['actions'] if x['action'] in ['store_screw','place_screw'] and x['phase']=='normal' and not any(x['labels'])]
            purpose='other_hand_storage_comparison_not_matched_control'
        if not normal:raise ValueError('multiview:no_storage_normal:'+name)
        match = min(normal, key=lambda x: abs(x['start_frame']-row['start_frame']))
        refs.append(anchor(trial, match, purpose))
    cases = []
    for ref in refs:
        for view in ['front', 'top', 'ego']:
            trial = native_trial(ref['trial_id'], view)
            if view == 'front':
                a, b, mapping = ref['start_frame'], ref['end_frame_exclusive'], {'status': 'native_reference'}
            else:
                a, b, mapping = map_interval(ref, trial)
            fps = trial['fps']
            ca, cb = max(0,a-round(3*fps)), min(trial['frame_count'],b+round(6*fps))
            actions = [x for x in trial['actions'] if x['start_frame']<cb and x['end_frame_exclusive']>ca]
            target = [x for x in actions if x['hand']==ref['hand'] and x['start_frame']<b and x['end_frame_exclusive']>a]
            case = {'case_id': ref['anchor_id']+'_'+view, 'anchor': ref, 'view': view, 'trial_id': ref['trial_id'], 'target_hand': ref['hand'], 'target_interval_frames': [a,b], 'context_interval_frames': [ca,cb], 'fps': fps, 'frame_count':trial['frame_count'], 'source_video':trial['source_video'], 'mapping':mapping, 'native_target_actions':target, 'native_context_actions':actions, 'formal_release':False, 'human_review':'unreviewed'}
            if not Path(case['source_video']).exists() or not 0<=ca<=a<b<=cb<=trial['frame_count']:
                raise ValueError('multiview:media_or_interval:' + case['case_id'])
            cases.append(case)
    save_jsonl(FOLDER/'anchors.jsonl',refs)
    save_jsonl(FOLDER/'cases.jsonl',cases)
    save_jsonl(FOLDER/'first10_cases.jsonl',cases[:10])
    save_json(frozen,{'anchors':len(refs),'view_cases':len(cases),'cases_fingerprint':fingerprint(cases),'selection_purpose':'diagnostic_followup_not_independent_validation','existing_validation_participants_now_used_for_followup':True})
    return cases
