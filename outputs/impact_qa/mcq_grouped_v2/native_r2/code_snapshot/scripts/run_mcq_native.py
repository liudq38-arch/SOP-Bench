import argparse
import asyncio
from collections import Counter
import fcntl
from pathlib import Path
import sys


ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import fingerprint,read_json,save_json,save_jsonl
from impact_qa.mcq_native import draft_question,prepare_native_pilot
from impact_qa.mcq_native_checks import interaction_issues
from impact_qa.mcq_grouped_media import prepare_window_media
from impact_qa.mcq_grouped_review import array,enum,evidence_errors,obj
from impact_qa.structured_video_client import StructuredVideoPool


def observe_schema(media):
    item=obj({'hand':enum(['left','right']),'hand_identity':enum(['clear','unclear']),'interaction':enum(['holding','manipulating_part','rotating_fastener_with_fingers','rotating_fastener_with_tool','rotating_shaft','placing','picking_up','mixed','unclear']),'tool_contact':enum(['used_for_action','held_without_use','absent','unclear']),'object':{'type':'string'},'description':{'type':'string'},'evidence_frame_ids':array(enum(f['frame_id'] for f in media['sampled_frames']),0,4),'confidence':enum(['high','medium','low'])})
    item['properties']['tool_tip_relation']=enum(['touching_target','pointing_away','occluded','no_tool','mixed'])
    item['required'].append('tool_tip_relation')
    return obj({'hands':array(item,2,2)})


def ground_schema(case,media):
    labels=[x for x in case['correct_option_ids'] if x!='A']
    item=obj({'option_id':enum(labels or ['A']),'evidence_status':enum(['explained','observed_only','occluded','conflicts']),'evidence_frame_ids':array(enum(f['frame_id'] for f in media['sampled_frames']),0,4),'reason':{'type':'string'}})
    return obj({'visible_action':enum(['supported','partial','unclear','conflicts']),'hand_identity':enum(['clear','unclear']),'tool_contact':enum(['used_for_action','held_without_use','absent','unclear']),'claim_consistency':enum(['consistent','conflicts','unclear']),'factual_description':{'type':'string'},'evidence_frame_ids':array(enum(f['frame_id'] for f in media['sampled_frames']),0,4),'confidence':enum(['high','medium','low']),'anomaly_evidence':array(item,len(labels),len(labels))})


def gate(case,media,observed,grounded):
    issues=interaction_issues(case,observed)
    target=next(h for h in observed['hands'] if h['hand']==case['event']['hand'])
    if grounded['visible_action']!='supported' or grounded['claim_consistency']!='consistent':
        issues.append('action_or_claim_not_supported')
    if target['hand_identity']!='clear' or grounded['hand_identity']!='clear':
        issues.append('hand_identity_unclear')
    if target['confidence']!='high' or grounded['confidence']!='high':
        issues.append('visual_confidence_below_high')
    if target['tool_contact']!=grounded['tool_contact']:
        issues.append('tool_contact_disagreement')
    for ids in [target['evidence_frame_ids'],grounded['evidence_frame_ids']]:
        issues.extend(evidence_errors(ids,case['event'],media,minimum_span=0.5))
    if case['diagnostic_only']:
        issues.append('below_5s_diagnostic_only')
    types=[x for x in case['correct_option_ids'] if x!='A']
    if sorted(x['option_id'] for x in grounded['anomaly_evidence'])!=types:
        issues.append('type_set_mismatch')
    explained=bool(types) and all(r['evidence_status']=='explained' and not evidence_errors(r['evidence_frame_ids'],case['event'],media,minimum_span=0.5) for r in grounded['anomaly_evidence'])
    if any(r['evidence_status']=='conflicts' for r in grounded['anomaly_evidence']):
        issues.append('visual_GT_conflict')
    return {'gt_candidate_supported':not issues,'anomaly_reason_explained':explained and not issues,'issues':sorted(set(issues))}


