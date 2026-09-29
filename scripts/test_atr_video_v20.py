import asyncio
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from impact_qa.common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.video_input import CONFIG, FOLDER, VideoClient


PROMPT='''Inspect the supplied video, which is sampled by the server. Use video-local seconds, not source frame numbers. The target interval is explicitly given; later footage is follow-up. Return JSON {"observed_action":"...","actual_tool":"...","tool_identity_grade":0,"tool_error_visually_established":false,"observed_followup":"...","qa":[{"kind":"actual_tool","question":"...","answer":"...","options":["...","...","..."],"correct_option":0,"evidence_local_seconds":[0.0],"visual_grade":0,"source_basis":"visual or annotation or both"}],"limitations":["..."]}. Grades 0-3 measure direct visibility, not probability. Make at most 3 first-person QA pairs: target action/tool, whether a tool error is annotated if GT is supplied, or a directly visible subsequent change. Exactly one MCQ option must match each answer. Cite visible local seconds within this video. If GT is absent, do not assume a tool was wrong. GT labels establish annotated error categories but not the correct replacement tool, exact mechanism or deadline. Never infer screwdriver tip from handle color. Never equate later normal/recovery or a new tool with successful or timely correction. No expected-tool or timeliness answer without an explicit normative source. If the target is outside this window, do not describe it from future/past GT as visible here. Abstain where evidence is insufficient. Do not output chain-of-thought.'''


async def main():
    windows=read_jsonl(FOLDER/'windows.jsonl');cases={c['case_id']:c for c in read_jsonl(OUT/'atr_v19/cases.jsonl')}
    pairs=['atr_b5048432118ffc77','atr_403f880f747b22eb','atr_17fd15858f5679ef']
    chosen=[]
    for pair in pairs:
        for view in ['ego','front']:
            for profile in ['target','context']:
                selected=next(w for w in windows if w['pair_id']==pair and w['view']==view and w['profile']==profile)
                chosen.append(selected)
    files=['configs/impact_qa/video_v20.json','impact_qa/video_input.py','scripts/test_atr_video_v20.py']
    frozen={'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},'selected_windows':fingerprint(chosen),'prompt':PROMPT}
    if (FOLDER/'probe_frozen.json').exists() and read_json(FOLDER/'probe_frozen.json')!=frozen:raise ValueError('video_probe:changed_frozen')
    save_json(FOLDER/'probe_frozen.json',frozen)
    clients=[VideoClient(url) for url in CONFIG['base_urls']];limits=[asyncio.Semaphore(1) for c in clients]
    started=time.monotonic()
    async def process(index,w,gt):
        stage='gt_generate' if gt else 'visual_only'
        path=FOLDER/'probe_runs'/(w['window_id']+'_'+stage+'.json')
        if path.exists():return read_json(path)
        public={'target_hand':cases[w['case_id']]['shared_gt']['target_hand'],'profile':w['profile'],'view':w['view'],'video_local_duration_s':w['source_end_s']-w['source_start_s'],'target_local_interval_s':w['target_local_interval_s'],'decoded_frames':w['decoded_frames'],'sampled_local_times_s':w['sampled_local_times_s'],'annotation_gt':cases[w['case_id']]['shared_gt'] if gt else None}
        try:
            async with limits[index%3]:response=await clients[index%3].call(w,PROMPT,public)
            result=response['result']
            if not isinstance(result.get('qa'),list):raise ValueError('video_probe:qa_schema')
            for q in result['qa']:
                if type(q.get('correct_option')) is not int or q['correct_option'] not in range(3) or len(q.get('options',[]))!=3 or len(set(q['options']))!=3:raise ValueError('video_probe:options')
                if not isinstance(q.get('evidence_local_seconds'),list) or any(type(t) not in [int,float] or not 0<=t<=public['video_local_duration_s']+.05 for t in q['evidence_local_seconds']):raise ValueError('video_probe:time_range')
            r={'window_id':w['window_id'],'case_id':w['case_id'],'pair_id':w['pair_id'],'view':w['view'],'profile':w['profile'],'stage':stage,'status':'ok','cache_key':response['cache_key'],'usage':response['usage'],'seconds':response['seconds'],'result':result,'not_independently_validated':True}
        except Exception as exc:r={'window_id':w['window_id'],'stage':stage,'status':'error','error':str(exc)}
        save_json(path,r);print({k:r[k] for k in ['window_id','stage','status']},flush=True);return r
    try:
        rows=await asyncio.gather(*(process(i,w,True) for i,w in enumerate(chosen)),*(process(i,w,False) for i,w in enumerate(chosen) if w['profile']=='target'))
    finally:await asyncio.gather(*(c.close() for c in clients))
    save_jsonl(FOLDER/'probe_results.jsonl',rows)
    summary={'requests':len(rows),'ok':sum(r['status']=='ok' for r in rows),'errors':[r for r in rows if r['status']=='error'],'max_prompt_tokens':max((r.get('usage',{}).get('prompt_tokens',0) for r in rows),default=0),'elapsed_seconds':time.monotonic()-started,'per_service_concurrency':1,'same_model_roles':True,'formal_release':False}
    if not (FOLDER/'initial_probe_summary.json').exists():save_json(FOLDER/'initial_probe_summary.json',summary)
    print(summary,flush=True)


if __name__=='__main__':asyncio.run(main())
