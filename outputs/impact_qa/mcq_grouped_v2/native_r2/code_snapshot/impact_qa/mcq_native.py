from collections import Counter, defaultdict
from functools import lru_cache

from impact_qa.common import ANNOTATIONS, ROOT, fingerprint, read_json, read_jsonl


VIEWS = ('front', 'top', 'ego')
VIDEO_ROOT = ROOT / '/data_1/ldq/dataset/impact/IMPACT-v1.1/videos'


@lru_cache(maxsize=1)
def atr_index():
    index=defaultdict(list)
    for hand in ['L','R']:
        for split in ['train','val','test']:
            path=ANNOTATIONS/'ATR'/('atr_segments_'+hand)/(split+'.split1.jsonl')
            sha=__import__('hashlib').sha256(path.read_bytes()).hexdigest()
            for i,row in enumerate(read_jsonl(path)):
                index[(row['video_id'],row['entity'])].append(dict(row,source={'path':str(path.relative_to(ROOT)),'pointer':f'/jsonl/{i}','sha256':sha}))
    return index


@lru_cache(maxsize=400)
def native_trial(trial_id, view):
    path = ANNOTATIONS / 'TAS-B' / view / (trial_id + '_' + view + '.json')
    doc = read_json(path)
    names = {x['id']: x['name'] for x in doc['action_labels']}
    verbs = {x['id']: x['name'] for x in doc['verbs']}
    nouns = {x['id']: x['name'] for x in doc['nouns']}
    sha = __import__('hashlib').sha256(path.read_bytes()).hexdigest()
    actions = []
    for i, row in enumerate(doc['segments']):
        actions.append({'start_frame': row['start_frame'], 'end_frame_exclusive': row['end_frame'] + 1, 'hand': row['entity'], 'action': names[row['action_label']], 'verb': verbs.get(row['verb'],'null'), 'noun': nouns.get(row['noun'],'null'), 'phase': row['phase'], 'labels': row['anomaly_type'], 'source': {'path': str(path.relative_to(ROOT)), 'pointer': f'/segments/{i}', 'sha256': sha}})
    return {'trial_id': trial_id, 'video_id': doc['video_id'], 'view': view, 'fps': doc['meta_data']['fps'], 'frame_count': doc['meta_data']['num_frames'], 'actions': actions, 'source_video': str(VIDEO_ROOT / view / (doc['video_id'] + '.mp4')), 'annotation_meta': doc['meta_data']}


def stable_runs(trial):
    result = []
    for hand in ['left', 'right']:
        runs = []
        for action in sorted((a for a in trial['actions'] if a['hand'] == hand), key=lambda a: a['start_frame']):
            key = (action['phase'], tuple(action['labels']))
            if runs and runs[-1]['end_frame_exclusive'] == action['start_frame'] and runs[-1]['key'] == key:
                runs[-1]['end_frame_exclusive'] = action['end_frame_exclusive']
                runs[-1]['actions'].append(action)
            else:
                runs.append({'key': key, 'hand': hand, 'start_frame': action['start_frame'], 'end_frame_exclusive': action['end_frame_exclusive'], 'actions': [action], 'labels': action['labels'], 'phase': action['phase']})
        for run in runs:
            run.pop('key')
            run['duration_s'] = (run['end_frame_exclusive'] - run['start_frame']) / trial['fps']
            run['action_names'] = sorted({a['action'] for a in run['actions'] if a['action'] != 'null'})
            run['run_id'] = 'nr_' + fingerprint([trial['video_id'], hand, run['start_frame'], run['end_frame_exclusive'], run['labels']])[:16]
        result.extend(runs)
    return result


