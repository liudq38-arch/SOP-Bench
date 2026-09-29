import asyncio
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import read_json,read_jsonl,save_json
from impact_qa.front_mcq_expansion import FOLDER,export
from impact_qa.front_mcq_media import prepare_media
from impact_qa.mcq_grouped_review import array,enum,obj
from impact_qa.structured_video_client import StructuredVideoPool
from scripts.run_front_mcq_expansion import validate


async def main():
    groups=read_jsonl(FOLDER/'groups.jsonl')
    config=read_json(ROOT/'configs/impact_qa/front_mcq_expansion_v1.json')
    prompt=(ROOT/'prompts/impact_qa/front_mcq_expansion_v1.txt').read_text()+'\nREPAIR OUTPUT: Use the schema object keys for each event and each proposed category. Do not include event_id/category fields inside values. Each category has its own enumerated TARGET frame IDs. Re-examine the video; do not copy or invent evidence. Provide exactly the schema keys.'
    pool=StructuredVideoPool(config,FOLDER/'repairs')
    sem=asyncio.Semaphore(6)
    async def one(group):
        path=FOLDER/'results'/(group['group_id']+'.json')
        if path.exists() and read_json(path).get('status')=='ok':return
        async with sem:
            original=read_json(path) if path.exists() else {'status':'missing'}
            backup=FOLDER/'repairs'/'original_results'/(group['group_id']+'.json')
            if not backup.exists():save_json(backup,original)
            try:
                media=await asyncio.to_thread(prepare_media,group,FOLDER,config)
                properties={}
                for event in group['events']:
                    valid=[f['frame_id'] for f in media['sampled_frames'] if event['start_frame']<=f['source_frame_index']<event['end_frame_exclusive']]
                    outside=[f['frame_id'] for f in media['sampled_frames'] if not event['start_frame']<=f['source_frame_index']<event['end_frame_exclusive']]
                    context=[outside[i] for i in np.rint(np.linspace(0,len(outside)-1,min(16,len(outside)))).astype(int)] if outside else []
                    context_schema=array(enum(context),0,4) if context else array({'type':'string'},0,0)
                    check=obj(dict(verdict=enum(['supported','contradicted','insufficient']),reason={'type':'string'},alternative={'type':'string'},evidence_frame_ids=array(enum(valid),0,4),context_frame_ids=context_schema))
                    properties[event['event_id']]=obj(dict(facts={'type':'string'},progress=enum(['visible_state_change','productive_support','motion_only','no_visible_progress','unclear']),progress_evidence={'type':'string'},checks=obj({t:check for t in event['proposed_categories']})))
                schema=obj(properties)
                payload=dict(case_id=group['group_id'],view='front',model=group['model'],workflow=group['workflow'],
                             step_context=group['step_context'],action_annotations_fallible=group['action_context'],
                             frame_map=[dict(frame_id=f['frame_id'],source_s=round(f['source_pts_s'],3)) for f in media['sampled_frames']],
                             targets=[dict(event_id=e['event_id'],hand=e['hand'],source_interval_s=[e['start_frame']/group['fps'],e['end_frame_exclusive']/group['fps']],proposed_categories=e['proposed_categories']) for e in group['events']])
                response=await pool.call('front_mcq_repair',prompt,payload,schema,config['maximum_generation_tokens'],video=media)
                items=[]
                for event_id,item in response['result'].items():
                    items.append(dict(event_id=event_id,**{k:v for k,v in item.items() if k!='checks'},checks=[dict(category=t,**v) for t,v in item['checks'].items()]))
                value={'items':items};validate(value,group,media)
                save_json(path,dict(group_id=group['group_id'],status='ok',generation_identity=read_json(FOLDER/'generation_frozen.json')['identity'],items=value['items'],media=media,api_cache_key=response['cache_key'],repair=True,repair_cache_root=str(FOLDER/'repairs')))
                print('repaired',group['group_id'],flush=True)
            except Exception as exc:
                print('repair_failed',group['group_id'],repr(exc),flush=True)
            export(groups)
    selected=[g for g in groups if (FOLDER/'results'/(g['group_id']+'.json')).exists() and read_json(FOLDER/'results'/(g['group_id']+'.json')).get('status')=='error']
    try:await asyncio.gather(*(one(g) for g in selected))
    finally:await pool.close()
    print(export(groups),flush=True)


if __name__=='__main__':asyncio.run(main())
