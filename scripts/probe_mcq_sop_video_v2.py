import argparse
import asyncio
import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json
from impact_qa.mcq_sop_video import prepare_video, target_windows
from impact_qa.mcq_sop_validation import validate_result
from impact_qa.structured_video_client import StructuredVideoPool


async def run(args):
    config=read_json(ROOT/'configs/impact_qa/mcq_sop_video_v2.json')
    config['base_urls']=args.endpoints.split(',')
    config['per_service_concurrency']=args.concurrency
    folder=ROOT/config['output_root']
    questions=read_jsonl(ROOT/config['input_root']/'kept_questions.jsonl')
    groups={g['group_id']:g for g in read_jsonl(ROOT/'outputs/impact_qa/front_mcq_expansion_v1/groups.jsonl')}
    reference=read_json(ROOT/config['input_root']/'sop_reference.json')
    profile=config['profiles'][args.profile]
    eligible=sorted((q for q in questions if q['filter']['minimum_duration_s']>=profile['max_window_s']-2),key=lambda q:-q['filter']['minimum_duration_s'])
    selected=[]
    for m,w in [('A','assemble'),('B','assemble'),('A','disassemble'),('B','disassemble')]:
        subset=[q for q in eligible if groups[q['group_id']]['model']==m and groups[q['group_id']]['workflow']==w]
        if subset:selected.append(subset[0])
    selected+= [q for q in eligible if q not in selected]
    selected=selected[:args.limit]
    records=[]
    for q in selected:
        g=groups[q['group_id']]
        s=q['filter']['target_segments'][0]
        sop=reference['procedures'][g['model']+'_'+g['workflow']]
        window=target_windows(s,g,config,profile)[0]
        record=prepare_video(q,g,s,sop,window,config,args.profile)
        records.append(record)
        print(json.dumps(dict(stage='prepared',window_id=record['window_id'],question_id=q['question_id'],profile=args.profile,frames=record['case']['sampling'],processor_shape=record['processor_shape'],visual_tokens=record['estimated_visual_tokens']),ensure_ascii=False),flush=True)
    save_json(folder/f'prepared_{args.profile}.json',records)
    if args.prepare_only:return
    system=(ROOT/'prompts/impact_qa/mcq_sop_video_v2_system.txt').read_text()
    schema=read_json(ROOT/'prompts/impact_qa/mcq_sop_visual_v1_schema.json')
    pool=StructuredVideoPool(config,folder)
    async def call(record):
        target=record['case']['target']
        local_schema=copy.deepcopy(schema)
        local_schema['properties']['evidence_frames'].pop('uniqueItems',None)
        local_schema['properties']['evidence_frames']['items']['enum']=[f['frame_index'] for f in record['frames'] if f['role']=='target']
        local_schema['properties']['matched_sop_step']['enum']=[s['id'] for s in record['sop']['steps']]+['unknown']
        for field in ['t_start','t_end']:
            local_schema['properties']['evidence_actions']['items']['properties'][field].update(minimum=target['start_s'],maximum=target['end_s'])
        payload=dict(sop=record['sop'],case=record['case'],case_id=record['window_id'],time_reminder=f"视频时间0起算；本次只判断[{target['start_s']},{target['end_s']})秒；证据时间必须落在该范围。")
        video=dict(record,path=record['video_path'],sha256=record['video_sha256'],sampled_frames=record['frames'])
        output=dict(question_id=record['question_id'],trial_id=record['trial_id'],segment_id=record['segment_id'],window_id=record['window_id'],profile=args.profile,status='failed')
        errors=[]
        for attempt in range(config['attempts']):
            try:
                prompt=system if not errors else system+'\n上次返回未通过输出合同，仅修正格式与时间，不据此改变视觉结论。错误：'+errors[-1][-450:]
                response=await pool.call('sop_video_verify',prompt,payload,local_schema,config['maximum_generation_tokens'],video,lambda value:validate_result(value,schema,record))
                mapped=copy.deepcopy(response['result'])
                for action in mapped['evidence_actions']:
                    action['t_start']=round(action['t_start']+record['clip_offset_s'],6)
                    action['t_end']=round(action['t_end']+record['clip_offset_s'],6)
                output.update(mapped,status='ok',attempts=attempt+1,window_local_result=response['result'],clip_offset_s=record['clip_offset_s'],usage=response['usage'],api_cache_key=response['cache_key'],seconds=response['seconds'],media_manifest=str(folder/'video_manifests'/(record['window_id']+'.json')),prompt_fingerprint=fingerprint([system,local_schema]))
                break
            except Exception as exc:
                errors.append(type(exc).__name__+':'+str(exc))
        output['errors']=errors
        save_json(folder/'window_results'/(record['window_id']+'.json'),output)
        return output
    try:
        results=await asyncio.gather(*(call(r) for r in records))
    finally:
        await pool.close()
    save_json(folder/f'probe_{args.profile}_{args.concurrency}.json',results)
    print(json.dumps(dict(status='probe_finished',profile=args.profile,requests=len(results),ok=sum(r['status']=='ok' for r in results)),ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=['video128','video256','video256_detail'],default='video128')
    parser.add_argument('--limit',type=int,default=4)
    parser.add_argument('--concurrency',type=int,default=1)
    parser.add_argument('--endpoints',default='http://127.0.0.1:8002/v1')
    parser.add_argument('--prepare-only',action='store_true')
    asyncio.run(run(parser.parse_args()))


if __name__=='__main__':main()
