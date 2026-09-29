from collections import Counter
from hashlib import sha256

import numpy as np

from impact_qa.common import ANNOTATIONS, ROOT, TYPES, fingerprint, read_json
from impact_qa.evidence_audit import verify_native_action
from impact_qa.mcq_native import native_trial


TOOLS = {'torx_screwdriver','phillips_screwdriver','flat_head_screwdriver','combination_wrench'}
WORK = {'align','mount','dismount','insert','extract','seat','adjust','thread','tighten','loosen','hand_tighten','hand_loosen','hand_spin','attach','detach','remove','flip','rotate'}
FINGER = {'hand_tighten','hand_loosen','hand_spin','thread'}


def load_front_rows():
    rows, documents, segments, auxiliary = [], {}, set(), {}
    for path in sorted((ANNOTATIONS/'TAS-B/front').glob('*.json')):
        trial = native_trial(path.stem.removesuffix('_front'),'front')
        task_path=ANNOTATIONS/'TAS-S/front'/path.name
        task=read_json(task_path)
        auxiliary[str(task_path.relative_to(ROOT))]=sha256(task_path.read_bytes()).hexdigest()
        task_segments=task['segments']
        state_path=ANNOTATIONS/'ASR/annotations'/(trial['video_id']+'_asr.json')
        state_changes=None
        if state_path.exists():
            state=read_json(state_path)
            seq=sorted(state['state_sequence'],key=lambda r:r['frame'])
            state_changes=np.array([b['frame'] for a,b in zip(seq,seq[1:]) if a['state']!=b['state']],dtype=int)
            auxiliary[str(state_path.relative_to(ROOT))]=sha256(state_path.read_bytes()).hexdigest()
        by_hand={h:sorted([a for a in trial['actions'] if a['hand']==h],key=lambda a:a['start_frame']) for h in ['left','right']}
        for hand,actions in by_hand.items():
            groups=[]
            for a in actions:
                if groups and groups[-1][-1]['action']==a['action'] and groups[-1][-1]['end_frame_exclusive']==a['start_frame']:
                    groups[-1].append(a)
                else:
                    groups.append([a])
            merged={a['source']['pointer']:(g[0]['start_frame'],g[-1]['end_frame_exclusive']) for g in groups for a in g}
            tool,tool_start=None,None
            other=by_hand['right' if hand=='left' else 'left']
            for i,a in enumerate(actions):
                segments.add(verify_native_action(a,documents))
                start,end=a['start_frame'],a['end_frame_exclusive']
                duration=(end-start)/trial['fps']
                previous=actions[i-1] if i else None
                noun,verb=a['noun'],a['verb']
                if verb in {'pick_up','hold'} and noun in TOOLS:
                    tool,tool_start=noun,start
                elif verb in {'place','store','transfer'} or (verb=='pick_up' and noun not in TOOLS):
                    tool,tool_start=None,None
                if tool_start is not None and (start-tool_start)/trial['fps']>60:
                    tool,tool_start=None,None
                overlap=[b for b in other if b['start_frame']<end and b['end_frame_exclusive']>start]
                active=sum(max(0,min(end,b['end_frame_exclusive'])-max(start,b['start_frame'])) for b in overlap if b['verb'] in WORK)
                paired_tool=[b['noun'] for b in overlap if b['verb']=='hold' and b['noun'] in TOOLS]
                phases=[s for s in task_segments if s['f_start']<end and s['f_end']+1>start]
                stage=max(phases,key=lambda s:min(end,s['f_end']+1)-max(start,s['f_start']))['label'] if phases else None
                group_start,group_end=merged[a['source']['pointer']]
                rows.append(dict(row_id=fingerprint([a['source']['path'],a['source']['pointer']])[:20],trial_id=trial['trial_id'],participant=trial['trial_id'].split('_')[0],model=trial['trial_id'].split('_')[-2],workflow='assemble' if '_Reassembly_' in trial['trial_id'] else 'disassemble',view='front',fps=trial['fps'],source_video=trial['source_video'],frame_count=trial['frame_count'],action=a,duration_s=duration,previous_action=previous,stage=stage,other_hand_actions=overlap,other_hand_task_action_fraction=min(1,active/(end-start)),inferred_same_hand_tool=tool,tool_state_start_frame=tool_start,other_hand_explicit_hold_tools=paired_tool,has_ASR=state_changes is not None,ASR_state_changes=None if state_changes is None else int(np.searchsorted(state_changes,end)-np.searchsorted(state_changes,start,side='right')),merged_same_action_start=group_start,merged_same_action_end=group_end,merged_same_action_duration_s=(group_end-group_start)/trial['fps']))
    return rows,dict(TASB_documents={p:v[1] for p,v in documents.items()},auxiliary_documents=auxiliary,unique_segments=len(segments))


