import argparse
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time

import httpx
from transformers import AutoTokenizer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_sop_filter import filter_question, gt_types, summarize
from impact_qa.mcq_sop_reference import build_reference
from impact_qa.mcq_sop_payload import assert_blind, build_case, image_contents
from impact_qa.mcq_sop_validation import validate_result


CONFIG=ROOT/'configs/impact_qa/mcq_sop_visual_v1.json'


def prepare(config,folder):
    questions=read_jsonl(ROOT/config['input_questions']);groups={r['group_id']:r for r in read_jsonl(ROOT/config['input_groups'])}
    source_hash={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/config['input_questions'],ROOT/config['input_groups']]}
    frozen=folder/'source_frozen.json'
    if frozen.exists() and read_json(frozen)!=source_hash:raise ValueError('mcq_sop_visual:original_inputs_changed')
    save_json(frozen,source_hash)
    rows=[]
    for q in questions:
        if q['group_id'] not in groups:raise ValueError('mcq_sop_visual:missing_group:'+q['group_id'])
        rows.append(dict(q,filter=filter_question(q,groups[q['group_id']],config['threshold_s'])))
    kept=[q for q in rows if q['filter']['status']=='kept'];discarded=[q for q in rows if q['filter']['status']=='discarded']
    save_jsonl(folder/'kept_questions.jsonl',kept);save_jsonl(folder/'discarded_questions.jsonl',discarded)
    stats=summarize(rows);save_json(folder/'filter_statistics.json',stats)
    save_jsonl(folder/'first10_kept.jsonl',kept[:10]);save_jsonl(folder/'first10_discarded.jsonl',discarded[:10])
    reference=build_reference();save_json(folder/'sop_reference.json',reference)
    jobs=[dict(question=q,group=groups[q['group_id']],segment=s) for q in kept for s in q['filter']['target_segments']]
    print(json.dumps({'stage':'filter','total':len(rows),'kept':len(kept),'discarded':len(discarded),'jobs':len(jobs),'reasons':stats['discard_reasons']},ensure_ascii=False),flush=True)
    return jobs,reference,stats


