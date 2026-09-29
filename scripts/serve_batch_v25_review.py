import os
import sys
import time
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl
from impact_qa.human_review import ReviewStore, VERDICTS
from scripts.serve_history_v23_review import json_display


FOLDER = ROOT / 'outputs/impact_qa/batch_v25'
STORE = ReviewStore(FOLDER / 'human_review')


def targets():
    path = FOLDER / 'manifest.jsonl'
    return {r['case_id']: r for r in read_jsonl(path)} if path.exists() else {}


def result(case_id):
    path = FOLDER / 'results' / (case_id + '.json')
    if not path.exists():
        return {'case_id': case_id, 'status': 'queued'}
    try:
        return read_json(path)
    except (OSError, ValueError) as exc:
        return {'case_id': case_id, 'status': 'error', 'error': '历史记录无法读取：' + str(exc)}


def progress():
    path = FOLDER / 'progress.json'
    if not path.exists():
        return '任务队列准备中。'
    p = read_json(path)
    age = time.time() - p['updated_at_unix']
    return f"首批{p['selected']}个区间｜状态：{p['state']}｜已完成{p['counts'].get('completed', 0)}｜隔离{p['counts'].get('held', 0)}｜失败{p['counts'].get('error', 0)}｜处理中{p['counts'].get('running', 0)}｜开放QA候选{p['open_qa']}｜待补证题{p['held_qa']}｜进度更新于{age:.0f}秒前。\n\n完成表示生成及自动复核结束，不等于每条经过人工审核。"


def choices():
    rows = targets()
    values = []
    for key, t in rows.items():
        status = result(key)['status']
        subject = t.get('component') or ', '.join(t.get('atr_label_names', []))
        values.append((f"[{status}] {t['view']} | {subject} | {key[-8:]}", key))
    return values


def load(case_id):
    if not case_id:
        return None, '', '', {}, '', {}, '未审核', '', ''
    row = result(case_id)
    target = targets()[case_id]
    input_path = FOLDER / 'inputs' / (case_id + '.json')
    packet = read_json(input_path) if input_path.exists() else {}
    video = row.get('video') or packet.get('video', {}).get('path')
    info = f"{case_id}｜{target['video_id']}｜{row['status']}｜原始帧{target['start_frame']}–{target['end_frame']}"
    if row.get('error'):
        info += '\n错误：' + row['error']
    qa = '\n\n'.join(f"Q: {q['question']}\n\nA: {q['answer']}\n\n视觉支持：{q['visual_support']}；复核：{q.get('review', {}).get('verdict', '')}" for q in row.get('qa', {}).get('items', [])) or '该样本暂未产出可展示的QA候选。'
    if row.get('held_items'):
        qa += '\n\n——自动复核隔离——\n\n' + '\n\n'.join(f"Q: {q['question']}\n\nA: {q['answer']}\n\n原因：{q.get('review', {}).get('reason', '')}" for q in row['held_items'])
    history = '\n\n'.join(f"{r['source_interval_s'][0]:.3f}–{r['source_interval_s'][1]:.3f}s\n{r['description']}" for r in row.get('ledger', []))
    review = STORE.latest('batch_v25/' + case_id)
    return video, info, qa, row.get('fixed_mcq', packet.get('fixed_mcq', [])), history, json_display(row), review.get('verdict', '未审核'), review.get('corrected_answer', ''), review.get('notes', '')


def refresh(case_id):
    options = choices()
    ids = [key for label, key in options]
    if case_id not in ids:
        case_id = next((key for key in ids if result(key)['status'] == 'completed'), ids[0] if ids else None)
    return gr.update(choices=options, value=case_id), progress(), *load(case_id)


def save(case_id, reviewer, verdict, corrected, notes):
    row = result(case_id)
    if row['status'] not in ['completed', 'held']:
        raise gr.Error('该样本尚未完成生成，暂不能保存审核。')
    try:
        saved = STORE.save(dict(row, contract_id='batch_v25/' + case_id), reviewer, verdict, corrected, notes)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    return '已保存：' + saved['verdict']


def build_app():
    with gr.Blocks() as app:
        gr.Markdown('# 批量生成：具体操作开放QA\n详细描述作为证据；安装状态由ASR支撑，异常操作和固定MCQ由ATR支撑。所有新样本保留各自审核记录。')
        status = gr.Markdown(progress())
        case = gr.Dropdown(choices(), label='任务样本')
        reload = gr.Button('刷新任务与当前结果')
        info = gr.Markdown()
        video = gr.Video(label='题目对应的完整目标片段', interactive=False)
        qa = gr.Textbox(label='开放问题与答案', lines=15, interactive=False)
        with gr.Accordion('固定GT选择题', open=False):
            mcq = gr.JSON()
        with gr.Accordion('出题证据：逐段描述、history及来源', open=False):
            history = gr.Textbox(lines=16, interactive=False)
            raw = gr.JSON()
        reviewer = gr.Textbox(value='local_reviewer', label='审核人')
        verdict = gr.Radio(VERDICTS, value='未审核', label='当前样本QA审核')
        corrected = gr.Textbox(label='修正内容', lines=3)
        notes = gr.Textbox(label='备注', lines=2)
        button = gr.Button('保存审核')
        notice = gr.Markdown()
        outputs = [video, info, qa, mcq, history, raw, verdict, corrected, notes]
        app.load(refresh, [case], [case, status, *outputs])
        reload.click(refresh, [case], [case, status, *outputs], api_name='refresh_batch')
        case.change(load, [case], outputs, api_name='load_batch_case')
        button.click(save, [case, reviewer, verdict, corrected, notes], notice, api_name='save_batch_review')
        gr.Timer(10).tick(progress, outputs=status, api_name='batch_progress')
    return app
