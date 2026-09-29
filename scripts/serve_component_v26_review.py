import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import fingerprint, read_json, read_jsonl, save_jsonl
from impact_qa.human_review import ReviewStore, VERDICTS
from impact_qa.v26_data import CONFIG, FOLDER


STORE = ReviewStore(FOLDER / 'human_review')
KINDS = {'action_sequence': '详细动作序列', 'step_completion': '组件完成性', 'tools_parts': '工具与部件', 'observed_order': '动作顺序', 'duration': '动作时长', 'mcq_anomaly_types': '固定七选项MCQ'}


def manifest():
    p = FOLDER / 'manifest.jsonl'
    return read_jsonl(p) if p.exists() else []


def get_result(cid, arm):
    p = FOLDER / 'results' / (cid + '_' + arm + '.json')
    return read_json(p) if p.exists() else {'status': 'queued', 'questions': []}


def get_plan(cid):
    p = FOLDER / 'plans' / (cid + '.json')
    return read_json(p) if p.exists() else {'questions': [], 'mcq': []}


def progress():
    p = FOLDER / 'progress.json'
    if not p.exists():
        return 'v26 数据准备中。'
    d = read_json(p)
    return f"v26｜{d['state']}｜23个计划clip中的实际选样数：{d['selected_clips']}｜A/B状态：{d['arm_status']}｜开放题：{d['question_status']}。自动通过仍需人工审核。A仅GT，B为同一完整clip＋相同GT；不使用2秒history。"


def choices():
    return [(f"{i + 1}. {c['workflow']} | {'有ASR' if c['has_asr'] else '无ASR'} | {c['duration_s']:.1f}s | {c['video_id']} | {c['clip_id'][-6:]}", c['clip_id']) for i, c in enumerate(manifest())]


def question_choices(cid):
    p = get_plan(cid)
    return [(f"{KINDS.get(q['kind'], q['kind'])} | {q['question_id'].removeprefix(cid + '_')}", q['question_id']) for q in p['questions'] + p['mcq']]


def question_record(cid, qid, arm):
    return next((q for q in get_result(cid, arm).get('questions', []) if q['question_id'] == qid), None)


def contract(row, arm):
    return f"component_v26/{CONFIG['version']}/{row['question_id']}/{arm}/{fingerprint(row)[:16]}"


