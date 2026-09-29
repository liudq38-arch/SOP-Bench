from datetime import datetime, timezone
import fcntl
from pathlib import Path
import subprocess

import gradio as gr

from impact_qa.common import FFMPEG, ROOT, read_json, read_jsonl, save_json
from impact_qa.front_mcq_collaboration import consensus, review_index
from impact_qa.front_mcq_timeline import timeline_html
from impact_qa.front_mcq_guidance import guidance_html


FOLDER=ROOT/'outputs/impact_qa/front_mcq_expansion_v1'
GROUPS=read_jsonl(FOLDER/'groups.jsonl') if (FOLDER/'groups.jsonl').exists() else []
BY_ID={g['group_id']:g for g in GROUPS}
OPTIONS=read_json(FOLDER/'options.json') if (FOLDER/'options.json').exists() else []
NAMES={o['id']:o['name'] for o in OPTIONS}
LABELS={o['id']:o['id']+'. '+o['name'] for o in OPTIONS}


def questions():
    return read_jsonl(FOLDER/'questions.jsonl') if (FOLDER/'questions.jsonl').exists() else []


def status():
    if not (FOLDER/'progress.json').exists():return '候选准备中。'
    p=read_json(FOLDER/'progress.json')
    from impact_qa.front_mcq_collaboration import consensus,ledger,revision
    entries=ledger(FOLDER)
    reviewed=conflicts=0
    if entries:
        for q in questions():
            active=[r for r in entries.get(q['question_id'],[]) if r['revision']==revision(q)]
            reviewed+=bool(active)
            conflicts+=consensus(active)=='意见不一致，待复核'
    return f"本批全部为异常类型MCQ，共 {p['questions']} 道 · 未审核 {p['questions']-reviewed} 道 · 已审核 {reviewed} 道 · 分歧待复核 {conflicts} 道。开放式QA在独立历史标签页，不包含在此数量中。"


def filtered_questions(category='全部',duration='全部',state='已有视觉解释',review_mode='未审核',rows=None,reviews=None):
    rows=questions() if rows is None else rows
    reviews=review_index(FOLDER,rows) if reviews is None else reviews
    result=[]
    for q in rows:
        decisions=reviews.get(q['question_id'],[])
        if review_mode=='未审核' and decisions:continue
        if review_mode=='已审核' and not decisions:continue
        if review_mode=='分歧待复核' and consensus(decisions)!='意见不一致，待复核':continue
        seconds=q['scope']['target_duration_s']
        if category!='全部' and category not in [NAMES[i] for i in q['candidate_option_ids']+q['model_supported_option_ids']]:continue
        if duration=='目标≥20秒' and seconds<20:continue
        if duration=='目标≥5秒' and seconds<5:continue
        if duration=='目标<5秒' and seconds>=5:continue
        if state=='已有视觉解释' and not q['visual_review']:continue
        if state=='模型支持至少一类' and not q['model_supported_option_ids']:continue
        if state=='原GT未标异常' and q['origin']=='GT_anomaly':continue
        result.append(q)
    return sorted(result,key=lambda q:bool(reviews.get(q['question_id']))) if review_mode=='全部' else result


def choices(category='全部',duration='全部',state='已有视觉解释',review_mode='未审核',rows=None):
    from collections import Counter
    eligible=filtered_questions(category,duration,state,review_mode) if rows is None else rows
    counts=Counter(q['group_id'] for q in eligible)
    result=[]
    for group in GROUPS:
        if group['group_id'] in counts:
            longest=max(e['duration_s'] for e in group['events'])
            result.append((f"{group['trial_id']} | 播放{group['duration_s']:.1f}s | 最长目标{longest:.1f}s | 当前范围{counts[group['group_id']]}题 / 共{len(group['events'])}题 | {group['group_id'][-6:]}",group['group_id']))
    return result


