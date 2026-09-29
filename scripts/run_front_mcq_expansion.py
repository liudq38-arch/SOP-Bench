import argparse
import asyncio
import fcntl
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import TYPES,fingerprint,read_json,save_json
from impact_qa.front_mcq_expansion import FOLDER,export,prepare
from impact_qa.front_mcq_media import prepare_media
from impact_qa.mcq_grouped_review import array,enum,obj
from impact_qa.structured_video_client import StructuredVideoPool


def schema(group,media):
    refs=array(enum(f['frame_id'] for f in media['sampled_frames']),0,4)
    check=obj(dict(category=enum(TYPES),verdict=enum(['supported','contradicted','insufficient']),reason={'type':'string'},alternative={'type':'string'},evidence_frame_ids=refs,context_frame_ids=refs))
    item=obj(dict(event_id=enum(e['event_id'] for e in group['events']),facts={'type':'string'},progress=enum(['visible_state_change','productive_support','motion_only','no_visible_progress','unclear']),progress_evidence={'type':'string'},checks=array(check,1,6)))
    return obj(dict(items=array(item,len(group['events']),len(group['events']))))


def validate(value,group,media):
    if sorted(i['event_id'] for i in value['items'])!=sorted(e['event_id'] for e in group['events']):
        raise ValueError('front_expansion:event_set')
    frames={f['frame_id']:f['source_frame_index'] for f in media['sampled_frames']}
    events={e['event_id']:e for e in group['events']}
    for item in value['items']:
        event=events[item['event_id']]
        cats=[c['category'] for c in item['checks']]
        if len(cats)!=len(set(cats)) or not set(event['proposed_categories']).issubset(cats):
            raise ValueError('front_expansion:category_set')
        for c in item['checks']:
            ids=c['evidence_frame_ids']
            if len(ids)!=len(set(ids)) or any(not event['start_frame']<=frames[f]<event['end_frame_exclusive'] for f in ids):
                raise ValueError('front_expansion:target_citation')
            if c['verdict']=='supported' and len(ids)<2:
                raise ValueError('front_expansion:unsupported_citation')
            if c['category']=='temporal' and c['verdict']=='contradicted' and item['progress'] not in ['visible_state_change','productive_support']:
                c['verdict']='insufficient'
                c['alternative']='自动校验降级：可见手部运动不等于任务有效推进。'+c['alternative']


async def run(args,groups):
    import av,httpx,torch
    if not torch.cuda.is_available():raise RuntimeError('front_expansion:CUDA_unavailable')
    config=read_json(ROOT/'configs/impact_qa/front_mcq_expansion_v1.json')
    if args.single_service:config['base_urls']=['http://127.0.0.1:8002/v1']
    async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
        for base in config['base_urls']:
            response=await client.get(base+'/models');response.raise_for_status()
            if config['model'] not in [m['id'] for m in response.json()['data']]:raise ValueError('front_expansion:model_mismatch')
    save_json(FOLDER/'preflight.json',dict(torch=torch.__version__,cuda=torch.version.cuda,gpus=torch.cuda.device_count(),av=av.__version__,config=config))
    prompt=(ROOT/'prompts/impact_qa/front_mcq_expansion_v1.txt').read_text()
    identity=fingerprint([prompt,config['video_pixel_budget'],Path(__file__).read_text(),(ROOT/'impact_qa/front_mcq_media.py').read_text()])
    frozen=FOLDER/'generation_frozen.json'
    if frozen.exists() and read_json(frozen)['identity']!=identity:raise ValueError('front_expansion:run_changed')
    save_json(frozen,dict(identity=identity,prompt=prompt,config=config))
    pool=StructuredVideoPool(config,FOLDER)
    slots=asyncio.Semaphore(config['workers'])
    decoding=asyncio.Semaphore(config['decode_workers'])
    selected=groups[:args.limit] if args.limit else groups
    export(groups)
    async def process(group):
        path=FOLDER/'results'/(group['group_id']+'.json')
        if path.exists() and read_json(path).get('status')=='ok':return
        async with slots:
            record=dict(group_id=group['group_id'],status='error',generation_identity=identity)
            try:
                async with decoding:
                    media=await asyncio.to_thread(prepare_media,group,FOLDER,config)
                frame_map=[dict(frame_id=f['frame_id'],source_s=round(f['source_pts_s'],3)) for f in media['sampled_frames']]
                payload=dict(case_id=group['group_id'],view='front',model=group['model'],workflow=group['workflow'],
                             source_interval_s=[group['start_frame']/group['fps'],group['end_frame_exclusive']/group['fps']],
                             step_context=group['step_context'],action_annotations_fallible=group['action_context'],frame_map=frame_map,
                             targets=[dict(event_id=e['event_id'],hand=e['hand'],source_interval_s=[e['start_frame']/group['fps'],e['end_frame_exclusive']/group['fps']],
                                           proposed_categories=e['proposed_categories'],valid_target_frame_ids=[f['frame_id'] for f in media['sampled_frames'] if e['start_frame']<=f['source_frame_index']<e['end_frame_exclusive']]) for e in group['events']])
                response=await pool.call('front_mcq_review',prompt,payload,schema(group,media),config['maximum_generation_tokens'],video=media,validator=lambda x:validate(x,group,media))
                record.update(status='ok',items=response['result']['items'],media=media,api_cache_key=response['cache_key'])
            except Exception as exc:record['error']=f'{type(exc).__name__}:{exc}'
            save_json(path,record)
            print(group['group_id'],record['status'],record.get('error',''),flush=True)
            export(groups)
    try:await asyncio.gather(*(process(g) for g in selected))
    finally:await pool.close()
    print(export(groups),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--limit',type=int)
    parser.add_argument('--single-service',action='store_true')
    args=parser.parse_args()
    FOLDER.mkdir(parents=True,exist_ok=True)
    with (FOLDER/'runner.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        groups=prepare()
        if args.prepare_only:print(export(groups),flush=True)
        else:asyncio.run(run(args,groups))


if __name__=='__main__':main()