def report(folder,jobs,stats):
    results=[];pending=[];normal_gt=[];origin_counts={};model_counts={}
    for job in jobs:
        q=job['question'];s=job['segment'];key=fingerprint(s['segment_id'])[:24];path=folder/'results'/f'{key}.json'
        if not path.exists():pending.append(s['segment_id']);continue
        result=read_json(path);results.append(result)
        origin=q['origin'];origin_counts.setdefault(origin,Counter())[result.get('verdict',result['status'])]+=1
        model=job['group']['model'];model_counts.setdefault(model,Counter())[result.get('verdict',result['status'])]+=1
        if result.get('verdict')=='normal' and gt_types(q):
            normal_gt.append(dict(question_id=q['question_id'],trial_id=q['trial_id'],segment_id=s['segment_id'],GT_types=gt_types(q),target=s,qwen=result))
    save_jsonl(folder/'verification_results.jsonl',results)
    save_jsonl(folder/'normal_but_gt_anomaly.jsonl',normal_gt)
    verdicts=Counter(r['verdict'] for r in results if r['status']=='ok')
    kinds=Counter(r['anomaly_type'] for r in results if r['status']=='ok')
    failures=Counter(r['status'] for r in results if r['status']!='ok')
    successful=sum(verdicts.values());summary=dict(expected_segments=len(jobs),finished=len(results),pending=len(pending),successful=successful,verdict_counts=dict(verdicts),anomaly_type_counts=dict(kinds),failures=dict(failures),insufficient_evidence_fraction=verdicts['insufficient_evidence']/successful if successful else None,normal_but_gt_anomaly=len(normal_gt),by_origin={k:dict(v) for k,v in origin_counts.items()},by_model={k:dict(v) for k,v in model_counts.items()},filter=stats,formal_release=False)
    save_json(folder/'summary.json',summary)
    lines=['# MCQ时长过滤与SOP盲视觉核验','',f"输入 {stats['total']}；保留 {stats['kept']}；丢弃 {stats['discarded']}；丢弃原因 {stats['discard_reasons']}。",f'已返回 {len(results)}/{len(jobs)}，有效JSON与证据合同通过 {successful}，待处理 {len(pending)}。',f'Verdict: {dict(verdicts)}',f'模型异常类型: {dict(kinds)}',f'执行失败: {dict(failures)}',f'GT异常但模型normal: {len(normal_gt)}，详见normal_but_gt_anomaly.jsonl。','','## 过滤后的类型构成','', '| GT类型 | 总数 | 保留 | 保留率 |','|---|---:|---:|---:|']
    for kind,row in stats['by_gt_type'].items():lines.append(f"| {kind} | {row['total']} | {row['kept']} | {row['retention_rate']:.2%} |")
    lines+=['',f"低保留率提示：{stats['low_retention_flags']}",stats['significance_note'],'','## 判定边界','','GT异常和规则候选分开统计；所有原短标注保留计数。模型未接收原题、GT答案、异常类型、相位、旧审核或规则命中。输入包含有证据边界的SOP、显式换序组/连接前置、候选步骤部件工具、clip完整双手TAS-B、去标签的TAS-S提示和逐帧时间。PSR的51条状态操作不能独立构成偏序图，未伪造为官方依赖。','operational是本次输出类别，对应官方handling作分析；redundant是额外核验维度，未写回数据集。单一主因不等于官方多标签全量预测。confidence是模型自评，不是校准准确率。','normal仅表示给定目标的可见抽帧未见异常且支持合法动作，不证明整段连续视频/未采样时刻都正常。没有状态推进的判断必须有连续尝试证据，不能仅凭长间隔图像相似。','结果是待人工复核的模型意见；没有修改原MCQ、标注、审核记录或数据集。']
    (folder/'report.md').write_text('\n'.join(lines)+'\n')
    return summary