def review_media(group):
    target=FOLDER/'review_media'/(group['group_id']+'.mp4')
    if target.exists() and target.stat().st_size>0:return str(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.with_suffix('.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if target.exists() and target.stat().st_size>0:return str(target)
        tmp=target.with_suffix('.tmp.mp4')
        subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-nostdin','-y','-threads','2',
                        '-ss',str(group['start_frame']/group['fps']),'-i',group['source_video'],'-t',str(group['duration_s']),
                        '-an','-vf','scale=1280:-2','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21',
                        '-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)],capture_output=True,check=True,timeout=600)
        tmp.replace(target)
    return str(target)


def review_value(qid):
    path=FOLDER/'human_reviews'/(qid+'.json') if qid else None
    r=read_json(path) if path and path.exists() else {}
    return r.get('verdict','待审核'),[LABELS[k] for k in r.get('option_ids',[])],r.get('note','')


def render(gid):
    if gid not in BY_ID:return None,'暂无符合筛选的结果。',[],gr.update(choices=[],value=None),'待审核',[],''
    group=BY_ID[gid]
    qs=[q for q in questions() if q['group_id']==gid]
    a,b=group['start_frame']/group['fps'],group['end_frame_exclusive']/group['fps']
    blocks=[f"**{group['trial_id']} · front · 原片 {a:.2f}–{b:.2f}秒 · 上下文 {b-a:.1f}秒**",
            '每题只判断指定手和指定时间段。画面左侧不一定是操作者左手。多个异常采用多选；A不能与异常选项共选。',
            '**七个固定选项**\n\n'+'\n'.join(f"- {o['id']}. **{o['name']}**：{o['definition']}" for o in OPTIONS)]
    gallery=[];seen=set()
    resultpath=FOLDER/'results'/(gid+'.json')
    result=read_json(resultpath) if resultpath.exists() else {}
    media={f['frame_id']:f for f in result.get('media',{}).get('sampled_frames',[])}
    for n,q in enumerate(qs,1):
        src=q['scope']['source_interval_s'];loc=q['scope']['playback_interval_s']
        blocks.append(f"### {n}. {q['question_zh']}\n\n{q['question']}\n\n目标时长 **{src[1]-src[0]:.2f}秒**；原片 **{src[0]:.2f}–{src[1]:.2f}秒**。")
        gt=', '.join(LABELS[k] for k in q['GT_option_ids']) or '无异常类型标记（不自动等同Correct）'
        proposal=', '.join(LABELS[k] for k in q['candidate_option_ids'])
        supported=', '.join(LABELS[k] for k in q['model_supported_option_ids']) or '尚无受支持的异常结论'
        blocks.append(f"**原GT：** {gt}；phase={q['GT_phase']}\n\n**待核验候选：** {proposal}\n\n**模型支持：** {supported}。")
        if q['visual_review']:
            blocks.append('**可见过程：** '+q['visual_review']['facts'])
            blocks.append('**推进依据：** '+q['visual_review'].get('progress_evidence','未提供'))
            for c in q['visual_evidence']:
                times='、'.join(f"{f['playback_s']:.2f}s（源{f['source_s']:.2f}s）" for f in c['frames']) or '没有目标帧引用'
                blocks.append(f"- **{c['category']} · {c['verdict']}**：{c['reason']}\n  替代解释/局限：{c['alternative']}\n  证据：{times}")
                for fid in c['evidence_frame_ids']:
                    if fid in media and fid not in seen and len(gallery)<24:
                        seen.add(fid);gallery.append((media[fid]['path'],f"{fid} 播放{media[fid]['local_pts_s']:.2f}s / 原片{media[fid]['source_pts_s']:.2f}s"))
        else:blocks.append('视觉解释尚未完成。'+('生成错误：'+result.get('error','') if result.get('status')=='error' else ''))
        human=review_value(q['question_id'])
        blocks.append(f"**人工审核：** {human[0]}；{', '.join(human[1]) or '未定答案'}；{human[2]}")
    qchoices=[(f"第{i+1}题 · 播放{q['scope']['playback_interval_s'][0]:.2f}–{q['scope']['playback_interval_s'][1]:.2f}s",q['question_id']) for i,q in enumerate(qs)]
    qid=qchoices[0][1] if qchoices else None
    return review_media(group),'\n\n'.join(blocks),gallery,gr.update(choices=qchoices,value=qid),*review_value(qid)


def refresh(gid,category,duration,state):
    values=choices(category,duration,state)
    if gid not in [v for _,v in values]:gid=values[0][1] if values else None
    return gr.update(choices=values,value=gid),status(),*render(gid)


def navigate(gid,category,duration,state,offset):
    values=choices(category,duration,state);ids=[v for _,v in values]
    if not ids:return refresh(None,category,duration,state)
    index=ids.index(gid) if gid in ids else 0
    return refresh(ids[(index+offset)%len(ids)],category,duration,state)


def save_review(qid,verdict,answers,note):
    if not qid or qid not in {q['question_id'] for q in questions()}:raise gr.Error('请选择有效题目。')
    ids=[s.split('.')[0] for s in answers]
    if 'A' in ids and len(ids)>1:raise gr.Error('Correct不能与异常选项同时选择。')
    if verdict=='确认/修正答案' and not ids:raise gr.Error('确认答案时请选择至少一个选项。')
    r=dict(question_id=qid,verdict=verdict,option_ids=ids,note=note,updated_at=datetime.now(timezone.utc).isoformat(),reviewer='human_via_gradio')
    save_json(FOLDER/'human_reviews'/(qid+'.json'),r)
    import json
    with (FOLDER/'human_review_history.jsonl').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX);handle.write(json.dumps(r,ensure_ascii=False)+'\n')
    return '审核已保存；点击刷新可更新题目下方记录。'


def build_tab(app):
    from impact_qa.front_mcq_collaboration import claim,consensus,current_reviews,heartbeat,record,revision
    gr.HTML('<div class="review-intro"><b>IMPACT · MCQ协作审核</b><span>看视频 → 核对GT与证据 → 一键提交下一题</span></div>')
    summary=gr.Markdown(status())
    with gr.Row():
        reviewer=gr.Textbox(label='审核昵称',placeholder='每人使用不同昵称，例如 LDQ',scale=2)
        start=gr.Button('领取未审核题目',variant='primary',scale=1)
        reload=gr.Button('刷新结果',scale=1)
    review_mode=gr.Radio(['未审核','已审核','分歧待复核','全部'],value='未审核',label='审核队列（默认跳过任何人已审核的题目）')
    with gr.Accordion('筛选与选择视频',open=False):
        with gr.Row():
            category=gr.Dropdown(['全部']+[o['name'] for o in OPTIONS if o['id']!='A'],value='全部',label='候选类型')
            duration=gr.Dropdown(['全部','目标≥20秒','目标≥5秒','目标<5秒'],value='全部',label='目标时长')
            state=gr.Dropdown(['全部','已有视觉解释','模型支持至少一类','原GT未标异常'],value='已有视觉解释',label='结果范围')
        selected=gr.Dropdown(choices(),label='Clip：长短目标交错展示')
        apply=gr.Button('应用筛选')
    notification=gr.Markdown()
    with gr.Row(equal_height=False):
        with gr.Column(scale=6,min_width=440):
            timeline=gr.HTML('',elem_id='front-review-timeline')
            video=gr.Video(label='本clip · 原始帧率与真实时长',interactive=False,elem_id='front-review-video')
            with gr.Row():
                seek=gr.Button('从判断区间开始播放',variant='primary')
                context=gr.Button('从前3秒开始看')
            seek.click(fn=None,inputs=None,outputs=None,js="() => { window.impactMCQTimeline?.playTarget(); }",api_name=False)
            context.click(fn=None,inputs=None,outputs=None,js="() => { window.impactMCQTimeline?.showContext(); }",api_name=False)
            qid=gr.Dropdown(label='本clip的MCQ题目')
            guidance=gr.HTML('',elem_id='front-review-guidance')
            with gr.Accordion('查看证据原帧',open=False):gallery=gr.Gallery(columns=2,label='当前题目证据帧')
            with gr.Accordion('完整源视频',open=False):
                full_button=gr.Button('加载完整视频');full_video=gr.Video(interactive=False,label='按原片时间核查')
                full_button.click(lambda gid:BY_ID[gid]['source_video'] if gid in BY_ID else None,[selected],[full_video],api_name='front_mcq_full_video')
        with gr.Column(scale=5,min_width=400,elem_classes='review-card'):
            body=gr.Markdown()
            answers=gr.CheckboxGroup(list(LABELS.values()),label='确认的答案（可修改；多异常可多选）')
            with gr.Row():
                yes=gr.Button('通过 · 下一题',variant='primary',elem_id='front-review-pass')
                no=gr.Button('不通过 · 下一题',variant='stop')
            with gr.Row():
                unsure=gr.Button('证据不足 · 下一题')
                skip=gr.Button('跳过 / 领取下一题')
            note=gr.Textbox(label='备注（选填）',placeholder='问题描述、答案或证据哪里需要修改',lines=2)
            evidence=gr.Markdown(elem_classes='review-evidence')
            history=gr.Markdown()
    with gr.Accordion('本clip的MCQ（按上方审核队列过滤）',open=True):all_body=gr.Markdown()
    with gr.Accordion('七类选项的定义',open=False):
        gr.Markdown('\n\n'.join(f"**{o['id']}. {o['name']}** — {o['definition']}" for o in OPTIONS))
    version=gr.State('')
    outputs=[video,body,all_body,gallery,qid,answers,note,version,selected,history,notification,evidence,summary,review_mode,timeline,guidance]

    def available(cat,dur,st,mode='未审核'):
        return filtered_questions(cat,dur,st,mode)

    def display(question_id,name,message='',cat='全部',dur='全部',st='已有视觉解释',mode='未审核',empty=False):
        qs=questions();reviews_by_id=review_index(FOLDER,qs)
        eligible=filtered_questions(cat,dur,st,mode,rows=qs,reviews=reviews_by_id)
        group_choices=choices(rows=eligible)
        q=next((r for r in eligible if r['question_id']==question_id),None)
        if q is None and eligible and not empty:
            q=eligible[0];question_id=q['question_id']
            message+=' 已优先显示当前队列中的题目。'
        if not q:return None,'当前范围没有可领取的题目。','',[],gr.update(choices=[],value=None),[],'','',gr.update(choices=group_choices,value=None),'',message,'',status(),mode,'',''
        group=BY_ID[q['group_id']];same=[r for r in eligible if r['group_id']==q['group_id']]
        loc=q['scope']['playback_interval_s'];src=q['scope']['source_interval_s']
        gt=' · '.join(LABELS[k] for k in q['GT_option_ids']) or '未标异常（不等于已确认Correct）'
        proposed=' · '.join(LABELS[k] for k in q['candidate_option_ids'])
        supported=' · '.join(LABELS[k] for k in q['model_supported_option_ids']) or '暂无支持结论'
        text=[f"### 本题 · 播放 {loc[0]:.2f}–{loc[1]:.2f} 秒",q['question_zh'],
              f"**GT：** {gt}\n\n**候选答案：** {proposed}\n\n**模型支持：** {supported}",
              f"原片 {src[0]:.2f}–{src[1]:.2f}s · 目标 {src[1]-src[0]:.2f}s · 指操作者的{'左' if q['scope']['hand']=='left' else '右'}手"]
        audit_path=FOLDER/'codex_checks.json'
        if audit_path.exists():
            audited=next((r for r in read_json(audit_path)['items'] if r['question_id']==q['question_id']),None)
            if audited:text[3]+='\n\n**复查提醒：** '+audited['note']
        images=[];seen=set()
        result_path=FOLDER/'results'/(q['group_id']+'.json')
        result=read_json(result_path) if result_path.exists() else {}
        fmap={f['frame_id']:f for f in result.get('media',{}).get('sampled_frames',[])}
        if q['visual_review']:
            text.append('**视觉过程：** '+q['visual_review']['facts'])
            text.append('**推进依据：** '+q['visual_review'].get('progress_evidence','未提供'))
            translations={'supported':'支持','contradicted':'存在反证','insufficient':'证据不足'}
            for c in q['visual_evidence']:
                timestamps='、'.join(f"{f['playback_s']:.2f}s" for f in c['frames']) or '无'
                text.append(f"**{c['category']} · {translations[c['verdict']]}**\n\n{c['reason']}\n\n局限：{c['alternative']} · 证据播放时间：{timestamps}")
                for fid in c['evidence_frame_ids']:
                    if fid in fmap and fid not in seen:
                        seen.add(fid);images.append((fmap[fid]['path'],f"播放{fmap[fid]['local_pts_s']:.2f}s / 原片{fmap[fid]['source_pts_s']:.2f}s"))
        else:text.append('视觉依据生成中，请等待完成后审核。')
        reviews=reviews_by_id[q['question_id']]
        own=next((r for r in reviews if r['reviewer']==name.strip()),None)
        checked=[LABELS[k] for k in (own['option_ids'] if own else q['candidate_option_ids'])]
        hist='**协作审核：** '+consensus(reviews)
        if reviews:hist+='\n\n'+'\n\n'.join(f"{r['reviewer']} · {r['verdict']} · {','.join(r['option_ids'])} · {r['note']}" for r in reviews)
        listing=[]
        for i,row in enumerate(same,1):
            gl=' · '.join(LABELS[k] for k in row['GT_option_ids']) or '未标异常'
            visual=row['visual_review']['facts'] if row['visual_review'] else '视觉依据生成中'
            listing.append(f"**{i}. [{consensus(reviews_by_id[row['question_id']])}] {row['question_zh']}**\n\nGT：{gl}\n\n视觉依据：{visual}")
        options=[(f"[{consensus(reviews_by_id[row['question_id']])}] 第{i+1}题 · {row['scope']['playback_interval_s'][0]:.2f}–{row['scope']['playback_interval_s'][1]:.2f}s · {','.join(row['candidate_option_ids'])}",row['question_id']) for i,row in enumerate(same)]
        return review_media(group),'\n\n'.join(text[:5]),'\n\n---\n\n'.join(listing),images,gr.update(choices=options,value=question_id),checked,own['note'] if own else '',revision(q),gr.update(choices=group_choices,value=q['group_id']),hist,message,'\n\n'.join(text[5:]),status(),mode,timeline_html(q,group),guidance_html(q,group)

    def initial(name):
        return display(None,name)

    def next_question(name,cat,dur,st,mode):
        question_id,message=claim(FOLDER,available(cat,dur,st),name)
        return display(question_id,name,message,cat,dur,st,'未审核',empty=question_id is None)

    def choose_question(question_id,name,cat,dur,st,mode):
        message=''
        eligible=available(cat,dur,st,mode)
        if name.strip() and question_id in {q['question_id'] for q in eligible}:
            _,message=claim(FOLDER,eligible,name,preferred=question_id)
        return display(question_id,name,message,cat,dur,st,mode)

    def choose_group(gid,name,cat,dur,st,mode):
        qs=[q for q in available(cat,dur,st,mode) if q['group_id']==gid]
        return choose_question(qs[0]['question_id'] if qs else None,name,cat,dur,st,mode)

    def apply_filters(name,cat,dur,st,mode):
        return display(None,name,'',cat,dur,st,mode)

    def submit(question_id,rev,name,checked,comment,cat,dur,st,mode,verdict):
        q=next((q for q in questions() if q['question_id']==question_id),None)
        if q is None:raise gr.Error('请选择题目。')
        try:saved=record(FOLDER,q,rev,name,verdict,[v.split('.')[0] for v in checked],comment)
        except ValueError as exc:raise gr.Error(str(exc)) from exc
        next_id,message=claim(FOLDER,available(cat,dur,st),name)
        from datetime import timezone,timedelta
        saved_at=datetime.fromisoformat(saved['updated_at']).astimezone(timezone(timedelta(hours=8))).strftime('%H:%M:%S')
        verdict_name={'pass':'通过','fail':'不通过','unsure':'证据不足'}[verdict]
        receipt=f"已保存 · {saved_at} · {name.strip()} · {question_id} · {verdict_name} · 答案 {','.join(saved['option_ids']) or '未定'}。本题已移出未审核队列。"
        return display(next_id,name,receipt+message,cat,dur,st,'未审核',empty=next_id is None)

    app.load(fn=None,inputs=None,outputs=reviewer,js="() => { try { return localStorage.getItem('impact_mcq_reviewer_v1') || ''; } catch { return ''; } }").then(initial,[reviewer],outputs,api_name='initialize_front_mcq')
    reviewer.input(fn=None,inputs=[reviewer],outputs=None,js="name => { try { localStorage.setItem('impact_mcq_reviewer_v1', name); } catch {} }")
    inputs=[reviewer,category,duration,state,review_mode]
    start.click(next_question,inputs,outputs,api_name='claim_front_mcq')
    skip.click(next_question,inputs,outputs,api_name='skip_front_mcq')
    reload.click(lambda question_id,name,cat,dur,st,mode:display(question_id,name,'',cat,dur,st,mode),[qid]+inputs,outputs,api_name='refresh_front_mcq')
    apply.click(apply_filters,inputs,outputs,api_name='filter_front_mcq')
    review_mode.input(apply_filters,inputs,outputs,api_name='set_front_mcq_review_mode')
    selected.input(choose_group,[selected]+inputs,outputs,api_name='load_front_mcq_group')
    qid.input(choose_question,[qid]+inputs,outputs,api_name='load_front_mcq_question')
    submission=[qid,version,reviewer,answers,note,category,duration,state,review_mode]
    yes.click(lambda *args:submit(*args,'pass'),submission,outputs,api_name='pass_front_mcq')
    no.click(lambda *args:submit(*args,'fail'),submission,outputs,api_name='fail_front_mcq')
    unsure.click(lambda *args:submit(*args,'unsure'),submission,outputs,api_name='unsure_front_mcq')
    gr.Timer(20).tick(status,outputs=summary,api_name='front_mcq_progress')
    gr.Timer(60).tick(lambda question_id,name:heartbeat(FOLDER,question_id,name),[qid,reviewer],api_name=False)
