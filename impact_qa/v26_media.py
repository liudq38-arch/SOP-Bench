import hashlib
import math
import subprocess
from pathlib import Path

import av

from impact_qa.common import FFMPEG, fingerprint, read_json, save_json
from impact_qa.v26_data import CONFIG, FOLDER


def profile(trial):
    path = Path(trial['source_video'])
    stat = {'size': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns}
    key = fingerprint([str(path), stat])
    cache = FOLDER / 'profiles' / (key + '.json')
    if cache.exists():
        return read_json(cache)
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        pts = [float(f.pts * f.time_base) for f in container.decode(stream)]
    if len(pts) != trial['frame_count'] or any(b <= a for a, b in zip(pts, pts[1:])):
        raise ValueError('v26_media:source_frame_pts:' + trial['video_id'])
    error = max(abs(t - i / trial['fps']) for i, t in enumerate(pts))
    if error > .002:
        raise ValueError('v26_media:non_cfr_annotation_clock:' + trial['video_id'])
    value = {'source_video': str(path), 'stat': stat, 'pts': pts, 'annotation_clock_max_error_s': error, 'last_frame_duration_s': 1 / trial['fps']}
    save_json(cache, value)
    return value


def prepare_media(trial, clip):
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
    from vllm.multimodal.media.image import ImageMediaIO
    from vllm.multimodal.media.video import VideoMediaIO

    prof = profile(trial)
    key = fingerprint([prof['stat'], clip, CONFIG['video_width'], CONFIG['video_fps'], CONFIG['video_max_frames'], CONFIG['video_pixel_budget']])
    cached = FOLDER / 'media_manifests' / (clip['clip_id'] + '.json')
    if cached.exists():
        value = read_json(cached)
        if value['preparation_key'] != key or hashlib.sha256(Path(value['path']).read_bytes()).hexdigest() != value['sha256']:
            raise ValueError('v26_media:changed_cached_clip:' + clip['clip_id'])
        return value
    dest = FOLDER / 'media' / (clip['clip_id'] + '.mp4')
    dest.parent.mkdir(parents=True, exist_ok=True)
    a, b = clip['start_frame'], clip['end_frame_exclusive']
    if not dest.exists():
        tmp = dest.with_suffix('.tmp.mp4')
        command = [FFMPEG, '-nostdin', '-v', 'error', '-threads', '2', '-i', trial['source_video'], '-vf', f"select=between(n\\,{a}\\,{b - 1}),setpts=PTS-STARTPTS,scale={CONFIG['video_width']}:-2", '-frames:v', str(b - a), '-an', '-fps_mode', 'vfr', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(tmp)]
        subprocess.run(command, check=True, capture_output=True, timeout=600)
        tmp.replace(dest)
    with av.open(str(dest)) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        local = [float(f.pts * f.time_base) for f in container.decode(stream)]
    expected = prof['pts'][a:b]
    if len(local) != len(expected) or max(abs(t - (p - expected[0])) for t, p in zip(local, expected)) > .002:
        raise ValueError('v26_media:encoded_pts_or_count:' + clip['clip_id'])
    io = {'video_backend': 'opencv', 'fps': CONFIG['video_fps'], 'num_frames': CONFIG['video_max_frames']}
    images, metadata = VideoMediaIO(ImageMediaIO(), **io).load_file(dest)
    indices = [int(i) for i in metadata['frames_indices']]
    if not indices or indices[0] != 0 or indices[-1] != b - a - 1 or not 1 <= len(indices) <= CONFIG['video_max_frames']:
        raise ValueError('v26_media:whole_clip_sampling:' + clip['clip_id'])
    height, width = smart_resize(len(images), *images.shape[1:3], min_pixels=4096, max_pixels=CONFIG['video_pixel_budget'])
    frames = [{'frame_id': f'f{a + i:07d}', 'source_frame_index': a + i, 'source_pts_s': prof['pts'][a + i], 'local_pts_s': local[i]} for i in indices]
    counts = {}
    for event in trial['events']:
        if event['action'] != 'null' and event['start_frame'] < b and event['end_frame_exclusive'] > a:
            counts[event['event_id']] = sum(event['start_frame'] <= f['source_frame_index'] < event['end_frame_exclusive'] for f in frames)
    value = {'preparation_key': key, 'clip_id': clip['clip_id'], 'path': str(dest), 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'source_stat': prof['stat'], 'source_interval_frames': [a, b], 'source_start_pts_s': expected[0], 'source_end_pts_s': prof['pts'][b] if b < len(prof['pts']) else prof['pts'][-1] + prof['last_frame_duration_s'], 'encoded_frames': len(local), 'sampled_frames': frames, 'actual_sample_count': len(frames), 'sample_max_gap_s': max((y['local_pts_s'] - x['local_pts_s'] for x, y in zip(frames, frames[1:])), default=0), 'event_sample_counts': counts, 'events_without_sample': [k for k, v in counts.items() if not v], 'media_io_kwargs': {'video': io}, 'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': CONFIG['video_pixel_budget']}}, 'processor_shape': [height, width], 'estimated_visual_tokens': math.ceil(len(images) / 2) * (height // 32) * (width // 32), 'annotation_clock_max_error_s': prof['annotation_clock_max_error_s'], 'whole_clip': True, 'history_used': False}
    save_json(cached, value)
    return value
