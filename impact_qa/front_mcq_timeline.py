from html import escape
import math


def timeline_html(question,group):
    start,end=map(float,question['scope']['playback_interval_s'])
    duration=float(group['duration_s'])
    if not all(math.isfinite(v) for v in [start,end,duration]) or not 0<=start<end<=duration+1e-6:
        raise ValueError('front_mcq_timeline:invalid_interval')
    hand='左手' if question['scope']['hand']=='left' else '右手'
    return f'''<section class="mcq-timeline" data-question="{escape(question['question_id'],quote=True)}" data-group="{escape(group['group_id'],quote=True)}" data-start="{start:.8f}" data-end="{end:.8f}" data-duration="{duration:.8f}" data-state="loading">
<div class="mcq-interval-heading"><strong>本题判断区间 <span>{start:.2f}–{end:.2f} 秒</span> · {hand}</strong><span class="mcq-phase" aria-live="polite">等待视频</span></div>
<div class="mcq-seekbar"><div class="mcq-range" style="left:{start/duration*100:.6f}%;width:{(end-start)/duration*100:.6f}%"></div><div class="mcq-playhead"></div><input class="mcq-slider" type="range" min="0" max="{duration:.8f}" step="0.01" value="0" aria-label="视频进度，标记区域是本题判断区间" /></div>
<div class="mcq-clock"><span>0秒</span><span class="mcq-current-time">当前 0.00秒 / {duration:.2f}秒</span><span>{duration:.2f}秒</span></div>
<div class="mcq-timeline-hint">彩色区域为本题待判断片段，可点击进度条定位；区间外为上下文。</div>
</section>'''