def safe_display(value):
    if isinstance(value, dict):
        return {('artifact_path' if k == 'path' else k): safe_display(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_display(v) for v in value]
    return value


def load_question(cid, qid):
    if not cid or not qid:
        return '', '', '', {}, '', '未审核', '未审核', '', '', ''
    plan = get_plan(cid)
    q = next((q for q in plan['questions'] + plan['mcq'] if q['question_id'] == qid), None)
    if q is None:
        raise gr.Error('题目ID不属于所选clip。')
    if q['kind'] == 'mcq_anomaly_types':
        options = '\n'.join(f"{o['id']}. {o['name']}: {o['definition']}" for o in q['options'])
        answer = 'Correct options: ' + ', '.join(q['correct_option_ids'])
        reviewed = STORE.latest(contract(q, 'shared_mcq'))
        return q['question'] + '\n\n' + options, answer, 'A/B共享同一确定性GT答案。', safe_display(q), '固定MCQ：代码计算，多选；correct与异常互斥。审核保存至A栏。', reviewed.get('verdict', '未审核'), '未审核', reviewed.get('corrected_answer', ''), '', reviewed.get('notes', '')
    a, b = question_record(cid, qid, 'A'), question_record(cid, qid, 'B')
    va = STORE.latest(contract(a, 'A')) if a else {}
    vb = STORE.latest(contract(b, 'B')) if b else {}
    status = '\n'.join(f"{arm}: {row.get('status')} / {row.get('visual_support')} / {row.get('automatic_review', {}).get('reason', '')}" if row else f"{arm}: {get_result(cid, arm).get('status')} {get_result(cid, arm).get('error', '')}" for arm, row in [('A', a), ('B', b)])
    evidence = {'gt_reference_answer': q['reference_answer'], 'facts': q['reference_facts'], 'A_evidence_note': a.get('evidence_note') if a else None, 'B_evidence_note': b.get('evidence_note') if b else None}
    return q['question'], a['answer'] if a else '尚未生成可审核答案', b['answer'] if b else '尚未生成可审核答案', safe_display(evidence), status, va.get('verdict', '未审核'), vb.get('verdict', '未审核'), va.get('corrected_answer', ''), vb.get('corrected_answer', ''), va.get('notes') or vb.get('notes', '')


def load_case(cid, qid=None):
    options = question_choices(cid) if cid else []
    if qid not in {q for _, q in options}:
        qid = options[0][1] if options else None
    clip = next((c for c in manifest() if c['clip_id'] == cid), None)
    media = FOLDER / 'media_manifests' / (str(cid) + '.json')
    if media.exists():
        m = read_json(media)
        video = m['path']
        info = f"{clip['video_id']}｜源视频 {m['source_start_pts_s']:.3f}–{m['source_end_pts_s']:.3f}s｜模型实际 {m['actual_sample_count']} 帧｜最大采样间隔 {m['sample_max_gap_s']:.3f}s｜未采到帧的原子动作 {len(m['events_without_sample'])} 个。GT支持和视觉可见性分别审查。"
    else:
        video, info = None, '该clip尚未完成媒体准备。'
    return video, info, gr.update(choices=options, value=qid), *load_question(cid, qid)


def refresh(cid, qid):
    options = choices()
    if cid not in {value for _, value in options}:
        cid = options[0][1] if options else None
    return gr.update(choices=options, value=cid), progress(), *load_case(cid, qid)


def save(cid, qid, reviewer, verdict_a, verdict_b, corrected_a, corrected_b, notes):
    q = next((q for q in get_plan(cid)['mcq'] if q['question_id'] == qid), None)
    records = []
    if q:
        if verdict_a == '未审核':
            raise gr.Error('请在A栏选择MCQ审核结论。')
        records = [(q, 'shared_mcq', verdict_a, corrected_a)]
    else:
        for arm, verdict, corrected in [('A', verdict_a, corrected_a), ('B', verdict_b, corrected_b)]:
            if verdict != '未审核':
                row = question_record(cid, qid, arm)
                if row is None:
                    raise gr.Error(arm + '方案尚无可审核答案。')
                records.append((row, arm, verdict, corrected))
    if not records:
        raise gr.Error('请至少选择一个审核结论。')
    saved = []
    for row, arm, verdict, corrected in records:
        saved.append(STORE.save(dict(row, contract_id=contract(row, arm)), reviewer, verdict, corrected, notes))
    with STORE.connect() as db:
        import sqlite3
        db.row_factory = sqlite3.Row
        history = [dict(r) for r in db.execute('SELECT * FROM reviews ORDER BY id')]
    save_jsonl(FOLDER / 'human_reviews.jsonl', history)
    return '已保存 ' + str(len(saved)) + ' 条逐题审核记录；原答案保留，修订另存。'


def build_app():
    with gr.Blocks() as app:
        gr.Markdown('# v26：GT优先的完整clip A/B问答\nA只用GT，B使用同一GT和完整视频。默认英语QA；先播放视频，再展开GT检查。详细动作序列允许多部件、多工具，并行动作以时间区间展示。')
        status = gr.Markdown(progress())
        case = gr.Dropdown(choices(), label='Clip')
        reload = gr.Button('刷新进度与当前题')
        info = gr.Markdown()
        video = gr.Video(label='完整clip（可播放）', interactive=False)
        selected_question = gr.Dropdown(label='逐题选择')
        question_text = gr.Textbox(label='共同问题', lines=3, interactive=False)
        with gr.Row():
            answer_a = gr.Textbox(label='A：仅GT', lines=18, interactive=False)
            answer_b = gr.Textbox(label='B：GT＋完整clip', lines=18, interactive=False)
        machine = gr.Textbox(label='自动复核状态', lines=3, interactive=False)
        with gr.Accordion('GT参考答案与逐事实来源（审核时展开）', open=False):
            evidence = gr.JSON()
        reviewer = gr.Textbox(value='local_reviewer', label='审核人')
        with gr.Row():
            verdict_a = gr.Radio(VERDICTS, value='未审核', label='A / 共享MCQ审核')
            verdict_b = gr.Radio(VERDICTS, value='未审核', label='B审核')
        with gr.Row():
            corrected_a = gr.Textbox(label='A修订答案（可选）')
            corrected_b = gr.Textbox(label='B修订答案（可选）')
        notes = gr.Textbox(label='错误归因、遗漏或证据问题')
        save_button = gr.Button('保存当前题审核')
        notice = gr.Markdown()
        q_outputs = [question_text, answer_a, answer_b, evidence, machine, verdict_a, verdict_b, corrected_a, corrected_b, notes]
        case_outputs = [video, info, selected_question, *q_outputs]
        app.load(refresh, [case, selected_question], [case, status, *case_outputs])
        reload.click(refresh, [case, selected_question], [case, status, *case_outputs], api_name='refresh_v26')
        case.change(load_case, [case], case_outputs, api_name='load_v26_case')
        selected_question.change(load_question, [case, selected_question], q_outputs, api_name='load_v26_question')
        save_button.click(save, [case, selected_question, reviewer, verdict_a, verdict_b, corrected_a, corrected_b, notes], notice, api_name='save_v26_question_review')
        gr.Timer(15).tick(progress, outputs=status, api_name='v26_progress')
    return app
