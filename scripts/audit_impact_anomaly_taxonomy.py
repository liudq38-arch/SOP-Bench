from collections import Counter,defaultdict
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import ANNOTATIONS,read_json,read_jsonl,save_json,save_jsonl


def main():
    folder=ROOT/'reports/impact_qa/anomaly_taxonomy_audit'
    folder.mkdir(parents=True,exist_ok=True)
    paths=sorted((ANNOTATIONS/'TAS-B').glob('*/*.json'))
    print({'preflight':'CPU JSON analysis','annotation_files':len(paths),'first_file':str(paths[0])},flush=True)
    names=['error_temporal','error_spatial','error_handling','error_wrong_part','error_wrong_tool','error_procedural']
    top_keys=Counter()
    segment_keys=Counter()
    taxonomy_fields=Counter()
    view_files=Counter()
    phase=defaultdict(Counter)
    totals=Counter()
    normal=Counter()
    normal_example={}
    action_counts=[Counter() for _ in names]
    single_counts=[Counter() for _ in names]
    duration=[defaultdict(float) for _ in names]
    front_rows=[]
    sources=[]
    mismatches=[]
    for p in paths:
        d=read_json(p)
        view=d['view']
        view_files[view]+=1
        top_keys.update(d.keys())
        mapping={r['id']:r['name'] for r in d['action_labels']}
        fps=d['meta_data']['fps']
        if [r['name'] for r in d['anomaly_types']]!=names:
            mismatches.append(str(p))
        for r in d['anomaly_types']:
            taxonomy_fields.update(r.keys())
        source={'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        sources.append(source)
        for i,r in enumerate(d['segments']):
            segment_keys.update(r.keys())
            phase[view][r['phase']]+=1
            totals['segments_all_views']+=1
            if view!='front':
                continue
            action=mapping[r['action_label']]
            labels=[j for j,v in enumerate(r['anomaly_type']) if v]
            seconds=(r['end_frame']+1-r['start_frame'])/fps
            totals['segments_front']+=1
            row={'video_id':d['video_id'],'view':view,'hand':r['entity'],'action':action,'phase':r['phase'],'labels':[names[j] for j in labels],'start_frame':r['start_frame'],'end_frame_inclusive':r['end_frame'],'fps':fps,'interval_s':[r['start_frame']/fps,(r['end_frame']+1)/fps],'duration_s':seconds,'source':dict(source,pointer=f'/segments/{i}')}
            if not labels and r['phase']=='normal':
                normal[action]+=1
                normal_example.setdefault(action,row)
            if not labels:
                continue
            totals['anomalous_action_segments_front']+=1
            totals['multilabel_action_segments_front']+=len(labels)>1
            front_rows.append(row)
            for j in labels:
                action_counts[j][action]+=1
                duration[j][action]+=seconds
                if len(labels)==1:
                    single_counts[j][action]+=1
    atr_keys=Counter()
    atr_totals=Counter()
    atr_front=Counter()
    for hand in ['L','R']:
        for split in ['train','val','test']:
            p=ANNOTATIONS/'ATR'/('atr_segments_'+hand)/(split+'.split1.jsonl')
            sources.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            for r in read_jsonl(p):
                atr_keys.update(r.keys())
                atr_totals[r['view']]+=1
                if r['view']=='front':
                    atr_front.update(r['label_names'])
    classes=[]
    examples=[]
    for j,name in enumerate(names):
        selected=[r for r in front_rows if name in r['labels']]
        nonnull=[r for r in selected if r['action']!='null']
        labels=action_counts[j]
        common=sum(n for a,n in labels.items() if a!='null' and normal[a])
        top=[{'action':a,'anomaly_segments':n,'normal_segments_same_action':normal[a],'type_duration_s':round(duration[j][a],3),'single_type_segments':single_counts[j][a]} for a,n in labels.most_common(12)]
        cls={'id':j,'name':name,'front_TASB_action_segments':len(selected),'front_ATR_segments':atr_front[name],'single_type_action_segments':sum(single_counts[j].values()),'null_action_segments':labels['null'],'nonnull_anomaly_segments':len(nonnull),'nonnull_segments_whose_action_also_normal':common,'nonnull_action_names':len([a for a in labels if a!='null']),'all_nonnull_actions_have_normal_examples':all(normal[a]>0 for a in labels if a!='null'),'top_actions':top}
        seen=set()
        candidates=sorted(nonnull,key=lambda r:(len(r['labels'])!=1,not 3<=r['duration_s']<=20,-r['duration_s']))
        for r in candidates:
            if r['action'] in seen:
                continue
            seen.add(r['action'])
            examples.append({'category':name,'anomaly_example':r,'normal_same_action_examples':[normal_example[r['action']]] if r['action'] in normal_example else [],'reason_status':'category_and_action_only_no_causal_annotation'})
            if len(seen)==5:
                break
        classes.append(cls)
    report={'annotation_version':'v1.1','unit_note':'TASB atomic segments; co-label counts overlap; views are not independent trials','files':dict(view_files),'totals':dict(totals),'TASB_document_fields':dict(top_keys),'TASB_segment_fields':dict(segment_keys),'taxonomy_entry_fields':dict(taxonomy_fields),'ATR_fields':dict(atr_keys),'ATR_records_split1_by_view':dict(atr_totals),'phase_by_view':{v:dict(c) for v,c in phase.items()},'taxonomy_mismatches':mismatches,'classes':classes}
    save_json(folder/'annotation_audit.json',report)
    save_jsonl(folder/'front_anomaly_actions.jsonl',front_rows)
    save_jsonl(folder/'category_examples.jsonl',examples)
    save_json(folder/'annotation_source_manifest.json',sources)
    save_jsonl(folder/'first10_anomaly_actions.jsonl',front_rows[:10])
    print({'files':dict(view_files),'totals':dict(totals),'TASB_segment_fields':list(segment_keys),'ATR_fields':list(atr_keys),'taxonomy_mismatches':mismatches},flush=True)
    for c in classes:
        print(c,flush=True)


if __name__=='__main__':
    main()
