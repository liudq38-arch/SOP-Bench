import asyncio
import fcntl
import hashlib
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from impact_qa.api import Pool
from impact_qa.atr_qa import FOLDER, KINDS, ROOT, validate_generation, validate_reviews
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.reliable_pool import ReliablePool


def templates(hand):
    return {'actual_action':f'What did I do with my {hand} hand during the highlighted interval?', 'actual_tool':f'Which tool or tools did I handle with my {hand} hand during the highlighted interval?', 'tool_error':f'Did I use an inappropriate tool with my {hand} hand during the highlighted interval?', 'anomaly_type':f'Which types of error occurred in my {hand}-hand operation during the highlighted interval?', 'observed_correction':f'What change in tool use or manipulation is visible for my {hand} hand after the highlighted interval?', 'expected_tool':'Which tool should I have used instead during the highlighted interval?', 'timely_correction':'Did I correct the error in time?'}


async def main():
    cases=read_jsonl(FOLDER/'cases.jsonl')
    prompts={s:(ROOT/f'prompts/impact_qa/v19/{s}.txt').read_text() for s in ['generate','blind','audit']}
    pool=ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000,8001,8002]],4),FOLDER/'request_audit')
    sources=['impact_qa/atr_qa.py','scripts/prepare_atr_v19.py','scripts/run_atr_v19.py','impact_qa/api.py','impact_qa/reliable_pool.py']+[f'prompts/impact_qa/v19/{s}.txt' for s in prompts]
    frozen={'sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},'cases_hash':fingerprint(cases),'model_revision':pool.model_revision,'per_service_concurrency':4,'semantic_retries':0}
    if (FOLDER/'frozen.json').exists() and read_json(FOLDER/'frozen.json')!=frozen:raise ValueError('atr_runner:frozen_changed')
    save_json(FOLDER/'frozen.json',frozen)
    for c in cases:
        for im in c['images']:
            if hashlib.sha256(Path(im['path']).read_bytes()).hexdigest()!=im['sha256']:raise ValueError('atr_runner:media_hash')
    gate=asyncio.Semaphore(12);started=time.monotonic()
    async def process(c):
        async with gate:
            path=FOLDER/'runs'/(c['case_id']+'.json')
            if path.exists():
                r=read_json(path)
                if r['status']!='running':return r
            else:r={'case_id':c['case_id'],'pair_id':c['pair_id'],'view':c['view'],'status':'running','stages':{},'cache_keys':{}}
            public={'target_hand':c['shared_gt']['target_hand'],'view':c['view'],'target_interval_original_s':c['interval_s'],'images':c['image_manifest'],'followup_limit_s':20}
            questions=templates(c['shared_gt']['target_hand'])
            shared={**public,'shared_gt':c['shared_gt'],'question_templates':questions,'correct_option_positions':{k:int(fingerprint([c['pair_id'],k])[:8],16)%3 for k in KINDS}}
            async def call(stage,payload,tokens,validator):
                if stage not in r['stages']:
                    response=await pool.call('atr_v19_'+stage,prompts[stage],payload,c['images'],max_tokens=tokens)
                    r['cache_keys'][stage]=response['cache_key'];save_json(path,r)
                    r['stages'][stage]=validator(response['result']);save_json(path,r)
                return r['stages'][stage]
            try:
                g=await call('generate',shared,4200,lambda x:validate_generation(x,c))
                active=[q for q in g['items'] if q['answerable']]
                for q in active:
                    if q['question']!=questions[q['kind']] or q['correct_option']!=shared['correct_option_positions'][q['kind']]:raise ValueError('atr_generate:question_or_option_protocol')
                if active:
                    b=await call('blind',{**public,'questions':[{'kind':q['kind'],'question':q['question']} for q in active]},2200,lambda x:validate_reviews(x,[q['kind'] for q in active],c))
                    a=await call('audit',{**shared,'proposed_items':active,'blind_answers':b},3000,lambda x:validate_reviews(x,[q['kind'] for q in active],c,True))
                    blind={q['kind']:q for q in b['items']};audit={q['kind']:q for q in a['items']}
                    r['decisions']=[]
                    for q in active:
                        v=audit[q['kind']];u=blind[q['kind']]
                        passed=q['grade']==3 and u['grade']==3 and v['grade']==3 and all(v[k] for k in ['source_supported','visual_supported','blind_agrees','options_unique','scope_correct'])
                        r['decisions'].append({'kind':q['kind'],'status':'model_screened_unvalidated' if passed else 'needs_human_review','generation_grade':q['grade'],'blind_grade':u['grade'],'audit':v})
                r['status']='complete'
            except Exception as exc:r['status']='error';r['error']=f'{type(exc).__name__}:{exc}'
            save_json(path,r);print({k:r[k] for k in ['case_id','view','status']},flush=True);return r
    try:results=await asyncio.gather(*(process(c) for c in cases))
    finally:await pool.close()
    save_jsonl(FOLDER/'results.jsonl',results)
    summary={'view_cases':len(cases),'counts':dict(Counter(r['status'] for r in results)),'elapsed_seconds':time.monotonic()-started,'same_model_roles':True,'formal_release':False}
    if not (FOLDER/'initial_summary.json').exists():save_json(FOLDER/'initial_summary.json',summary)
    print(summary,flush=True)


if __name__=='__main__':
    FOLDER.mkdir(parents=True,exist_ok=True)
    with (FOLDER.parent/'quality_v16_runner.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        asyncio.run(main())
