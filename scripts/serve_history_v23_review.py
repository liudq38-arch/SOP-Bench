import json
import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl
from impact_qa.human_review import ReviewStore, VERDICTS


FOLDER = ROOT / 'outputs/impact_qa/history_v23'
RECORDS = {r['case']['case_id']: r for r in read_jsonl(ROOT / 'outputs/impact_qa/descriptive_v21/cases.jsonl') if r['case']['pair_id'] == 'atr_403f880f747b22eb'}
MEDIA = {r['case_id']: r for r in read_json(FOLDER / 'review_media.json')}
STORE = ReviewStore(FOLDER / 'human_review')
STEP_FOLDER = ROOT / 'outputs/impact_qa/step_v24'
STEP_STORE = ReviewStore(STEP_FOLDER / 'human_review')
COMPLETION_FOLDER = ROOT / 'outputs/impact_qa/completion_v24'
COMPLETION_STORE = ReviewStore(COMPLETION_FOLDER / 'human_review')


def completion_cases():
    path = COMPLETION_FOLDER / 'manifest.json'
    return [r['case_id'] for r in read_json(path)] if path.exists() else []


def json_display(value):
    if isinstance(value, dict):
        return {('artifact_path' if key == 'path' else key): json_display(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_display(item) for item in value]
    return value


def load_completion(case_id):
    path = COMPLETION_FOLDER / 'results' / (case_id + '.json')
    result = read_json(path) if path.exists() else {}
    inputs = read_json(COMPLETION_FOLDER / 'inputs' / (case_id + '.json'))
    target, video = inputs['target'], inputs['video']
    observation = result.get('observation', {})
    qa = '\n\n'.join(f"Q: {q['question']}\n\nA: {q['answer']}\n\n视觉核验：{q['visual_support']}；{q['visual_limitation']}" for q in result.get('qa', {}).get('items', []))
    info = f"完成性对照小样：{result.get('status', 'running')}。同视角ASR末端状态={target['state_at_end']}（-1错误安装，1正确安装）；仅判断防振手柄，不表示整机完成。该小样整段输入{len(video['sampled_frames'])}帧，2秒片段编号不适用。源时间{target['source_interval_s'][0]:.3f}–{target['source_interval_s'][1]:.3f}秒。"
    review = COMPLETION_STORE.latest(case_id)
    return video['path'], video['path'], info, observation.get('description', ''), {}, {}, observation.get('visible_end_state', ''), '', qa, {'note': '完成性补充样本，本页未新增MCQ；原ATR固定MCQ保持不变。'}, [observation.get('limitations', '')], json_display(result), review.get('verdict', '未审核'), review.get('corrected_answer', ''), review.get('notes', '')


def step_result(case_id):
    path = STEP_FOLDER / 'results' / (case_id + '.json')
    value = read_json(path) if path.exists() else {}
    ready_path = STEP_FOLDER / 'review_ready' / (case_id + '.json')
    if ready_path.exists():
        ready = read_json(ready_path)
        if ready.get('source_cache_key') == value.get('cache_key'):
            value = ready
    return value if value.get('status') == 'pending_review' else {}


def load(case_id, clip_index):
    if case_id in completion_cases():
        return load_completion(case_id)
    path = FOLDER / 'runs' / case_id / 'result.json'
    result = read_json(path) if path.exists() else {'status': 'running', 'ledger': []}
    index = int(clip_index)
    record = RECORDS[case_id]
    clip = record['clips'][index]
    row = result['ledger'][index] if index < len(result['ledger']) else {}
    local = row.get('description', '该片段尚未完成。')
    history = result['ledger'][index - 1]['memory_after'] if index and index <= len(result['ledger']) else {}
    integration = result.get('integration', {})
    sections = '\n\n'.join(s['description'] for s in integration.get('sections', []))
    revision_path = FOLDER / 'qa_visual_revision' / (case_id + '.json')
    revision = read_json(revision_path) if revision_path.exists() else {}
    ready_path = FOLDER / 'review_ready' / (case_id + '.json')
    ready = read_json(ready_path) if ready_path.exists() else {}
    step = step_result(case_id)
    qa_source = step or ready or (revision if revision.get('status') == 'pending_review' else result)
    qa = '\n\n'.join(f"[{q['kind']}] Q: {q['question']}\n\nA: {q['answer']}" for q in qa_source.get('qa', {}).get('items', []))
    mcq_path = FOLDER / 'fixed_mcq.jsonl'
    mcq = [r for r in read_jsonl(mcq_path) if r['case_id'] == case_id] if mcq_path.exists() else []
    info = f"状态：{result['status']}；已连续描述{len(result['ledger'])}/{len(record['clips'])}段。这里只处理完整选定ATR事件，不是整条源视频。当前片段源时间：{clip['core_frames'][0]['source_pts_s']:.3f}–{clip['core_frames'][-1]['source_pts_s']:.3f}秒。"
    if step:
        old_review = STORE.latest('history_v23/' + case_id)
        info += f" 当前展示v24具体步骤QA；原v23审核：{old_review.get('verdict', '未审核')}，不自动沿用为新题目的结论。"
        if step.get('held_items'):
            qa += '\n\n——待补证，不纳入可回答QA——\n\n' + '\n\n'.join(f"Q: {q['question']}\n\nA: {q['answer']}" for q in step['held_items'])
    elif ready.get('held_items'):
        info += f" 有{len(ready['held_items'])}道否定事件题因缺少充分依据隔离，保留在原始记录中。"
    review = STEP_STORE.latest('step_v24/' + case_id) if step else STORE.latest('history_v23/' + case_id)
    return MEDIA[case_id]['path'], clip['video']['path'], info, local, history, row.get('memory_after', {}), sections, integration.get('overall_description', ''), qa, mcq, integration.get('contradictions_or_uncertainties', []), {'original': result, 'qa_visual_revision': revision, 'review_ready': ready, 'step_v24': step}, review.get('verdict', '未审核'), review.get('corrected_answer', ''), review.get('notes', '')


def save(case_id, reviewer, verdict, corrected, notes):
    if case_id in completion_cases():
        result = read_json(COMPLETION_FOLDER / 'results' / (case_id + '.json'))
        try:
            value = COMPLETION_STORE.save(dict(result, contract_id=case_id), reviewer, verdict, corrected, notes)
        except ValueError as exc:
            raise gr.Error(str(exc)) from exc
        return '已保存：' + value['verdict']
    result = read_json(FOLDER / 'runs' / case_id / 'result.json')
    revision_path = FOLDER / 'qa_visual_revision' / (case_id + '.json')
    ready_path = FOLDER / 'review_ready' / (case_id + '.json')
    result = {'original': result, 'qa_visual_revision': read_json(revision_path) if revision_path.exists() else {}, 'review_ready': read_json(ready_path) if ready_path.exists() else {}}
    step = step_result(case_id)
    try:
        value = STEP_STORE.save(dict(step, contract_id='step_v24/' + case_id), reviewer, verdict, corrected, notes) if step else STORE.save(dict(result, contract_id='history_v23/' + case_id), reviewer, verdict, corrected, notes)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    return '已保存：' + value['verdict']


def build_app():
    with gr.Blocks(title='连续2秒视频与history实验') as app:
        gr.Markdown('# 具体步骤理解：完成了吗、执行正确吗、先后如何\n先看视频和开放QA。详细描述与history作为出题证据收起展示。新QA单独审核；待补证的完成性问题不纳入可回答QA。MCQ仍来自ATR GT。')
        choices = [(key, key) for key in RECORDS] + [('完成性对照：' + ('尚未正确安装防振手柄' if key.endswith('misassembled') else '已正确安装防振手柄'), key) for key in completion_cases()]
        case = gr.Dropdown(choices, value=next(iter(RECORDS)), label='视频／具体步骤样本')
        index = gr.Dropdown(list(range(8)), value=0, label='2秒核心片段编号')
        refresh = gr.Button('刷新')
        info = gr.Markdown()
        with gr.Row():
            full = gr.Video(label='完整选定事件', interactive=False)
            current = gr.Video(label='当前输入片段（含少量边界重叠）', interactive=False)
        qa = gr.Textbox(label='具体操作的开放问题与答案', lines=20, interactive=False)
        with gr.Accordion('出题依据：详细描述与history（不是题目）', open=False):
            description = gr.Textbox(label='当前片段详细描述', lines=8, interactive=False)
            with gr.Row():
                previous = gr.JSON(label='读取该片段前的history摘要')
                memory = gr.JSON(label='读取该片段后的history摘要')
            integrated = gr.Textbox(label='按时间整合的详细叙述', lines=12, interactive=False)
            summary = gr.Textbox(label='整体过程概述', lines=5, interactive=False)
        with gr.Accordion('固定GT选择题、不确定点与原始记录', open=False):
            mcq = gr.JSON(label='固定MCQ')
            uncertainties = gr.JSON(label='整合时保留的不确定点')
            raw = gr.JSON(label='全部局部描述、事件ID和历史')
        reviewer = gr.Textbox(value='local_reviewer', label='审核人')
        verdict = gr.Radio(VERDICTS, value='未审核', label='当前版本QA的审核结论')
        corrected = gr.Textbox(label='修正内容', lines=4)
        notes = gr.Textbox(label='问题或遗漏', lines=3)
        button = gr.Button('保存审核')
        notice = gr.Markdown()
        outputs = [full, current, info, description, previous, memory, integrated, summary, qa, mcq, uncertainties, raw, verdict, corrected, notes]
        app.load(load, [case, index], outputs)
        case.change(load, [case, index], outputs, api_name='load_case')
        index.change(load, [case, index], outputs)
        refresh.click(load, [case, index], outputs)
        button.click(save, [case, reviewer, verdict, corrected, notes], notice, api_name='save_review')
    return app


def main():
    from scripts.serve_unified_review import main as serve
    serve()


if __name__ == '__main__':
    main()
