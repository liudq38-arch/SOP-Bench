import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.atr_qa import ANNOTATIONS, FOLDER, ROOT, VIDEOS, context, interval, iou, materialize, source_ref
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl


def main():
    rows=[]
    for hand in ['L','R']:
        path=ANNOTATIONS/f'ATR/atr_segments_{hand}/train.split1.jsonl'
        for index,row in enumerate(read_jsonl(path)):
            if row['view'] not in ['ego','front']:continue
            row['_manifest_source']=source_ref(path,f'/jsonl/{index}',{k:v for k,v in row.items() if not k.startswith('_')},'atr_'+row['view'])
            rows.append(row)
    docs={r['video_id']:read_json(ANNOTATIONS/'TAS-B'/r['annotation_path']) for r in rows}
    groups=defaultdict(lambda:defaultdict(list))
    for r in rows:
        trial=r['video_id'].rsplit('_',1)[0]
        if not (VIDEOS/r['view']/(r['video_id']+'.mp4')).exists():continue
        groups[(trial,r['entity'],tuple(r['labels']))][r['view']].append(r)
    pairs=[]
    for (trial,hand,labels),views in groups.items():
        for ego in views['ego']:
            ranked=sorted([(iou(interval(ego,docs),interval(f,docs)),f) for f in views['front']],key=lambda x:x[0],reverse=True)
            if not ranked or ranked[0][0]<.4 or (len(ranked)>1 and ranked[0][0]-ranked[1][0]<.15):continue
            score,front=ranked[0]
            reverse=sorted([(iou(interval(e,docs),interval(front,docs)),e['sample_id']) for e in views['ego']],reverse=True)
            if reverse[0][1]!=ego['sample_id']:continue
            if interval(ego,docs)[1]-interval(ego,docs)[0]>30:continue
            pairs.append({'pair_id':'atr_'+fingerprint([ego['sample_id'],front['sample_id']])[:16],'trial':trial,'hand':hand,'labels':ego['label_names'],'iou':score,'ego':ego,'front':front})
    pairs.sort(key=lambda p:fingerprint(p['pair_id']))
    chosen=[];trials=set()
    for p in pairs:
        if 'error_wrong_tool' in p['labels'] and p['trial'] not in trials and len(chosen)<12:
            chosen.append(p);trials.add(p['trial'])
    for label in ['error_wrong_part','error_spatial','error_handling','error_temporal','error_procedural']:
        matches=[p for p in pairs if label in p['labels'] and 'error_wrong_tool' not in p['labels'] and p not in chosen]
        matches.sort(key=lambda p:(p['trial'] in trials,fingerprint(p['pair_id'])))
        if matches:chosen.append(matches[0]);trials.add(matches[0]['trial'])
    cases=[]
    for pair in chosen:
        facts=context(pair['ego'],docs[pair['ego']['video_id']])+context(pair['front'],docs[pair['front']['video_id']])
        sources=[pair[v]['_manifest_source'] for v in ['ego','front']]+[f['source'] for f in facts]
        shared={'atr_labels':pair['labels'],'target_hand':pair['hand'],'atomic_context':[{k:v for k,v in f.items() if k!='source'} for f in facts],'allowed_source_ids':[s['source_id'] for s in sources],'normative_correct_tool':None,'correction_deadline':None,'recovery_event_link':None,'rules':['TAS-S has_anomaly is unavailable as normality evidence.','null means action identity unavailable in that view, not proof of inactivity.','Later normal action or different tool is not proof of successful recovery.','This dataset marks wrong-tool usage but does not always state the correct replacement.']}
        for view in ['ego','front']:
            r=pair[view];case={'case_id':pair['pair_id']+'_'+view,'pair_id':pair['pair_id'],'trial':pair['trial'],'view':view,'video_id':r['video_id'],'source_video':str(VIDEOS/view/(r['video_id']+'.mp4')),'metadata':docs[r['video_id']]['meta_data'],'interval_s':list(interval(r,docs)),'source_interval_inclusive':[r['start_frame'],r['end_frame']],'pair_iou':pair['iou'],'shared_gt':shared,'source_catalog':sources,'split':'official_ATR_train_S1','historically_exposed_training_not_independent':True}
            path=FOLDER/'cases'/(case['case_id']+'.json')
            if path.exists():
                old=read_json(path)
                if {k:v for k,v in old.items() if k not in ['images','image_manifest']}!=case:raise ValueError('atr_prepare:changed_case')
                case=old
            else:case=materialize(case);save_json(path,case)
            for im in case['images']:
                if not Path(im['path']).exists():raise ValueError('atr_prepare:missing_media')
            cases.append(case);print(case['case_id'],flush=True)
    save_jsonl(FOLDER/'cases.jsonl',cases);save_jsonl(FOLDER/'first10.jsonl',cases[:10]);save_jsonl(FOLDER/'paired_selection.jsonl',chosen)
    report={'available_matched_pairs':len(pairs),'selected_pairs':len(chosen),'view_cases':len(cases),'selected_labels':dict(Counter(l for p in chosen for l in p['labels'])),'trials':len(trials),'participants':len({p['trial'].split('_')[0] for p in chosen}),'min_pair_iou':min(p['iou'] for p in chosen),'images_per_case':28,'selection_before_model_results':True,'official_val_test_used':False,'normative_expected_tool_available':False,'timely_deadline_available':False}
    save_json(ROOT/'reports/impact_qa/atr_v19_precheck.json',report);print(report)


if __name__=='__main__':main()
