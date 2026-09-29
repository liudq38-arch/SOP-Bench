import json
import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl
from impact_qa.human_review import ReviewStore, VERDICTS


FOLDER = ROOT / 'outputs/impact_qa/event_v22'
BASE = ROOT / 'outputs/impact_qa/descriptive_v21'
RECORDS = {r['case']['case_id']: r for r in read_jsonl(BASE / 'cases.jsonl')}
STORE = ReviewStore(FOLDER / 'human_review')


def load(case_id, branch='B'):
    record = RECORDS[case_id]
    clip = record['clips'][3 if '403f880f' in case_id else 0]
    path = FOLDER / ('runs/B' if branch == 'B' else 'assisted') / (clip['clip_id'] + '.json')
    result = read_json(path) if path.exists() else {'status': '运行中'}
    old_path = BASE / 'runs' / case_id / (clip['clip_id'] + '.json')
    old = read_json(old_path) if old_path.exists() else {}
    old_qa = '\n\n'.join('Q: ' + q['question'] + '\nA: ' + q['answer'] for q in old.get('qa', {}).get('items', []))
    qa = result.get('qa')
    new_qa = 'Q: ' + qa['question'] + '\n\nA: ' + qa['answer'] if qa else '尚无通过本轮模型筛选的问答。'
    verdicts = {v['claim_id']: v['verdict'] for v in result.get('verification', {}).get('verdicts', [])}
    rows = [[e['event_id'], e['evidence_span_s'], e['text'], verdicts.get(e['event_id'], 'pending'), e['evidence_frame_ids']] for e in result.get('events', [])]
    review_path = FOLDER / 'agent_review.json'
    agent = read_json(review_path).get(case_id, {}) if review_path.exists() and branch == 'B' else {}
    provenance = '自动观察分支' if branch == 'B' else '代理看图提供事件的辅助对照，不计自动生成准确率'
    info = f"{provenance}。状态：{result['status']}；核心区间（源时间）：{clip['core_frames'][0]['source_pts_s']:.3f}–{clip['core_frames'][-1]['source_pts_s']:.3f}秒。模型筛选不等于人工通过。代理复查：{agent.get('disposition', '待真人核验')}。"
    stored = STORE.latest('v22/' + branch + '/' + clip['clip_id'])
    cross_path = FOLDER / 'crosscheck8b' / ('candidate_' + clip['clip_id'] + '.json')
    cross = read_json(cross_path) if cross_path.exists() and branch == 'B' else {}
    return clip['video']['path'], info, new_qa, old_qa, rows, {'result': result, 'agent_review': agent, 'crosscheck8b': cross}, stored.get('verdict', '未审核'), stored.get('corrected_answer', ''), stored.get('notes', '')


def save(case_id, branch, reviewer, verdict, corrected, notes):
    record = RECORDS[case_id]
    clip = record['clips'][3 if '403f880f' in case_id else 0]
    path = FOLDER / ('runs/B' if branch == 'B' else 'assisted') / (clip['clip_id'] + '.json')
    if not path.exists():
        raise gr.Error('结果尚未生成。')
    try:
        row = STORE.save(dict(read_json(path), contract_id='v22/' + branch + '/' + clip['clip_id']), reviewer, verdict, corrected, notes)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    return '已保存：' + row['verdict']


def build_app():
    with gr.Blocks(title='IMPACT v22事件证据与QA对照') as app:
        gr.Markdown('# IMPACT事件描述QA对照\n对照视频检查每条事件事实、动作先后及遗漏，再审核问题和答案。模型筛选结果和代理复查均不是人工金标准。')
        select = gr.Dropdown(list(RECORDS), value=next(iter(RECORDS)), label='片段与视角')
        branch = gr.Dropdown([('自动观察生成（存在已知错误）', 'B'), ('代理事件辅助对照（待人工核验）', 'assisted')], value='assisted', label='结果来源')
        refresh = gr.Button('刷新')
        video = gr.Video(label='输入视频（含边界上下文）', interactive=False)
        info = gr.Markdown()
        current = gr.Textbox(label='v22开放问答', lines=10, interactive=False)
        baseline = gr.Textbox(label='v21原始问答（对照）', lines=8, interactive=False)
        events = gr.Dataframe(headers=['事件ID', '证据时间范围', '事实', '模型判定', '证据帧'], interactive=False)
        with gr.Accordion('来源核对与原始输出', open=False):
            raw = gr.JSON()
        reviewer = gr.Textbox(label='审核人', value='local_reviewer')
        verdict = gr.Radio(VERDICTS, value='未审核', label='结论')
        corrected = gr.Textbox(label='修正答案', lines=4)
        notes = gr.Textbox(label='错误或遗漏', lines=3)
        save_button = gr.Button('保存人工审核')
        notice = gr.Markdown()
        outputs = [video, info, current, baseline, events, raw, verdict, corrected, notes]
        app.load(load, [select, branch], outputs)
        select.change(load, [select, branch], outputs, api_name='load_case')
        branch.change(load, [select, branch], outputs)
        refresh.click(load, [select, branch], outputs)
        save_button.click(save, [select, branch, reviewer, verdict, corrected, notes], notice, api_name='save_review')
    return app


def main():
    from scripts.serve_unified_review import main as serve
    serve()


if __name__ == '__main__':
    main()
