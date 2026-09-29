import os
import sys
from pathlib import Path

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED','False')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import gradio as gr

from impact_qa.common import OUT, read_json, read_jsonl
from impact_qa.human_review import ReviewStore, VERDICTS


def build_app():
    folder=OUT/'atr_v19'
    rows=read_jsonl(OUT/'atr_v19_1/qa_drafts.jsonl')
    cases={c['case_id']:c for c in read_jsonl(folder/'cases.jsonl')}
    lookup={(r['pair_id'],r['kind'],r['view']):r for r in rows}
    clips={c['case_id']:c for c in read_jsonl(folder/'review_clips.jsonl')}
    pairs=list(dict.fromkeys(r['pair_id'] for r in rows))
    kinds={'实际动作':'actual_action','实际工具':'actual_tool','是否用错工具':'tool_error','异常类别':'anomaly_type','后续观察到的改变':'observed_correction','应该使用的工具（缺规范）':'expected_tool','是否及时纠正（缺时限）':'timely_correction'}
    store=ReviewStore(folder/'human_reviews')
    def render(r):
        if not r:return '该视角生成失败，无有效草稿。'
        if not r['answerable']:return f'问题：{r["question"]}\n\n本项未生成确定答案。\n原因：{r["limitation"]}'
        options='\n'.join(f'{chr(65+i)}. {o}' for i,o in enumerate(r['options']))
        return f'问题：{r["question"]}\n\n模型答案：{r["answer"]}\n\n{options}\n正确项（模型草稿）：{chr(65+r["correct_option"])}\n\n状态：{r["status"]}\n证据：{r["evidence"]}\n限制：{r["limitation"]}'
    def load(pair,kind,review_view):
        output=[];intervals=[]
        for view in ['ego','front']:
            clip=clips[pair+'_'+view];output.extend([clip['path'],render(lookup.get((pair,kinds[kind],view)))])
            intervals.append(f'{view} 播放器内题目区间 {clip["target_start_local_s"]:.2f}–{clip["target_end_local_s"]:.2f} 秒')
        r=lookup.get((pair,kinds[kind],review_view));cid=r['contract_id'] if r else None;s=store.latest(cid) if cid else {}
        native=[read_json(p) for p in sorted((OUT/'atr_video_v20/probe_runs').glob(pair+'*.json'))]
        return (*output,'；'.join(intervals),s.get('verdict','未审核'),s.get('corrected_answer',''),s.get('notes',''),cid,{'ATR类别':cases[pair+'_ego']['shared_gt']['atr_labels'],'目标手':cases[pair+'_ego']['shared_gt']['target_hand'],'审核视角':review_view,'GT动作上下文':cases[pair+'_ego']['shared_gt']['atomic_context']},'尚未审核' if not s else '已保存：'+s['updated_at'],native or {'状态':'该事件尚未运行视频模式小样'})
    def save(cid,pair,kind,view,reviewer,verdict,corrected,notes):
        r=lookup.get((pair,kinds[kind],view))
        if not r or cid!=r['contract_id']:raise gr.Error('请等待题目加载完成。')
        try:result=store.save(r,reviewer,verdict,corrected,notes)
        except ValueError as exc:raise gr.Error(str(exc)) from exc
        return '已保存：'+result['contract_id']+' · '+result['verdict']
    def move(pair,step):return pairs[max(0,min(len(pairs)-1,pairs.index(pair)+step))]
    choices=[(f'{i+1}. {cases[p+"_ego"]["trial"]} | '+','.join(cases[p+'_ego']['shared_gt']['atr_labels']),p) for i,p in enumerate(pairs)]
    with gr.Blocks(title='ATR 第一视角与正面对照审核') as app:
        gr.Markdown('# ATR 异常 QA：第一视角与正面对照\n同一事件并排展示两视角。视频含之前3秒和之后最多20秒；播放器下方标明真正题目区间。模型草稿及筛选状态均待人工验证。切换前请保存。')
        pair=gr.Dropdown(choices,value=pairs[0],label='异常事件')
        with gr.Row():
            prev=gr.Button('上一事件');nxt=gr.Button('下一事件');kind=gr.Dropdown(list(kinds),value='实际工具',label='问题类型')
        with gr.Row():
            with gr.Column():ego=gr.Video(label='第一视角 ego',interactive=False);ego_qa=gr.Textbox(label='第一视角生成结果',lines=13,interactive=False)
            with gr.Column():front=gr.Video(label='正面 front',interactive=False);front_qa=gr.Textbox(label='正面生成结果',lines=13,interactive=False)
        times=gr.Markdown()
        with gr.Accordion('ATR 与上下文 GT',open=False):detail=gr.JSON()
        with gr.Accordion('原生视频模式小样输出（仅部分事件，未经质量验收）',open=False):native=gr.JSON()
        with gr.Row():view=gr.Radio(['ego','front'],value='ego',label='本次审核哪个视角的答案');reviewer=gr.Textbox(value='local_reviewer',label='审核人')
        verdict=gr.Radio(VERDICTS,value='未审核',label='审核结论');corrected=gr.Textbox(label='修正答案');notes=gr.Textbox(label='备注',lines=3)
        with gr.Row():save_btn=gr.Button('保存该视角审核',variant='primary');export=gr.Button('导出审核记录')
        notice=gr.Markdown();download=gr.File(interactive=False);loaded=gr.State()
        outputs=[ego,ego_qa,front,front_qa,times,verdict,corrected,notes,loaded,detail,notice,native]
        for component in [pair,kind,view]:component.change(load,[pair,kind,view],outputs,api_name='load_pair' if component is pair else False)
        app.load(load,[pair,kind,view],outputs,api_name=False)
        prev.click(lambda p:move(p,-1),pair,pair,api_name=False);nxt.click(lambda p:move(p,1),pair,pair,api_name=False)
        save_btn.click(save,[loaded,pair,kind,view,reviewer,verdict,corrected,notes],notice,api_name='save_review')
        export.click(store.export,[],download,api_name='export_reviews')
    return app


def main():
    from scripts.serve_unified_review import main as serve
    serve()


if __name__=='__main__':main()
