import json
import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.human_review import ROOT, ReviewStore, VERDICTS, read_rows


FOLDER = ROOT / 'outputs/impact_qa/descriptive_v21'
CONFIG = json.loads((ROOT / 'configs/impact_qa/descriptive_v21_pilot.json').read_text())
RECORDS = {r['case']['case_id']: r for r in read_rows(FOLDER / 'cases.jsonl')}
STORE = ReviewStore(FOLDER / 'human_review')


def load(case_id):
    record = RECORDS[case_id]
    case = record['case']
    index = CONFIG['pilot_selection']['clip_indices'].get(case['pair_id'], 0)
    clip = record['clips'][index]
    result_path = FOLDER / 'runs' / case_id / (clip['clip_id'] + '.json')
    result = json.loads(result_path.read_text()) if result_path.exists() else {'status': '生成中，稍后刷新'}
    description = '\n\n'.join(s['text'] for s in result.get('description', {}).get('sections', []))
    qa = '\n\n'.join(f"Q: {q['question']}\n\nA: {q['answer']}" for q in result.get('qa', {}).get('items', []))
    cards_path = FOLDER / 'runs' / case_id / 'frame_cards.jsonl'
    cards = read_rows(cards_path) if cards_path.exists() else []
    values = [[c['frame_id'], round(c['source_pts_s'], 4), c.get('details', ''), c.get('change_from_previous', ''), '; '.join(c.get('unknowns', []))] for c in cards]
    a, b = clip['core_frames'][0]['source_pts_s'], clip['core_frames'][-1]['source_pts_s']
    offset = clip['media_frames'][0]['source_pts_s']
    info = f"状态：{result['status']}。原视频目标共{len(record['frames'])}帧；本次只测试其中{len(clip['core_frames'])}帧。题目核心区间：源视频{a:.3f}–{b:.3f}秒；播放器{a-offset:.3f}–{b-offset:.3f}秒。播放器包含少量边界重叠。模型草稿，不是金标准。"
    stored = STORE.latest(clip['clip_id'])
    return clip['video']['path'], info, description, qa, values, result, stored.get('verdict', '未审核'), stored.get('corrected_answer', ''), stored.get('notes', '')


def save(case_id, reviewer, verdict, corrected, notes):
    record = RECORDS[case_id]
    index = CONFIG['pilot_selection']['clip_indices'].get(record['case']['pair_id'], 0)
    clip = record['clips'][index]
    path = FOLDER / 'runs' / case_id / (clip['clip_id'] + '.json')
    if not path.exists():
        raise gr.Error('该片段尚未完成生成。')
    row = dict(json.loads(path.read_text()), contract_id=clip['clip_id'])
    try:
        result = STORE.save(row, reviewer, verdict, corrected, notes)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    return '已保存：' + result['verdict']


def build_app():
    with gr.Blocks(title='详细事件描述与开放QA小样') as app:
        gr.Markdown('# 详细事件描述与开放QA小样\n先对照视频检查动作先后、工具/部件、两手配合、遗漏和未经证实的结论。这里只展示6个短clip，不代表整个ATR事件都完成了逐帧生成。')
        select = gr.Dropdown(list(RECORDS), value=next(iter(RECORDS)), label='片段/视角')
        refresh = gr.Button('刷新结果')
        video = gr.Video(label='实际输入的视频窗口', interactive=False)
        info = gr.Markdown()
        description = gr.Textbox(label='完整事件描述', lines=10, interactive=False)
        qa = gr.Textbox(label='描述性开放问答', lines=12, interactive=False)
        with gr.Accordion('逐帧记录', open=False):
            cards = gr.Dataframe(headers=['帧ID', '源时间秒', '可见细节', '相邻变化', '未知'], interactive=False)
        with gr.Accordion('原始结果和模型审核', open=False):
            raw = gr.JSON()
        reviewer = gr.Textbox(value='local_reviewer', label='审核人')
        verdict = gr.Radio(VERDICTS, value='未审核', label='结论')
        corrected = gr.Textbox(label='修正描述/答案', lines=4)
        notes = gr.Textbox(label='问题与遗漏', lines=3)
        save_button = gr.Button('保存人工审核')
        notice = gr.Markdown()
        outputs = [video, info, description, qa, cards, raw, verdict, corrected, notes]
        app.load(load, select, outputs)
        select.change(load, select, outputs, api_name='load_case')
        refresh.click(load, select, outputs)
        save_button.click(save, [select, reviewer, verdict, corrected, notes], notice, api_name='save_review')
    return app


def main():
    from scripts.serve_unified_review import main as serve
    serve()


if __name__ == '__main__':
    main()
