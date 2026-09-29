import os
from pathlib import Path
import subprocess

import gradio as gr

from impact_qa.common import FFMPEG, ROOT, read_json, read_jsonl


NATIVE_FOLDER=ROOT/os.environ.get('IMPACT_MCQ_NATIVE_REVIEW','outputs/impact_qa/mcq_grouped_v2/review_export')


def rows():
    path=NATIVE_FOLDER/'questions.jsonl'
    return read_jsonl(path) if path.exists() else []


def choices():
    return [(f"{q['family_id']} | {q['view']} | {q['scope']['hand']} | {q['scope']['local_interval_s'][1]:.2f}s | {','.join(q['correct_option_ids'])} | {q['status']}",q['question_id']) for q in rows()]


def original_media(q):
    cases=read_jsonl(NATIVE_FOLDER/'cases.jsonl')
    c=next(c for c in cases if c['case_id']==q['question_id'])
    target=NATIVE_FOLDER/'review_media'/(q['question_id']+'.mp4')
    if target.exists() and target.stat().st_size:
        return str(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix('.tmp.mp4')
    a,b=q['scope']['source_interval_s']
    subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-nostdin','-y','-ss',f'{a:.8f}','-i',c['clip']['source_video'],'-t',f'{b-a:.8f}','-an','-vf','scale=960:-2','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)],check=True,timeout=120,capture_output=True)
    tmp.replace(target)
    return str(target)


def render(case_id):
    q=next((q for q in rows() if q['question_id']==case_id),None)
    if not q:
        return None,None,'本轮尚无结果。'
    a,b=q['scope']['source_interval_s']
    review=q['visual_review']
    blocks=[f"**视角：{q['view']}｜目标：{q['scope']['hand']} hand｜原片 {a:.3f}–{b:.3f}s**",'题目只问指定手在这段视频中的操作。不同视角采用各自原生 GT，不能默认答案相同。',f"**Q:** {q['question']}",f"**GT 答案：** {q['answer']}",'**固定选项及定义**\n\n'+'\n'.join(f"- **{o['id']}. {o['name']}**：{o['definition']}" for o in q['options']),f"**模型事实描述：** {review['factual_description']}"]
    for r in review['anomaly_evidence']:
        blocks.append(f"**{r['option_id']} 原因证据状态：`{r['evidence_status']}`**\n\n{r['reason']}\n\n证据帧：{', '.join(r['evidence_frame_ids']) or '无'}")
    if q['correct_option_ids']==['A']:
        blocks.append('Correct 指这个视角、这只手、这个时间段的 normal 标注；不推断整段装配成功，也不涵盖另一只手。')
    audit_path=NATIVE_FOLDER/'codex_visual_audit.json'
    if audit_path.exists():
        audit=read_json(audit_path)
        item=next((r for r in audit['cases'] if r['case_id']==case_id),None)
        if item:
            blocks.append(f"**Codex 复查：`{item['verdict']}`**\n\n{item['note']}")
    blocks.append(f"自动检查：`{q['status']}`；原因：{', '.join(q['automatic_gate']['issues']) or '机械检查通过，仍须独立核验'}。真人审核未完成；正式发布关闭。")
    if q['diagnostic_only']:
        blocks.append('此样例不足 5 秒，仅用于比较视角与排查，不进入本轮正式候选。')
    return original_media(q),q['video_path'],'\n\n'.join(blocks)


def refresh(case_id):
    options=choices()
    if case_id not in [x[1] for x in options]:
        case_id=options[0][1] if options else None
    original,sampled,body=render(case_id)
    return gr.update(choices=options,value=case_id),original,sampled,body


def build_native_tab():
    gr.Markdown('同一操作的 front / top / ego 对照。GT 答案、可见事实和异常原因分别展示；`observed_only` 表示看到了操作，但尚不能确认为什么错误。')
    summary_path=NATIVE_FOLDER/'summary.json'
    if summary_path.exists():
        summary=read_json(summary_path)
        if 'gt_facts_candidates' in summary:
            gr.Markdown(f"本轮 {summary['unique_view_cases']} 个视角样例：{summary['gt_facts_candidates']} 个 GT＋动作事实候选（异常 {summary['candidate_anomaly']}，Correct {summary['candidate_correct']}），{summary['held']} 个 hold；完整异常原因确认 {summary['all_types_reason_verified']}。以下仍展示全部结果与复查备注，供人工校验。")
    case=gr.Dropdown(choices(),label='MCQ 测试片段')
    reload=gr.Button('刷新 MCQ 测试结果')
    original=gr.Video(label='对应原片片段（原始帧率）',interactive=False)
    with gr.Accordion('模型实际输入视频',open=False):
        sampled=gr.Video(label='4fps 采样，包含源帧编号',interactive=False)
    qa=gr.Markdown()
    reload.click(refresh,[case],[case,original,sampled,qa],api_name='refresh_native_mcq')
    case.change(render,[case],[original,sampled,qa],api_name='load_native_mcq')
    return case,original,sampled,qa
