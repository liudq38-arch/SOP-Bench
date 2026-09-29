import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_jsonl, save_json
from impact_qa.video_input import CONFIG, FOLDER, VideoClient


async def main():
    windows=[w for w in read_jsonl(FOLDER/'windows.jsonl') if w['decoded_frames']==64][:6]
    if len(windows)!=6:raise ValueError('capacity:need_six_64_frame_windows')
    clients=[VideoClient(url) for url in CONFIG['base_urls']];samples=[];done=asyncio.Event()
    async def monitor():
        while not done.is_set():
            proc=await asyncio.create_subprocess_exec('nvidia-smi','--query-gpu=index,memory.used','--format=csv,noheader,nounits',stdout=asyncio.subprocess.PIPE)
            out,_=await proc.communicate();samples.append(out.decode().strip())
            try:await asyncio.wait_for(done.wait(),timeout=1)
            except asyncio.TimeoutError:pass
    async def request(i,w):
        try:
            r=await clients[i//2].call(w,'Return only JSON with a short visible tool description under key tool and a boolean visible. Do not infer hidden tool type.',{'capacity_probe':'six_requests_two_per_service','view':w['view']},max_tokens=160)
            return {'window_id':w['window_id'],'status':'ok','seconds':r['seconds'],'usage':r['usage'],'cache_key':r['cache_key']}
        except Exception as exc:return {'window_id':w['window_id'],'status':'error','error':str(exc)}
    monitor_task=asyncio.create_task(monitor());started=time.monotonic()
    try:results=await asyncio.gather(*(request(i,w) for i,w in enumerate(windows)))
    finally:
        done.set();await monitor_task;await asyncio.gather(*(c.close() for c in clients))
    peaks={}
    for sample in samples:
        for line in sample.splitlines():
            k,v=[int(x.strip()) for x in line.split(',')];peaks[k]=max(peaks.get(k,0),v)
    report={'concurrent_requests':6,'per_service_concurrency':2,'frames_per_request':64,'max_tokens_per_request':160,'results':results,'all_ok':all(r['status']=='ok' for r in results),'elapsed_seconds':time.monotonic()-started,'sampled_peak_gpu_used_mib':peaks,'limitation':'Short output concurrency probe; long QA output concurrency not established.'}
    save_json(ROOT/'reports/impact_qa/video_v20_concurrency.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':asyncio.run(main())
