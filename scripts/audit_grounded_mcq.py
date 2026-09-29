import argparse
import asyncio
from pathlib import Path
import sys


ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import read_json,read_jsonl,save_json,save_jsonl
from impact_qa.mcq_grouped_media import prepare_window_media
from impact_qa.mcq_grouped_review import array,enum,evidence_errors,obj
from impact_qa.structured_video_client import StructuredVideoPool


async def run(round_name, exact=False):
    folder=ROOT/'outputs/impact_qa/mcq_grouped_v1'
    source=folder/round_name
    config=read_json(source/'selection.json')['config']
    config['target_overlay']=True
    config['workers']=2
    config['per_service_concurrency']=2
    candidates=read_jsonl(source/'annotation_backed_candidates.jsonl')
    units={u['unit_id']:u for u in read_jsonl(folder/'candidate_units.jsonl')}
    stage='critic_exact' if exact else 'critic'
    pool=StructuredVideoPool(config,source/stage)
    sem=asyncio.Semaphore(config['workers'])
    prompt=(ROOT/'prompts/impact_qa/mcq_grouped_v1/critic.txt').read_text()
    if exact:
        prompt+='\nOnly target-interval frames are included in this audit video. Explicitly report which anatomical hand performs the annotated action. A hand that merely stabilizes while the other turns the shaft is not the hand performing shaft rotation. Do not let a matching object name substitute for the correct actor and interaction.\n'
    save_json(source/stage/'frozen.json',{'prompt':prompt,'config':config,'exact_target_only':exact})

    async def audit(question):
        async with sem:
            unit=units[question['question_id']]
            record=read_json(source/'results'/(unit['unit_id']+'.json'))
            result={'question_id':unit['unit_id'],'accepted_for_human_review':True,'events':[]}
            result['status']='model_screened_candidate_only_requires_independent_review'
            for segment in question['abnormal_segments']:
                eid=segment['event_id']
                event=next(e for ep in unit['episodes'] for e in ep['events'] if e['event_id']==eid)
                short_types=[label for label,seconds in event.get('type_support_seconds',{}).items() if seconds<config.get('minimum_type_support_seconds',0)]
                if short_types:
                    result['events'].append({'event_id':eid,'accepted':False,'hold_reason':'type_support_below_minimum','types':short_types})
                    result['accepted_for_human_review']=False
                    continue
                old=record['event_reviews'][eid]
                chosen=next(w for w in record['windows'] if w['media']['sha256']==old['media_sha256'])
                window=dict(chosen['window'],events=[event])
                if exact:
                    window['start_frame']=max(window['start_frame'],event['start_frame'])
                    window['end_frame_exclusive']=min(window['end_frame_exclusive'],event['end_frame_exclusive'])
                media=await asyncio.to_thread(prepare_window_media,unit,window,config,folder)
                payload={'case_id':unit['unit_id']+'_'+eid,'hand':event['hand'],'target_interval_frames':[event['start_frame'],event['end_frame_exclusive']],'annotation_actions':event.get('action_names',[]),'blind_observation':old['observation']['description'],'grounded_description':old['type_review']['action_grounding']['description'],'video_sampling':media['sampled_frames']}
                schema=obj({'claims_consistent':{'type':'boolean'},'action_visible':{'type':'boolean'},'matches_annotation_action':{'type':'boolean'},'tool_contact_status':enum(['used_for_action','held_not_used','no_tool','unclear']),'confidence':enum(['high','medium','low']),'evidence_frame_ids':array(enum(f['frame_id'] for f in media['sampled_frames']),0,4),'factual_description':{'type':'string'},'reason':{'type':'string'}})
                if exact:
                    schema['properties']['performing_hand']=enum(['left','right','both','unclear'])
                    schema['required'].append('performing_hand')
                try:
                    reply=await pool.call('factual_critic',prompt,payload,schema,1600,video=media)
                    out=reply['result']
                    issues=evidence_errors(out['evidence_frame_ids'],event,media)
                    accepted=out['claims_consistent'] and out['action_visible'] and out['matches_annotation_action'] and out['confidence']=='high' and not issues
                    if exact:
                        accepted &= out['performing_hand'] in [event['hand'],'both']
                    result['events'].append({'event_id':eid,'accepted':accepted,'audit':out,'evidence_errors':issues,'media':media})
                    result['accepted_for_human_review'] &= accepted
                except Exception as exc:
                    result['events'].append({'event_id':eid,'accepted':False,'error':str(exc)})
                    result['accepted_for_human_review']=False
            save_json(source/stage/'results'/(unit['unit_id']+'.json'),result)
            return result
    try:
        records=await asyncio.gather(*(audit(q) for q in candidates))
    finally:
        await pool.close()
    by_id={r['question_id']:r for r in records}
    kept=[dict(q,factual_critic=by_id[q['question_id']],status='awaiting_independent_visual_audit') for q in candidates if by_id[q['question_id']]['accepted_for_human_review']]
    save_jsonl(source/(stage+'_candidates.jsonl'),kept)
    save_jsonl(source/(stage+'_decisions.jsonl'),records)
    summary={'input_candidates':len(candidates),'kept_for_independent_audit':len(kept),'held':len(candidates)-len(kept),'formal_release':False}
    save_json(source/stage/'summary.json',summary)
    print(summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('round')
    parser.add_argument('--exact',action='store_true')
    args=parser.parse_args()
    asyncio.run(run(args.round,args.exact))