def rule_masks(rows):
    verb=np.array([r['action']['verb'] for r in rows])
    noun=np.array([r['action']['noun'] for r in rows])
    action=np.array([r['action']['action'] for r in rows])
    previous=np.array([r['previous_action']['verb'] if r['previous_action'] else '' for r in rows])
    duration=np.array([r['duration_s'] for r in rows])
    merged_duration=np.array([r['merged_same_action_duration_s'] for r in rows])
    assemble=np.array([r['workflow']=='assemble' for r in rows])
    work_fraction=np.array([r['other_hand_task_action_fraction'] for r in rows])
    tools=np.isin(noun,list(TOOLS))
    rules={}
    def add(key,category,description,mask,kind='annotation_proxy_not_verified_visual_rule'):
        rules[key]=dict(category=category,description=description,mask=mask,kind=kind)
    add('H_hand_spin','handling','verb == hand_spin',verb=='hand_spin')
    add('S_place_prev_loosen','spatial','place/store; immediately preceding same-hand verb is loosen',np.isin(verb,['place','store'])&(previous=='loosen'))
    add('S_place_prev_tighten','spatial','place/store; immediately preceding same-hand verb is tighten',np.isin(verb,['place','store'])&(previous=='tighten'))
    add('S_all_place_store','spatial','all place/store',np.isin(verb,['place','store']))
    for threshold in [5,8,10,15,20,30]:
        add('T_null_'+str(threshold),'temporal','null atomic duration >= '+str(threshold)+'s',(action=='null')&(duration>=threshold))
        add('T_merged_null_'+str(threshold),'temporal','null label-blind contiguous same-action duration >= '+str(threshold)+'s; evaluated per raw atom',(action=='null')&(merged_duration>=threshold),'segmentation_sensitivity')
    add('P_reassembly_dismount','procedural','Reassembly and verb == dismount',assemble&(verb=='dismount'))
    add('P_reassembly_reverse','procedural','Reassembly and dismount/extract/remove/loosen/hand_loosen/detach',assemble&np.isin(verb,['dismount','extract','remove','loosen','hand_loosen','detach']))
    add('W_tool_pick_align','wrong_tool','pick_up/align with named tool noun',np.isin(verb,['pick_up','align'])&tools)
    add('W_tool_pick','wrong_tool','pick_up with named tool noun',(verb=='pick_up')&tools)
    for threshold in [0,5,8,15]:
        hold=(verb=='hold')&~tools&(noun!='null')&assemble&(duration>=threshold)
        add('T_assembly_part_hold_'+str(threshold),'temporal','Reassembly hold part >= '+str(threshold)+'s',hold)
        add('T_assembly_part_hold_quiet_other_'+str(threshold),'temporal','Reassembly hold part >= '+str(threshold)+'s; other-hand task-action overlap <= 10%',hold&(work_fraction<=.1))
    add('T_tool_hold','temporal','hold named tool',(verb=='hold')&tools)
    add('H_tool_hold','handling','hold named tool',(verb=='hold')&tools)
    inferred=np.array([r['inferred_same_hand_tool'] is not None for r in rows])
    fingers=np.isin(verb,list(FINGER))
    paired=np.array([bool(r['other_hand_explicit_hold_tools']) for r in rows])
    add('H_tool_carried_finger','handling','finger action; inferred same-hand tool state refreshed <=60s before atom start; persistence unverified',fingers&inferred)
    add('T_tool_carried_finger','temporal','finger action; inferred same-hand tool state refreshed <=60s before atom start; persistence unverified',fingers&inferred)
    add('H_opposite_tool_hold_finger','handling','finger action overlapping other-hand explicit tool hold',fingers&paired)
    add('T_opposite_tool_hold_finger','temporal','finger action overlapping other-hand explicit tool hold',fingers&paired)
    add('W_inferred_tool_period','wrong_tool','all atoms with conservatively inferred same-hand named tool held',inferred)
    for target in ['handling','temporal']:
        for v in ['hand_spin','hand_tighten','hand_loosen','thread']:
            add(target[0].upper()+'_carried_'+v,target,'inferred tool carried with '+v,inferred&(verb==v))
    return rules


def metric(mask,truth,durations):
    tp=int(np.sum(mask&truth));fp=int(np.sum(mask&~truth));fn=int(np.sum(~mask&truth));tn=int(np.sum(~mask&~truth))
    precision=tp/(tp+fp) if tp+fp else None
    recall=tp/(tp+fn) if tp+fn else None
    prevalence=float(np.mean(truth))
    return dict(triggered=tp+fp,TP=tp,FP=fp,FN=fn,TN=tn,GT_precision=precision,GT_recall=recall,GT_prevalence=prevalence,lift=None if precision is None or not prevalence else precision/prevalence,GT_duration_recall=float(np.sum(durations[mask&truth])/np.sum(durations[truth])) if np.any(truth) else None,GT_binary_accuracy=(tp+tn)/len(mask),accuracy_note='all-negative baseline may dominate; GT is not independent truth')


def evaluate(rows,rules):
    labels=np.array([r['action']['labels'] for r in rows],dtype=bool)
    durations=np.array([r['duration_s'] for r in rows])
    result=[]
    predictions=np.zeros_like(labels)
    base={'H_hand_spin','S_place_prev_loosen','T_null_8','P_reassembly_dismount','W_tool_pick_align'}
    for key,rule in rules.items():
        mask=rule['mask'];i=TYPES.index(rule['category'])
        record=dict(rule_id=key,**{k:v for k,v in rule.items() if k!='mask'},**metric(mask,labels[:,i],durations),cross_labels={t:int(np.sum(mask&labels[:,j])) for j,t in enumerate(TYPES)},subgroups={})
        for group in ['workflow','model']:
            record['subgroups'][group]={}
            for value in sorted({r[group] for r in rows}):
                take=np.array([r[group]==value for r in rows])
                record['subgroups'][group][value]=metric(mask[take],labels[take,i],durations[take])
        result.append(record)
        if key in base: predictions[:,i]|=mask
    return dict(rules=result,baseline_rule_ids=sorted(base),class_totals={t:int(labels[:,i].sum()) for i,t in enumerate(TYPES)},baseline_union_any_anomaly=metric(predictions.any(axis=1),labels.any(axis=1),durations),baseline_typed_micro=dict(TP=int(np.sum(predictions&labels)),predicted_labels=int(predictions.sum()),GT_positive_labels=int(labels.sum()),precision=float(np.sum(predictions&labels)/predictions.sum()),recall=float(np.sum(predictions&labels)/labels.sum())),view='front',atomic_rows=len(rows),videos=len({r['trial_id'] for r in rows}),not_visual_accuracy=True,wrong_part_no_operational_proxy=True)
