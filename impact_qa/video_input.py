import asyncio
import hashlib
import math
import subprocess
import time
from pathlib import Path

import httpx

from impact_qa.common import FFMPEG, OUT, ROOT, fingerprint, read_json, save_json


CONFIG=read_json(ROOT/'configs/impact_qa/video_v20.json')
FOLDER=OUT/'atr_video_v20'


def windows(start,end,size,overlap):
    result=[]
    while start<end:
        stop=min(end,start+size)
        result.append((start,stop))
        if stop>=end:break
        start=stop-overlap
    return result


def prepare_windows(case):
    from vllm.multimodal.media.image import ImageMediaIO
    from vllm.multimodal.media.video import VideoMediaIO
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize

    results=[]
    source=Path(case['source_video']);a,b=case['interval_s'];duration=case['metadata']['num_frames']/case['metadata']['fps']
    for profile,policy in CONFIG['profiles'].items():
        start=max(0,a-policy['before_s']);end=min(duration,b+policy['after_s'])
        for index,(left,right) in enumerate(windows(start,end,policy['max_window_s'],policy['overlap_s'])):
            identifier=f'{case["case_id"]}_{profile}_{index}'
            dest=FOLDER/'clips'/(identifier+'.mp4');dest.parent.mkdir(parents=True,exist_ok=True)
            manifest=FOLDER/'windows'/(identifier+'.json')
            key=fingerprint([str(source),source.stat().st_size,source.stat().st_mtime_ns,left,right,CONFIG])
            if manifest.exists():
                old=read_json(manifest)
                if old['preparation_key']!=key:raise ValueError('video_input:changed_cached_window')
                results.append(old);continue
            if not dest.exists():
                tmp=dest.with_name(dest.stem+'.tmp.mp4')
                subprocess.run([FFMPEG,'-nostdin','-v','error','-ss',str(left),'-i',str(source),'-t',str(right-left),'-vf',f'scale={CONFIG["image_max_width"]}:-2','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(tmp)],check=True,capture_output=True,timeout=180)
                tmp.replace(dest)
            io={'video_backend':CONFIG['media_backend'],'fps':policy['fps'],'num_frames':policy['num_frames']}
            frames,meta=VideoMediaIO(ImageMediaIO(),**io).load_file(dest)
            if len(frames)<CONFIG['min_decoded_frames']:
                io['fps']=-1;io['num_frames']=CONFIG['min_decoded_frames']
                frames,meta=VideoMediaIO(ImageMediaIO(),**io).load_file(dest)
            if not CONFIG['min_decoded_frames']<=len(frames)<=policy['num_frames']:raise ValueError('video_input:frame_budget')
            h,w=frames.shape[1:3]
            nh,nw=smart_resize(len(frames),h,w,min_pixels=4096,max_pixels=CONFIG['mm_processor_kwargs']['size']['longest_edge'])
            indices=meta['frames_indices'];local=[i/meta['fps'] for i in indices]
            record={'window_id':identifier,'case_id':case['case_id'],'pair_id':case['pair_id'],'view':case['view'],'profile':profile,'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'preparation_key':key,'source_start_s':left,'source_end_s':right,'target_original_interval_s':[a,b],'target_local_interval_s':[max(a,left)-left,min(b,right)-left] if min(b,right)>max(a,left) else None,'media_io_kwargs':{'video':io},'mm_processor_kwargs':CONFIG['mm_processor_kwargs'],'decoded_frames':len(frames),'source_shape':[h,w],'processor_shape':[nh,nw],'estimated_visual_tokens':math.ceil(len(frames)/2)*(nh//32)*(nw//32),'sampled_frame_indices':indices,'sampled_local_times_s':local,'sampled_original_times_s':[left+t for t in local],'loader_metadata':meta}
            save_json(manifest,record);results.append(record)
    return results


class VideoClient:
    def __init__(self,base_url):
        self.http=httpx.AsyncClient(base_url=base_url,trust_env=False,timeout=480)
        self.base_url=base_url

    async def close(self):await self.http.aclose()

    async def call(self,window,prompt,payload,max_tokens=None):
        content=[{'type':'text','text':__import__('json').dumps(payload,ensure_ascii=False)},{'type':'video_url','video_url':{'url':Path(window['path']).as_uri()}}]
        request={'model':CONFIG['model'],'messages':[{'role':'system','content':prompt},{'role':'user','content':content}],'media_io_kwargs':window['media_io_kwargs'],'mm_processor_kwargs':window['mm_processor_kwargs'],'max_tokens':max_tokens or CONFIG['max_tokens'],'temperature':CONFIG['temperature'],'top_p':CONFIG['top_p'],'seed':CONFIG['seed'],'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_object'}}
        key=fingerprint([request,window['sha256']]);path=FOLDER/'api_cache'/(key+'.json')
        if path.exists() and read_json(path).get('status')=='ok':return read_json(path)
        for attempt in range(3):
            started=time.monotonic()
            try:
                response=await self.http.post('/chat/completions',json=request);response.raise_for_status();body=response.json()
                if body['choices'][0]['finish_reason']=='length':raise ValueError('video_client:truncated')
                result=__import__('json').loads(body['choices'][0]['message']['content'])
                record={'cache_key':key,'status':'ok','window_id':window['window_id'],'base_url':self.base_url,'seconds':time.monotonic()-started,'usage':body['usage'],'request':request,'result':result,'raw_response':body};save_json(path,record);return record
            except Exception as exc:
                save_json(path,{'status':'error','attempt':attempt+1,'window_id':window['window_id'],'request':request,'error':f'{type(exc).__name__}:{exc}'})
                if attempt==2:raise
                await asyncio.sleep(2**attempt)