def match_run(reference, source_fps, target_trial):
    a, b = reference['start_frame'] / source_fps, reference['end_frame_exclusive'] / source_fps
    names = set(reference['action_names'])
    candidates = []
    for run in stable_runs(target_trial):
        if run['hand'] != reference['hand']:
            continue
        ta, tb = run['start_frame'] / target_trial['fps'], run['end_frame_exclusive'] / target_trial['fps']
        common = names.intersection(run['action_names'])
        if not common or abs(ta - a) > 2.5 or abs(tb - b) > 2.5:
            continue
        if abs(run['duration_s'] - (b-a)) > max(2.5, (b-a)*0.35):
            continue
        candidates.append((abs(ta-a)+abs(tb-b), run, sorted(common)))
    candidates.sort(key=lambda x: (x[0], x[1]['run_id']))
    if not candidates:
        return None, {'status': 'no_unambiguous_action_time_match'}
    if len(candidates) > 1 and candidates[1][0]-candidates[0][0] < 0.5:
        return None, {'status': 'ambiguous_match', 'candidate_ids': [r[1]['run_id'] for r in candidates]}
    distance, run, common = candidates[0]
    return run, {'status': 'matched_native_action_interval', 'boundary_distance_sum_s': distance, 'common_action_names': common, 'native_labels_differ': run['labels'] != reference['labels'], 'mapping_is_not_frame_synchronization': True}


def make_case(trial, run, family, parent_clip_id=None, diagnostic=False):
    if run['duration_s'] > 20:
        raise ValueError('native_mcq:pilot_requires_complete_run_at_most_20s')
    if any(run['labels']):
        correct = [chr(66+i) for i, flag in enumerate(run['labels']) if flag]
    elif run['phase'] == 'normal' and run['action_names']:
        correct = ['A']
    else:
        raise ValueError('native_mcq:invalid_normal_scope')
    event = dict(run, event_id=run['run_id'])
    a,b=run['start_frame'],run['end_frame_exclusive']
    neighbors = [r for r in trial['actions'] if r['hand']==run['hand'] and r['action']!='null']
    before = [r for r in neighbors if r['end_frame_exclusive']<=a][-2:]
    after = [r for r in neighbors if r['start_frame']>=b][:2]
    case_id = 'nq_' + fingerprint([trial['video_id'],run['run_id']])[:16]
    clip = {'clip_id':case_id,'video_id':trial['video_id'],'view':trial['view'],'fps':trial['fps'],'start_frame':a,'end_frame_exclusive':b,'source_video':trial['source_video'],'workflow':'assemble' if '_Reassembly_' in trial['video_id'] else 'disassemble','duration_s':run['duration_s']}
    atr=[r for r in atr_index().get((trial['video_id'],run['hand']),[]) if r['start_frame']<b and r['end_frame']+1>a]
    if correct==['A'] and atr:
        raise ValueError('native_mcq:normal_conflicts_with_ATR:'+case_id)
    if correct!=['A'] and not any(r['start_frame']<=a and r['end_frame']+1>=b and all(not flag or r['labels'][i] for i,flag in enumerate(run['labels'])) for r in atr):
        raise ValueError('native_mcq:ATR_does_not_cover_TASB_scope:'+case_id)
    return {'case_id':case_id,'family_id':family,'parent_clip_id':parent_clip_id,'view':trial['view'],'clip':clip,'event':event,'atr_sources':atr,'neighbor_actions':{'before':before,'after':after},'correct_option_ids':correct,'production_duration_eligible':run['duration_s']+1e-8>=5,'diagnostic_only':diagnostic or run['duration_s']<5,'formal_release':False,'human_review':'unreviewed'}


