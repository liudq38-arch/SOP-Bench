import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ['IMPACT_V26_CONFIG'] = 'configs/impact_qa/component_v26_gt.json'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio as gr

from impact_qa.common import read_json, read_jsonl
from impact_qa.v26_data import FOLDER


KINDS = {
    'action_sequence': '整体操作与详细动作',
    'step_completion': '组件完成性',
    'tools_parts': '工具与部件',
    'observed_order': '观察到的顺序',
    'duration': '动作时长',
}


def manifest():
    path = FOLDER / 'manifest.jsonl'
    return read_jsonl(path) if path.exists() else []


def result(cid):
    path = FOLDER / 'results' / (cid + '_A.json')
    return read_json(path) if path.exists() else {'status': 'queued', 'questions': []}


def plan(cid):
    path = FOLDER / 'plans' / (cid + '.json')
    return read_json(path) if path.exists() else {'questions': [], 'mcq': []}


def review_media(cid, clip):
    """Return a materialized clip for human review without adding it to model inputs."""
    manifest_path = FOLDER / 'media_manifests' / (cid + '.json')
    if manifest_path.exists():
        value = read_json(manifest_path)
        path = Path(value.get('path', ''))
        if path.exists():
            return str(path)
    source = Path(clip.get('source_video', ''))
    if not source.exists():
        return None
    media_dir = FOLDER / 'review_media'
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / (cid + '.mp4')
    if not target.exists():
        start = float(clip['source_start_s'])
        duration = max(0.05, float(clip['source_end_s']) - start)
        ffmpeg = shutil.which('ffmpeg')
        for candidate in [
            '/home/ldq/miniconda3/envs/ffmpeg/bin/ffmpeg',
            '/home/ldq/miniconda3/pkgs/ffmpeg-9.0.1-gpl_hc1c51de_902/bin/ffmpeg',
        ]:
            if ffmpeg or not Path(candidate).exists():
                continue
            ffmpeg = candidate
        if not ffmpeg:
            return None
        command = [
            ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
            '-ss', f'{start:.6f}', '-i', str(source), '-t', f'{duration:.6f}',
            '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-pix_fmt', 'yuv420p', str(target),
        ]
        try:
            subprocess.run(command, check=True, timeout=180)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
    return str(target) if target.exists() else None


def choices():
    values = []
    for row in manifest():
        record = result(row['clip_id'])
        values.append((f"[{record.get('status', 'queued')}] {row['workflow']} | {'有ASR' if row['has_asr'] else '无ASR'} | {row['duration_s']:.1f}s | {row['video_id']} | {row['clip_id'][-8:]}", row['clip_id']))
    return values


def progress():
    path = FOLDER / 'progress.json'
    if not path.exists():
        return 'GT-only 计划已准备，等待 Qwen3.8 服务和生成任务。'
    data = read_json(path)
    return f"GT-only｜{data.get('state')}｜计划 clip：{data.get('selected_clips', 0)}｜arm 状态：{data.get('arm_status', {})}｜问题状态：{data.get('question_status', {})}｜只输入标注，不输入视频。"


def render_case(cid):
    if not cid:
        return None, '', '没有可用 clip。'
    clip = next((row for row in manifest() if row['clip_id'] == cid), None)
    if clip is None:
        return None, '', '所选 clip 不存在。'
    record = result(cid)
    generated = {row['question_id']: row for row in record.get('questions', [])}
    media = review_media(cid, clip)
    blocks = [f"**{clip['video_id']}** · {clip['workflow']} · {'ASR' if clip['has_asr'] else 'no ASR'} · {clip['duration_s']:.1f}s · 生成状态：`{record.get('status', 'queued')}`"]
    case_plan = plan(cid)
    questions = case_plan.get('questions', [])
    if not questions:
        blocks.append('题目计划尚未生成。')
    for index, question in enumerate(questions, 1):
        row = generated.get(question['question_id'])
        answer = row.get('answer', '尚未生成') if row else '尚未生成'
        status = row.get('status', 'queued') if row else 'queued'
        review = row.get('automatic_review', {}) if row else {}
        reason = review.get('reason', '')
        blocks.append(f"### {index}. {KINDS.get(question['kind'], question['kind'])}\n\n**Q:** {question['question']}\n\n**A:** {answer}\n\n状态：`{status}`" + (f" · 自动复核：{review.get('verdict')}（{reason}）" if review else ''))
    offset = len(questions)
    for index, question in enumerate(case_plan.get('mcq', []), offset + 1):
        options = '；'.join(f"{o['id']}. {o['name']}：{o['definition']}" for o in question.get('options', []))
        correct = ', '.join(question.get('correct_option_ids', [])) or '无'
        blocks.append(f"### {index}. 固定 GT 多选：异常类型\n\n**Q:** {question['question']}\n\n**选项:** {options}\n\n**GT答案:** `{correct}`\n\n状态：`deterministic_gt`（模型未参与出题）")
    return media, '\n\n'.join(blocks), progress()


def refresh(cid):
    values = choices()
    ids = [value for _, value in values]
    if cid not in ids:
        cid = ids[0] if ids else None
    media, qa, status = render_case(cid)
    return gr.update(choices=values, value=cid), media, status, qa


def build_app():
    with gr.Blocks() as app:
        gr.Markdown('# 最新 GT-only QA 生成结果\n这里只显示最新的 annotation-only A 方案：每个 clip 的全部开放式问题和答案按顺序列出。模型输入只有 GT 标注与题目计划，不输入视频。')
        status = gr.Markdown(progress())
        case = gr.Dropdown(choices(), label='Clip')
        reload = gr.Button('刷新生成结果')
        video = gr.Video(label='对应 clip（仅用于人工审核；不作为 GT-only 模型输入）', autoplay=False, interactive=False)
        qa = gr.Markdown()
        app.load(refresh, [case], [case, video, status, qa])
        reload.click(refresh, [case], [case, video, status, qa], api_name='refresh_gt_only')
        case.change(lambda cid: render_case(cid), [case], [video, qa, status], api_name='load_gt_only_clip')
        gr.Timer(15).tick(progress, outputs=status, api_name='gt_only_progress')
    return app


if __name__ == '__main__':
    build_app().queue(default_concurrency_limit=2).launch(server_name='0.0.0.0', server_port=7863, share=False, show_error=True)
