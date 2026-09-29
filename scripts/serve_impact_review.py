import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio as gr

from impact_qa.human_review import KINDS, REVIEW, STATUS, VERDICTS, ReviewData


def build_app(data):
    def filter_rows(scope, kind):
        ids = data.ids(scope, kind)
        return gr.Dropdown(choices=data.choices(ids), value=ids[0] if ids else None), f'当前筛选 {len(ids)} 组；全部草稿 161 组。'

    def move(cid, scope, kind, step):
        ids = data.ids(scope, kind)
        if not ids:
            return None
        index = ids.index(cid) if cid in ids else 0
        return ids[max(0, min(len(ids) - 1, index + step))]

    def load(cid, context):
        if not cid:
            return None, '当前筛选没有题目。', '', '', '', '', {}, '未审核', '', '', '', None
        r = data.by_id[cid]
        p = data.packages[cid]
        start, end, target_start, target_end = data.timing(cid, context)
        saved = data.store.latest(cid)
        choices = '\n'.join(f'{chr(65+i)}. {option}' for i, option in enumerate(r['options']))
        correct = f'{chr(65 + r["GT_correct_option"])}. {r["options"][r["GT_correct_option"]]}'
        metadata = f'**{KINDS.get(r["kind"], r["kind"])} · {STATUS.get(r["status"], r["status"])}**\n\n视频：`{r["video_id"]}`  \n题目：`{cid}`  \n原录像题目区间：**{target_start:.3f}–{target_end:.3f} 秒**；当前播放：{start:.3f}–{end:.3f} 秒。'
        if context:
            metadata += f'  \n扩展视频仅供辅助审核；题目区间在播放器的 **{target_start-start:.3f}–{target_end-start:.3f} 秒**。'
        details = {'筛除原因': r['rejection_reasons'], '结构错误': r['schema_error'], '目标GT事实': p['answer_contract']['facts'], '公开参考流程': p['public_reference']['procedure']['procedure_text']}
        notice = ('上次保存：' + saved['updated_at'] + ' · ' + saved['reviewer']) if saved else '尚未保存人工审核。'
        return data.clip(cid, context), metadata, r['open_question'], r['generated_answer'], r['mcq_question'] + '\n\n' + choices + '\n\n正确选项（GT）：' + correct, r['GT_answer'], details, saved.get('verdict', '未审核'), saved.get('corrected_answer', ''), saved.get('notes', ''), notice, cid

    def save(cid, selected, reviewer, verdict, corrected, notes):
        if not cid or cid != selected:
            raise gr.Error('请等待当前题目加载完成后再保存。')
        try:
            record = data.store.save(data.by_id[cid], reviewer, verdict, corrected, notes)
        except ValueError as exc:
            raise gr.Error(str(exc)) from exc
        return f'已保存：{cid} · {record["verdict"]} · {record["updated_at"]}'

    initial_ids = data.ids('仅通过筛选（33）', '全部题型')
    with gr.Blocks(title='IMPACT QA 人工审核') as app:
        gr.Markdown('# IMPACT QA 人工审核\n161 组生成草稿，每组包含开放题与多选题。默认显示通过模型筛选的 33 组；保存审核不会修改原始生成结果。')
        with gr.Row():
            scope = gr.Dropdown(['仅通过筛选（33）', '全部生成草稿（161）'], value='仅通过筛选（33）', label='数据范围')
            kind = gr.Dropdown(['全部题型', *KINDS.values()], value='全部题型', label='题型')
        count = gr.Markdown('当前筛选 33 组；全部草稿 161 组。')
        selector = gr.Dropdown(choices=data.choices(initial_ids), value=initial_ids[0], label='选择题目', interactive=True)
        with gr.Row():
            previous = gr.Button('上一条')
            next_button = gr.Button('下一条')
            context = gr.Checkbox(False, label='播放前后各扩展 3 秒的上下文')
        metadata = gr.Markdown()
        with gr.Row():
            with gr.Column(scale=3):
                video = gr.Video(label='原始录像片段', interactive=False, autoplay=False, height=440)
            with gr.Column(scale=2):
                question = gr.Textbox(label='开放式问题', interactive=False, lines=2)
                answer = gr.Textbox(label='模型生成答案', interactive=False, lines=2)
                mcq = gr.Textbox(label='多选题与正确选项', interactive=False, lines=8)
                gt = gr.Textbox(label='GT 参考答案', interactive=False, lines=2)
        with gr.Accordion('GT 事实、参考流程与筛除原因', open=False):
            details = gr.JSON()
        with gr.Row():
            reviewer = gr.Textbox(label='审核人', value='local_reviewer')
            verdict = gr.Radio(VERDICTS, value='未审核', label='人工结论')
        corrected = gr.Textbox(label='建议修正的答案（可选）')
        notes = gr.Textbox(label='备注 / 问题描述', lines=3)
        with gr.Row():
            save_button = gr.Button('保存审核', variant='primary')
            export_button = gr.Button('导出全部人工审核记录')
        notice = gr.Markdown('切换题目前请先保存审核。')
        export_file = gr.File(label='审核记录 JSONL', interactive=False)
        loaded = gr.State(None)
        outputs = [video, metadata, question, answer, mcq, gt, details, verdict, corrected, notes, notice, loaded]
        scope.change(filter_rows, [scope, kind], [selector, count], api_name='filter_cases')
        kind.change(filter_rows, [scope, kind], [selector, count], api_name=False)
        selector.change(load, [selector, context], outputs, api_name='load_case')
        context.change(load, [selector, context], outputs, api_name=False)
        previous.click(lambda cid, s, k: move(cid, s, k, -1), [selector, scope, kind], selector, api_name=False)
        next_button.click(lambda cid, s, k: move(cid, s, k, 1), [selector, scope, kind], selector, api_name=False)
        save_button.click(save, [loaded, selector, reviewer, verdict, corrected, notes], notice, api_name='save_review')
        export_button.click(data.store.export, [], export_file, api_name='export_reviews')
        app.load(load, [selector, context], outputs, api_name=False)
    return app


def main():
    from scripts.serve_unified_review import main as serve
    serve()


if __name__ == '__main__':
    main()