def prepare_native_pilot():
    parent=ROOT/'outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix4'
    old=read_jsonl(ROOT/'outputs/impact_qa/mcq_grouped_v1/candidate_units.jsonl')
    wanted=['mq_c06bafe3703fb66a','mq_c105936e99e64dc1','mq_fb80b543a58ba765','mq_c4a0a6ef5c5ad443','mq_6c9ec5129cc832f0','mq_f8f51a185a960bd4']
    cases, mappings = [], []
    for uid in wanted:
        unit=next(u for u in old if u['unit_id']==uid)
        event=unit['episodes'][0]['events'][0]
        trial_id=unit['clip']['trial_id']
        front=native_trial(trial_id,'front')
        choices=[r for r in stable_runs(front) if r['hand']==event['hand'] and any(r['labels']) and r['start_frame']>=event['start_frame'] and r['end_frame_exclusive']<=event['end_frame_exclusive'] and r['action_names']]
        reference=max(choices,key=lambda r:r['duration_s'])
        for view in VIEWS:
            trial=native_trial(trial_id,view)
            run,match=(reference,{'status':'native_reference'}) if view=='front' else match_run(reference,front['fps'],trial)
            mappings.append({'family_id':uid,'view':view,'reference_run':reference,'match':match,'native_run':run})
            if run:
                cases.append(make_case(trial,run,uid,unit['parent_clip_id']))
    controls=[]
    for uid in ['mq_c06bafe3703fb66a','mq_c105936e99e64dc1']:
        unit=next(u for u in old if u['unit_id']==uid)
        trial_id=unit['clip']['trial_id']
        front=native_trial(trial_id,'front')
        target=unit['episodes'][0]['events'][0]
        normal=[r for r in stable_runs(front) if r['hand']==target['hand'] and r['phase']=='normal' and not any(r['labels']) and 5<=r['duration_s']<=20 and r['action_names'] and any(a.startswith(('loosen','hand_loosen','tighten')) for a in r['action_names'])]
        if not normal:
            continue
        ref=min(normal,key=lambda r:min(abs(r['end_frame_exclusive']-target['start_frame']),abs(r['start_frame']-target['end_frame_exclusive'])))
        for view in VIEWS:
            trial=native_trial(trial_id,view)
            run,match=(ref,{'status':'native_reference'}) if view=='front' else match_run(ref,front['fps'],trial)
            if run and run['phase']=='normal' and not any(run['labels']):
                control=make_case(trial,run,uid+'_normal_control',unit['parent_clip_id'])
                controls.append(control)
    stats=Counter()
    canonical=defaultdict(list)
    for c in read_jsonl(parent/'manifest.jsonl'):
        trial=native_trial(c['trial_id'],'front')
        for r in stable_runs(trial):
            if any(r['labels']) and c['start_frame']<=r['start_frame']<r['end_frame_exclusive']<=c['end_frame_exclusive']:
                canonical[r['run_id']].append((r,c))
    for pairs in canonical.values():
        r,c=min(pairs,key=lambda p:(p[1]['duration_s'],p[1]['clip_id']))
        stats['all_unique_anomaly_runs']+=1
        stats['runs_ge5']+=r['duration_s']>=5-1e-8
        stats['runs_ge5_with_action']+=r['duration_s']>=5-1e-8 and bool(r['action_names'])
        stats['runs_1p5_to_5']+=1.5<=r['duration_s']<5-1e-8
        stats['runs_below_1p5']+=r['duration_s']<1.5
    return cases+controls,mappings,dict(stats)


def draft_question(case, options):
    clip=case['clip']
    hand=case['event']['hand']
    return {'question_id':case['case_id'],'family_id':case['family_id'],'parent_clip_id':case['parent_clip_id'],'view':case['view'],'kind':'mcq_anomaly_native_interval','question':f"During the {hand}-hand operation in this video segment, is there an anomaly? Select all applicable types, or Correct if none applies.",'options':options,'correct_option_ids':case['correct_option_ids'],'answer_basis':'native_view_TASB_with_ATR_crosscheck','scope':{'hand':hand,'local_interval_s':[0,round(clip['duration_s'],3)],'source_interval_frames':[clip['start_frame'],clip['end_frame_exclusive']],'source_interval_s':[clip['start_frame']/clip['fps'],clip['end_frame_exclusive']/clip['fps']],'fps':clip['fps']},'gt_actions':case['event']['actions'],'atr_sources':case['atr_sources'],'status':'GT_draft_visual_audit_pending','diagnostic_only':case['diagnostic_only'],'formal_release':False,'human_review':'unreviewed'}