async def run(config,folder,jobs,reference,args):
    system=(ROOT/'prompts/impact_qa/mcq_sop_visual_v1_system.txt').read_text()
    template=(ROOT/'prompts/impact_qa/mcq_sop_visual_v1_user.txt').read_text()
    schema=read_json(ROOT/'prompts/impact_qa/mcq_sop_visual_v1_schema.json')
    tokenizer=AutoTokenizer.from_pretrained(config['model_path'],local_files_only=True)
    model_config=read_json(Path(config['model_path'])/'config.json')
    version=fingerprint([config,reference,system,template,schema,{p.name:p.read_text() for p in [Path(__file__),ROOT/'impact_qa/mcq_sop_payload.py',ROOT/'impact_qa/mcq_sop_validation.py',ROOT/'impact_qa/mcq_sop_filter.py',ROOT/'impact_qa/mcq_sop_reference.py']}])
    lockfile=folder/'generation_frozen.json'
    if lockfile.exists() and read_json(lockfile)['fingerprint']!=version:raise ValueError('mcq_sop_visual:code_or_prompt_changed_requires_new_output_root')
    save_json(lockfile,dict(fingerprint=version,model_architectures=model_config['architectures'],model_type=model_config['model_type'],service_name=config['model']))
    clients=[httpx.AsyncClient(base_url=u,timeout=config['request_timeout_s'],trust_env=False) for u in config['base_urls']]
    for client in clients:
        r=await client.get('/models');r.raise_for_status()
        if config['model'] not in [x['id'] for x in r.json()['data']]:raise ValueError('mcq_sop_visual:model_service_mismatch')
    pool=ThreadPoolExecutor(max_workers=config['decode_workers']);decode_slots=asyncio.Semaphore(config['decode_workers']);request_slots=asyncio.Queue()
    for i in range(len(clients)):
        for _ in range(args.concurrency or config['per_service_concurrency']):request_slots.put_nowait(i)
    work=asyncio.Queue()
    selected=jobs
    if args.pilot:
        chosen=[]
        for model in ['A','B']:
            for workflow in ['assemble','disassemble']:
                subset=[j for j in jobs if j['group']['model']==model and j['group']['workflow']==workflow]
                for key in [lambda j:j['segment']['duration_s'],lambda j:-j['segment']['duration_s']]:
                    if subset:
                        pick=min(subset,key=key)
                        if pick not in chosen:chosen.append(pick)
        selected=chosen
    if args.limit:selected=selected[:args.limit]
    for job in selected:
        key=fingerprint(job['segment']['segment_id'])[:24];path=folder/'results'/f'{key}.json'
        if path.exists():
            old=read_json(path)
            if old.get('run_fingerprint')!=version:raise ValueError('mcq_sop_visual:cached_result_version_mismatch')
            if old['status']=='ok' or not args.retry_failures:continue
        work.put_nowait(job)
    save_json(folder/'run_status.json',dict(queued=work.qsize(),selected=len(selected),pid=__import__('os').getpid(),mode='pilot' if args.pilot else 'full'))
    completed=0;started=time.monotonic()
    async def worker():
        nonlocal completed
        while not work.empty():
            try:job=work.get_nowait()
            except asyncio.QueueEmpty:return
            q,g,s=job['question'],job['group'],job['segment'];key=fingerprint(s['segment_id'])[:24]
            result=dict(question_id=q['question_id'],trial_id=q['trial_id'],segment_id=s['segment_id'],status='input_failed',run_fingerprint=version)
            errors=[];slot=None;t0=time.monotonic()
            try:
                sop=reference['procedures'][g['model']+'_'+g['workflow']]
                async with decode_slots:
                    record=await asyncio.get_running_loop().run_in_executor(pool,build_case,q,g,s,sop,folder,config)
                local_schema=copy.deepcopy(schema);local_schema['properties']['matched_sop_step']['enum']=[x['id'] for x in sop['steps']]+['unknown']
                target=record['case']['target']
                action_schema=local_schema['properties']['evidence_actions']['items']['properties']
                for field in ['t_start','t_end']:
                    action_schema[field].update(minimum=target['start_s'],maximum=target['end_s'])
                local_schema['properties']['evidence_frames']['items']['enum']=[f['frame_index'] for f in record['frames'] if f['role']=='target']
                text=template.replace('{SOP_JSON}',json.dumps(dict(sop=sop),ensure_ascii=False,separators=(',',':'))).replace('{CASE_JSON}',json.dumps(record['case'],ensure_ascii=False,separators=(',',':'))).replace('{JSON_SCHEMA}',json.dumps(local_schema,separators=(',',':')))
                assert_blind(record['case']);assert_blind(sop)
                estimated=len(tokenizer.encode(system+text))+len(record['frames'])*640+config['maximum_generation_tokens']+768
                if estimated>config['max_model_len']:raise ValueError('context_budget_exceeded:'+str(estimated))
                content=[dict(type='text',text=text)]+image_contents(record)
                content.append(dict(type='text',text=f"本次目标是完整clip时间轴的 [{target['start_s']}, {target['end_s']}) 秒，目标手 {target['hand']}。证据时间不得重新归零成[0, duration]，t_start和t_end都须位于上述范围且t_start<t_end。可用目标图帧号：{local_schema['properties']['evidence_frames']['items']['enum']}。"))
                wire_schema=copy.deepcopy(local_schema)
                wire_schema['properties']['evidence_frames'].pop('uniqueItems',None)
                request=dict(model=config['model'],messages=[dict(role='system',content=system),dict(role='user',content=content)],temperature=0,top_p=1,seed=config['seed'],max_tokens=config['maximum_generation_tokens'],chat_template_kwargs={'enable_thinking':False},response_format={'type':'json_schema','json_schema':{'name':'segment_visual_verification','schema':wire_schema,'strict':True}},mm_processor_kwargs={'size':{'shortest_edge':65536,'longest_edge':config['max_image_pixels']}})
                log_request={k:v for k,v in request.items() if k!='messages'};log_request.update(system=system,user_text=text,final_time_reminder=content[-1]['text'],frame_inputs=record['frames'],estimated_total_tokens=estimated,labels_sent=False)
                save_json(folder/'requests'/f'{key}.json',log_request)
                slot=await request_slots.get()
                for attempt in range(config['attempts']):
                    try:
                        response=await clients[slot].post('/chat/completions',json=request);response.raise_for_status();body=response.json()
                        save_json(folder/'raw_responses'/f'{key}.{attempt}.json',body)
                        if body['choices'][0]['finish_reason']!='stop':raise ValueError('incomplete_generation:'+body['choices'][0]['finish_reason'])
                        value=json.loads(body['choices'][0]['message']['content']);validate_result(value,local_schema,record)
                        result.update(value,status='ok',attempts=attempt+1,usage=body.get('usage'),endpoint=config['base_urls'][slot],media_manifest=str(Path(record['frames'][0]['path']).parent/'manifest.json'))
                        break
                    except (httpx.HTTPError,ValueError,KeyError,TypeError,__import__('jsonschema').ValidationError) as exc:
                        message=str(exc)
                        if isinstance(exc,httpx.HTTPStatusError):message+=' '+exc.response.text[:1500]
                        errors.append(dict(attempt=attempt+1,error=type(exc).__name__+':'+message[:2000]))
                        result['status']='api_failed' if isinstance(exc,httpx.HTTPError) else 'parse_failed'
                        if attempt+1<config['attempts']:
                            feedback=f"上次输出未通过合同，仅修正格式/时间/一致性错误，不因格式错误改变视觉结论。证据时间是完整clip的[{target['start_s']}, {target['end_s']})秒，不能归零。错误："+message[:500]
                            request['messages']=[dict(role='system',content=system),dict(role='user',content=content+[dict(type='text',text=feedback)])]
                            await asyncio.sleep(min(2**attempt,4))
                result.update(validation_errors=errors,sampling=record['case']['sampling'])
            except Exception as exc:
                result.update(status='input_failed',error=type(exc).__name__+':'+str(exc))
            finally:
                if slot is not None:request_slots.put_nowait(slot)
                result['elapsed_s']=time.monotonic()-t0
                save_json(folder/'results'/f'{key}.json',result)
                completed+=1;work.task_done()
                print(json.dumps({k:result.get(k) for k in ['question_id','status','verdict','anomaly_type','confidence','elapsed_s','error']},ensure_ascii=False),flush=True)
                if completed%20==0:save_json(folder/'run_status.json',dict(completed_this_run=completed,remaining_this_run=work.qsize(),elapsed_s=time.monotonic()-started,pid=__import__('os').getpid()))
    try:
        await asyncio.gather(*(worker() for _ in range(min(max(1,work.qsize()),request_slots.qsize()+config['decode_workers']))))
    finally:
        await asyncio.gather(*(c.aclose() for c in clients));pool.shutdown(wait=True)
    save_json(folder/'run_status.json',dict(completed_this_run=completed,remaining_this_run=0,elapsed_s=time.monotonic()-started,finished=True))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--report-only',action='store_true');parser.add_argument('--pilot',action='store_true');parser.add_argument('--limit',type=int);parser.add_argument('--concurrency',type=int);parser.add_argument('--retry-failures',action='store_true');args=parser.parse_args()
    config=read_json(CONFIG);folder=ROOT/config['output_root'];folder.mkdir(parents=True,exist_ok=True)
    with (folder/'runner.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        jobs,reference,stats=prepare(config,folder)
        if not args.prepare_only and not args.report_only:asyncio.run(run(config,folder,jobs,reference,args))
        summary=report(folder,jobs,stats)
        print(json.dumps({k:summary[k] for k in ['expected_segments','finished','pending','verdict_counts','failures']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
