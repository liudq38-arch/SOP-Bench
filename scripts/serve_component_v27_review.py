import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ['IMPACT_V26_CONFIG'] = os.environ.get('IMPACT_V27_REVIEW_CONFIG', 'configs/impact_qa/component_v27_video_gt_r6.json')
sys.path.insert(0, str(ROOT))

import gradio as gr

from impact_qa.common import FFMPEG, read_json, read_jsonl
from impact_qa.v26_data import FOLDER
from impact_qa.mcq_native_page import NATIVE_FOLDER, build_native_tab, refresh as refresh_native
from impact_qa.front_mcq_page import build_tab as build_front_mcq_tab


INCREMENTAL_ROOT = Path(os.environ.get(
    'IMPACT_V27_INCREMENTAL_ROOT',
    'outputs/impact_qa/component_v27_video_gt_r7p2_incremental_r1',
))


KINDS = {
    'overall_operation': '整体操作',
    'detailed_operation': '工具与部件的详细动作',
    'step_completion': '组件完成性',
    'observed_order': '操作顺序',
    'operation_duration': '操作时长',
    'mcq_anomaly_clip': '固定 GT 异常类型选择题',
}


def manifest():
    path = FOLDER / 'manifest.jsonl'
    return read_jsonl(path) if path.exists() else []


def result(clip_id):
    path = FOLDER / 'results' / (clip_id + '_V.json')
    value = read_json(path) if path.exists() else {'status': 'queued', 'questions': []}
    merged = INCREMENTAL_ROOT / 'merged_questions.jsonl'
    if merged.exists():
        additions = [row for row in read_jsonl(merged) if row.get('clip_id') == clip_id and row.get('parent_output_root')]
        parent_ids = {row.get('question_id') for row in value.get('questions', [])}
        value['questions'] = value.get('questions', []) + [row for row in additions if row.get('question_id') not in parent_ids]
    return value


def choices():
    values = []
    for clip in manifest():
        record = result(clip['clip_id'])
        label = f"[{record.get('status', 'queued')}] {clip['workflow']} | {'有ASR' if clip['has_asr'] else '无ASR'} | {clip['duration_s']:.1f}s | {clip['video_id']} | {clip['clip_id'][-8:]}"
        values.append((label, clip['clip_id']))
    durations = {clip['clip_id']: clip['duration_s'] for clip in manifest()}
    from collections import defaultdict, deque
    buckets = defaultdict(deque)
    for item in sorted(values, key=lambda item: item[1]):
        seconds = durations[item[1]]
        buckets[0 if seconds >= 120 else 1 if seconds >= 60 else 2 if seconds >= 20 else 3].append(item)
    values = []
    while any(buckets.values()):
        for key in [0, 1, 2, 3]:
            if buckets[key]:
                values.append(buckets[key].popleft())
    return values


def progress():
    path = FOLDER / 'progress.json'
    if not path.exists():
        return 'video+GT 冒烟任务已准备，等待生成结果。'
    value = read_json(path)
    incremental_path = INCREMENTAL_ROOT / 'progress.json'
    incremental = read_json(incremental_path) if incremental_path.exists() else {}
    extra = f"｜增量：{incremental.get('supplemental_question_count', 0)}（保留{incremental.get('supplemental_question_status', {}).get('candidate', 0)}，hold{incremental.get('supplemental_question_status', {}).get('held', 0)}）" if incremental else ''
    return f"video+GT｜{value.get('state')}｜已处理：{value.get('resolved_clips', 0)}/{value.get('selected_clips', 0)}｜待处理：{value.get('pending_clip_count', 0)}｜状态：{value.get('arm_status', {})}｜问题：{value.get('question_status', {})}{extra}｜人工审核：待进行｜正式发布：关闭"


def review_media(clip):
    clip_id = clip['clip_id']
    media_dir = FOLDER / 'review_media'
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / (clip_id + '.mp4')
    if target.exists() and target.stat().st_size > 0:
        return str(target)
    source = Path(clip['source_video'])
    if not source.exists():
        value_path = FOLDER / 'inputs' / (clip_id + '.json')
        if value_path.exists():
            sampled = read_json(value_path).get('media', {}).get('path')
            if sampled and Path(sampled).exists():
                return sampled
        return None
    ffmpeg = shutil.which('ffmpeg') or FFMPEG
    tmp = target.with_suffix('.tmp.mp4')
    start = float(clip['source_start_s'])
    duration = float(clip['source_end_s']) - start
    command = [
        ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
        '-ss', f'{start:.6f}', '-i', str(source), '-t', f'{duration:.6f}',
        '-an', '-vf', 'fps=5,scale=960:-2', '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(tmp),
    ]
    try:
        subprocess.run(command, check=True, timeout=900, capture_output=True)
        tmp.replace(target)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        tmp.unlink(missing_ok=True)
        value_path = FOLDER / 'inputs' / (clip_id + '.json')
        if value_path.exists():
            sampled = read_json(value_path).get('media', {}).get('path')
            if sampled and Path(sampled).exists():
                return sampled
        return None
    return str(target) if target.exists() else None