async def run(folder,cases,config):
    import torch
    if not torch.cuda.is_available():
        raise ValueError('native_preflight:cuda_unavailable')
    prompts={s:(ROOT/'prompts/impact_qa'/config['prompt_directory']/(s+'.txt')).read_text() for s in ['observe','ground']}
    code={p:(ROOT/p).read_text() for p in ['impact_qa/mcq_native.py','scripts/run_mcq_native.py','impact_qa/mcq_grouped_media.py','impact_qa/mcq_native_checks.py']}
    version=fingerprint([config,cases,prompts,code])
    if (folder/'frozen.json').exists() and read_json(folder/'frozen.json')['version']!=version:
        raise ValueError('native:changed_configuration_requires_new_round')
    save_json(folder/'frozen.json',{'version':version,'config':config,'prompts':prompts,'code':code,'torch':torch.__version__,'cuda':torch.version.cuda})
    pool=StructuredVideoPool(config,folder)
    sem=asyncio.Semaphore(config['workers'])
    options=read_json(ROOT/config['parent_root']/'mcq_options.json')

    async def process(case):
        path=folder/'results'/(case['case_id']+'.json')
        if path.exists() and read_json(path).get('status')=='ok':
            return read_json(path)
        async with sem:
            record={'case_id':case['case_id'],'status':'error','view':case['view'],'family_id':case['family_id']}
            try:
                cfg=dict(config,detail_crop=config['crops'].get(case['view']))
                window={'start_frame':case['event']['start_frame'],'end_frame_exclusive':case['event']['end_frame_exclusive'],'events':[case['event']]}
                media=await asyncio.to_thread(prepare_window_media,case,window,cfg,folder)
                payload={'case_id':case['case_id'],'view':case['view'],'video_sampling':media['sampled_frames'],'duration_s':case['clip']['duration_s']}
                def check_observed(value):
                    if sorted(r['hand'] for r in value['hands'])!=['left','right']:
                        raise ValueError('native_observation:hand_set_mismatch')
                observed=await pool.call('native_observe',prompts['observe'],payload,observe_schema(media),1700,video=media,validator=check_observed)
                model='B' if '_B_' in case['clip']['video_id'] else 'A'
                reference=(ROOT/'prompts/impact_qa'/('v28r_object_knowledge_'+model+'.txt')).read_text()
                guided=dict(payload,target_hand=case['event']['hand'],gt_actions=case['event']['actions'],gt_answer_options=[o for o in options if o['id'] in case['correct_option_ids']],neighbors_not_shown=case['neighbor_actions'],domain_reference=reference,blind_observation=observed['result'])
                grounded=await pool.call('native_ground',prompts['ground'],guided,ground_schema(case,media),1900,video=media)
                decision=gate(case,media,observed['result'],grounded['result'])
                question=draft_question(case,options)
                question.update(video_path=media['path'],visual_observation=observed['result'],visual_review=grounded['result'],automatic_gate=decision,status='GT_candidate_needs_independent_audit' if decision['gt_candidate_supported'] else 'held',answer='; '.join(o['id']+'. '+o['name'] for o in options if o['id'] in case['correct_option_ids']))
                record.update(status='ok',media=media,question=question,gate=decision)
            except Exception as exc:
                record['error']=f'{type(exc).__name__}:{exc}'
            save_json(path,record)
            print({k:record.get(k) for k in ['case_id','status','view','gate','error']},flush=True)
            return record
    try:
        records=await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    questions=[r['question'] for r in records if r['status']=='ok']
    save_jsonl(folder/'questions.jsonl',questions)
    save_jsonl(folder/'visual_reviews.jsonl',records)
    save_jsonl(folder/'held.jsonl',[q for q in questions if q['status']=='held'])
    summary={'cases':len(cases),'completed':len(questions),'errors':[r for r in records if r['status']=='error'],'by_view':dict(Counter(q['view'] for q in questions)),'supported_GT_candidates':sum(q['automatic_gate']['gt_candidate_supported'] for q in questions),'explained_anomaly_candidates':sum(q['automatic_gate']['anomaly_reason_explained'] for q in questions),'held':sum(q['status']=='held' for q in questions),'issues':dict(Counter(i for q in questions for i in q['automatic_gate']['issues'])),'formal_release':False,'human_review':'unreviewed','new_api_calls':len(pool.calls)}
    save_json(folder/'summary.json',summary)
    print(summary,flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--round',default='native_r1')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--detail-review',action='store_true')
    args=parser.parse_args()
    config=read_json(ROOT/'configs/impact_qa/mcq_grouped_v1.json')
    config.update(sample_fps=4,video_width=960,workers=4,per_service_concurrency=4,target_overlay=False)
    config.update(prompt_directory='mcq_grouped_v2_detail' if args.detail_review else 'mcq_grouped_v2',crops={'front':[0.33,0.42,0.65,0.75],'top':[0.2,0.3,0.68,0.78],'ego':[0.02,0.45,0.92,1.0]} if args.detail_review else {'front':[0.2,0.3,0.8,0.95]})
    folder=ROOT/'outputs/impact_qa/mcq_grouped_v2'/args.round
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'runner.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        cases,mappings,stats=prepare_native_pilot()
        save_jsonl(folder/'cases.jsonl',cases)
        save_json(folder/'mapping_audit.json',mappings)
        save_json(folder/'stable_run_population.json',stats)
        save_jsonl(folder/'first10_cases.jsonl',cases[:10])
        print(stats,flush=True)
        print([(c['case_id'],c['view'],c['correct_option_ids']) for c in cases[:10]],flush=True)
        if not args.prepare_only:
            asyncio.run(run(folder,cases,config))


if __name__=='__main__':
    main()
