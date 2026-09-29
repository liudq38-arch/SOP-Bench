import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import TYPES,fingerprint,read_json,read_jsonl,save_json,save_jsonl
from impact_qa.front_rule_metrics import evaluate,load_front_rows,rule_masks
from impact_qa.mcq_native import native_trial
from impact_qa.review_frames import render_case


OUT=ROOT/'outputs/impact_qa/front_rule_coverage_v1'


def select(rows,rules):
    rng=np.random.default_rng(20260928)
    specs=[('spin','H_hand_spin','handling',3,2),('spatial','S_place_prev_loosen','spatial',2,2),('null','T_null_8','temporal',2,2),('hold','T_assembly_part_hold_quiet_other_8','temporal',2,2),('reverse','P_reassembly_dismount','procedural',2,2),('carried','H_tool_carried_finger','either_handling_temporal',2,2),('wrongtool',None,'wrong_tool',3,0),('wrongpart',None,'wrong_part',3,0)]
    cases,selection,used=[],[],set()
    for family,rule_key,category,positive,negative in specs:
        mask=rules[rule_key]['mask'] if rule_key else np.ones(len(rows),dtype=bool)
        truth=np.array([bool(r['action']['labels'][2] or r['action']['labels'][0]) if category=='either_handling_temporal' else bool(r['action']['labels'][TYPES.index(category)]) for r in rows])
        for label,n in [(True,positive),(False,negative)]:
            if n==0:continue
            pool=np.flatnonzero(mask&(truth==label))
            order=rng.permutation(pool)
            trials=set(); chosen=[]
            for idx in order:
                r=rows[int(idx)]
                if r['row_id'] in used or r['trial_id'] in trials:continue
                chosen.append(r);used.add(r['row_id']);trials.add(r['trial_id'])
                if len(chosen)==n:break
            for j,r in enumerate(chosen):
                key=f'{family}_{"gt" if label else "other"}_{j+1}'
                a=r['action'];trial=native_trial(r['trial_id'],'front');fps=r['fps']
                start,end=a['start_frame'],a['end_frame_exclusive'];ca,cb=max(0,start-round(6*fps)),min(trial['frame_count'],end+round(8*fps))
                context=[b for b in trial['actions'] if b['start_frame']<cb and b['end_frame_exclusive']>ca]
                case=dict(case_id=key,trial_id=r['trial_id'],view='front',target_hand=a['hand'],target_interval_frames=[start,end],context_interval_frames=[ca,cb],fps=fps,source_video=r['source_video'],sample_counts=[4,16 if r['duration_s']>12 else 10,4],source_action=a,native_context_actions=context,row_id=r['row_id'],rule_id=rule_key,selection_stratum='GT_label_present' if label else 'GT_label_absent',formal_release=False,human_review='unreviewed')
                cases.append(case);selection.append(dict(case_id=key,feature_row=r))
    return cases,selection


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--render',action='store_true')
    args=parser.parse_args()
    import av,torch
    if not torch.cuda.is_available():raise RuntimeError('front_rules:cuda_preflight_failed')
    save_json(OUT/'preflight.json',dict(torch=torch.__version__,cuda=torch.version.cuda,cuda_available=True,visible_gpus=torch.cuda.device_count(),av=av.__version__,processing='CPU, 3 decoding workers',model_requests=0))
    rows,sources=load_front_rows();rules=rule_masks(rows);metrics=evaluate(rows,rules)
    if len(rows)!=13512 or metrics['videos']!=112 or sources['unique_segments']!=13512:
        raise ValueError('front_rules:unexpected_corpus')
    if any(r['view']!='front' or '/front/' not in r['action']['source']['path'] for r in rows):
        raise ValueError('front_rules:non_front_input')
    frozen=OUT/'frozen.json'
    if frozen.exists() and read_json(frozen)['rows_fingerprint']!=fingerprint(rows):
        raise ValueError('front_rules:input_changed')
    save_json(OUT/'sources.json',sources)
    save_jsonl(OUT/'rows.jsonl',rows)
    save_jsonl(OUT/'first10_rows.jsonl',rows[:10])
    save_json(OUT/'metrics.json',metrics)
    save_jsonl(OUT/'rule_hits.jsonl',[dict(rule_id=k,row_ids=[r['row_id'] for r,m in zip(rows,s['mask']) if m]) for k,s in rules.items()])
    cases,selection=(read_jsonl(OUT/'cases.jsonl'),read_jsonl(OUT/'selection.jsonl')) if frozen.exists() else select(rows,rules)
    if frozen.exists() and read_json(frozen)['cases_fingerprint']!=fingerprint(cases):
        raise ValueError('front_rules:sample_changed')
    save_jsonl(OUT/'cases.jsonl',cases);save_jsonl(OUT/'selection.jsonl',selection)
    save_jsonl(OUT/'first10_cases.jsonl',cases[:10])
    save_json(frozen,dict(rows_fingerprint=fingerprint(rows),cases_fingerprint=fingerprint(cases),seed=20260928,sampling='GT-stratified diagnostic; unique trial within stratum; not accuracy evaluation',rows=len(rows),cases=len(cases)))
    for r in rows[:10]:print(r['row_id'],r['action']['action'],r['duration_s'],flush=True)
    for m in metrics['rules']:
        if m['rule_id'] in ['H_hand_spin','S_place_prev_loosen','T_null_8','T_merged_null_8','T_assembly_part_hold_8','T_assembly_part_hold_quiet_other_8','H_tool_carried_finger','T_tool_carried_finger','P_reassembly_dismount','W_tool_pick_align']:
            print(m['rule_id'],m['triggered'],m['TP'],m['GT_precision'],m['GT_recall'],flush=True)
    print('cases',len(cases),flush=True)
    if args.render:
        with ThreadPoolExecutor(max_workers=3) as pool:
            manifests=list(pool.map(lambda c:render_case(c,OUT),cases))
        save_json(OUT/'frame_manifest.json',manifests)
        print('rendered',len(manifests),'frames',sum(len(m['frames']) for m in manifests),flush=True)


if __name__=='__main__':main()