def render_case(clip_id):
    if not clip_id:
        return None, '没有可用 clip。', progress()
    clip = next((row for row in manifest() if row['clip_id'] == clip_id), None)
    if clip is None:
        return None, '所选 clip 不存在。', progress()
    record = result(clip_id)
    media = review_media(clip) if record.get('questions') else None
    blocks = [
        f"**{clip['video_id']}** · {clip['workflow']} · {'ASR' if clip['has_asr'] else 'no ASR'} · {clip['duration_s']:.1f}s",
        f"原片区间：{clip['source_start_s']:.2f}s–{clip['source_end_s']:.2f}s；生成状态：`{record.get('status', 'queued')}`。",
    ]
    questions = record.get('questions', [])
    if not questions:
        blocks.append('当前 clip 尚无已生成的问题。')
    for index, question in enumerate(questions, 1):
        answer = question.get('answer', '尚未生成')
        kind = KINDS.get(question.get('kind'), question.get('kind', 'QA'))
        blocks.append(f"### {index}. {kind}\n\n**Q:** {question.get('question', '')}\n\n**A:** {answer}")
        if question.get('options'):
            options = '；'.join(f"{item['id']}. {item['name']}：{item.get('definition', '')}" for item in question['options'])
            blocks.append(f"**选项:** {options}\n\n**GT答案:** {', '.join(question.get('correct_option_ids', [])) or '无'}")
        if question.get('abnormal_segments'):
            segments = question['abnormal_segments']
            detail = '\n'.join(f"- {item['start_s']:.2f}s–{item['end_s']:.2f}s：{item['observed_description']}（GT 类型：{', '.join(item['anomaly_types'])}；证据帧：{', '.join(item['evidence_frame_ids'])}）" for item in segments)
            blocks.append('**异常区间与视觉证据**\n\n' + detail)
        review = question.get('automatic_review', {})
        if review:
            blocks.append(f"自动复核：`{review.get('verdict')}` · {review.get('reason', '')}；人工审核：`{question.get('human_review', 'unreviewed')}`")
        elif question.get('human_review'):
            blocks.append(f"人工审核：`{question.get('human_review')}`")
    return media, '\n\n'.join(blocks), progress()


def refresh(clip_id):
    values = choices()
    ids = [value for _, value in values]
    if clip_id not in ids:
        clip_id = ids[0] if ids else None
    media, qa, status = render_case(clip_id)
    return gr.update(choices=values, value=clip_id), media, status, qa


def build_app():
    with gr.Blocks(css='.gradio-container {max-width:1500px!important} .review-intro {padding:18px 22px;border-radius:14px;background:#eef3f8;color:#20374c;margin-bottom:12px;display:flex;justify-content:space-between;gap:18px} .review-intro b {font-size:22px} .review-intro span {font-size:14px;align-self:center} .review-card {border:1px solid #e0e7ef;border-radius:14px;padding:16px!important} #front-review-pass {min-height:48px} #front-review-video {border-radius:12px;overflow:hidden}') as app:
        with gr.Tab('异常类型MCQ（1,977题）'):
            build_front_mcq_tab(app)
        with gr.Tab('历史开放式QA（2,309题 / 648 clip）'):
            gr.Markdown('这是此前生成的独立开放式题库，不包含在最新1,977道异常类型MCQ中。问题包括整体操作、工具与部件过程、组件完成性、操作顺序和时长。')
            status = gr.Markdown(progress())
            case = gr.Dropdown(choices(), label='Clip')
            reload = gr.Button('刷新生成结果')
            video = gr.Video(label='对应原片 clip', autoplay=False, interactive=False)
            qa = gr.Markdown()
            app.load(refresh, [case], [case, video, status, qa])
            reload.click(refresh, [case], [case, video, status, qa], api_name='refresh_v27')
            case.change(lambda cid: render_case(cid), [case], [video, qa, status], api_name='load_v27_clip')
            gr.Timer(15).tick(progress, outputs=status, api_name='v27_progress')
        with gr.Tab('MCQ 视角对照测试'):
            native_case,native_original,native_sampled,native_qa=build_native_tab()
            app.load(refresh_native,[native_case],[native_case,native_original,native_sampled,native_qa])
    return app


if __name__ == '__main__':
    allowed = [str(FOLDER), str(NATIVE_FOLDER.parent), str(ROOT/'outputs/impact_qa/front_mcq_expansion_v1'), str(Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos'))]
    frontend_js='() => {'+''.join('('+ (ROOT/'impact_qa'/name).read_text()+')();' for name in ['front_mcq_timeline.js','front_mcq_guidance.js'])+'}'
    build_app().queue(default_concurrency_limit=2).launch(server_name='0.0.0.0', server_port=7863, share=False, show_error=True, allowed_paths=allowed, css_paths=[ROOT/'impact_qa/front_mcq_timeline.css',ROOT/'impact_qa/front_mcq_guidance.css'], js=frontend_js)
