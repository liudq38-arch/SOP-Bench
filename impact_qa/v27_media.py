import hashlib
import math
import subprocess
from pathlib import Path

import av

from impact_qa.common import FFMPEG, ROOT, fingerprint, read_json, save_json
from impact_qa.v26_data import CONFIG, FOLDER
from impact_qa.v26_media import profile


def _valid_presentation_indexes(indexes, source_count):
    return bool(indexes) and all(0 <= index < source_count for index in indexes) and all(a < b for a, b in zip(indexes, indexes[1:]))


def _add_frame(selected, index, reason, start, end):
    index = min(end - 1, max(start, int(index)))
    selected.setdefault(index, set()).add(reason)


def select_source_frames(trial, clip, max_frames):
    start, end = clip['start_frame'], clip['end_frame_exclusive']
    errors = [e for e in trial['errors'] if e['duration_s'] >= CONFIG.get('long_anomaly_min_seconds', 5.0) and start <= e['start_frame'] < e['end_frame_exclusive'] <= end]
    errors.sort(key=lambda e: (-e['duration_s'], e['start_frame'], e['event_id']))
    selected = {}

    for error in errors:
        midpoint = (error['start_frame'] + error['end_frame_exclusive'] - 1) // 2
        _add_frame(selected, midpoint, 'atr_center:' + error['event_id'], start, end)
        if len(selected) >= max_frames:
            break

    for error in errors:
        if len(selected) >= max_frames:
            break
        first = error['start_frame'] + max(1, round((error['end_frame_exclusive'] - error['start_frame']) * 0.2))
        last = error['end_frame_exclusive'] - 1 - max(1, round((error['end_frame_exclusive'] - error['start_frame']) * 0.2))
        _add_frame(selected, first, 'atr_start:' + error['event_id'], start, end)
        if len(selected) < max_frames:
            _add_frame(selected, last, 'atr_end:' + error['event_id'], start, end)

    base_count = min(16, max_frames)
    for i in range(base_count):
        if len(selected) >= max_frames:
            break
        _add_frame(selected, start + round((end - start - 1) * i / max(1, base_count - 1)), 'uniform_context', start, end)

    actions = [e for e in trial['events'] if e['action'] != 'null' and e['start_frame'] < end and e['end_frame_exclusive'] > start]
    for event in actions:
        if len(selected) >= max_frames:
            break
        midpoint = (max(start, event['start_frame']) + min(end, event['end_frame_exclusive']) - 1) // 2
        _add_frame(selected, midpoint, 'tasb_action:' + event['event_id'], start, end)

    for i in range(max_frames):
        if len(selected) >= max_frames:
            break
        _add_frame(selected, start + round((end - start - 1) * i / max(1, max_frames - 1)), 'uniform_fill', start, end)

    indexes = sorted(selected)
    if not indexes:
        raise ValueError('v27_media:no_selected_frames:' + clip['clip_id'])
    while len(indexes) < 3:
        indexes.append(indexes[-1])
    return indexes, {str(i): sorted(selected[i]) for i in indexes}, errors


def _profile(trial):
    path = Path(trial['source_video'])
    stat = {'size': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns}
    key = fingerprint([str(path), stat])
    roots = [FOLDER]
    if CONFIG.get('reuse_media_root'):
        roots.append(ROOT / CONFIG['reuse_media_root'])
    for root in roots:
        cached = root / 'profiles' / (key + '.json')
        if cached.exists():
            value = read_json(cached)
            if value.get('source_video') != str(path) or value.get('stat') != stat:
                raise ValueError('v27_media:profile_source_changed:' + trial['video_id'])
            return value
    return profile(trial)


def _cached_media(cached, shared_root, key, clip_id, prof, clip, indexes):
    paths = [cached] if cached.exists() else []
    if shared_root and shared_root.is_dir():
        direct = shared_root / (clip_id + '.json')
        paths.extend([direct] if direct.exists() else [])
        paths.extend(path for path in shared_root.glob('*.json') if path != direct)
    for path in paths:
        value = read_json(path)
        media_path = Path(value['path'])
        exact = value.get('preparation_key') == key
        equivalent = (
            value.get('source_stat') == prof['stat']
            and value.get('source_interval_frames') == [clip['start_frame'], clip['end_frame_exclusive']]
            and [frame['source_frame_index'] for frame in value.get('sampled_frames', [])] == indexes
            and value.get('actual_sample_count') == len(indexes)
        )
        if (exact or equivalent) and media_path.exists() and hashlib.sha256(media_path.read_bytes()).hexdigest() == value['sha256']:
            value['preparation_key'] = key
            value['clip_id'] = clip_id
            save_json(cached, value)
            return value
        if path == cached:
            raise ValueError('v27_media:changed_cached_clip:' + clip_id)
    return None


def _encoded_pts(path):
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        return [float(frame.pts * frame.time_base) for frame in container.decode(stream)]


def prepare_media(trial, clip):
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
    from vllm.multimodal.media.image import ImageMediaIO
    from vllm.multimodal.media.video import VideoMediaIO

    prof = _profile(trial)
    indexes, reasons, errors = select_source_frames(trial, clip, CONFIG['video_max_frames'])
    key = fingerprint([prof['stat'], clip, indexes, CONFIG['video_width'], CONFIG['video_fps'], CONFIG['video_max_frames'], CONFIG['video_pixel_budget']])
    cached = FOLDER / 'media_manifests' / (clip['clip_id'] + '.json')
    shared_root = ROOT / CONFIG['reuse_media_root'] / 'media_manifests' if CONFIG.get('reuse_media_root') else None
    cached_value = _cached_media(cached, shared_root, key, clip['clip_id'], prof, clip, indexes)
    if cached_value:
        return cached_value

    dest = FOLDER / 'media' / (clip['clip_id'] + '.mp4')
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected_pts = [i / CONFIG['video_fps'] for i in range(len(indexes))]
    if dest.exists():
        try:
            existing_pts = _encoded_pts(dest)
        except Exception:
            existing_pts = []
        if len(existing_pts) != len(expected_pts) or max((abs(a - b) for a, b in zip(existing_pts, expected_pts)), default=0) > 0.002:
            dest.unlink()
    if not dest.exists():
        unique_indexes = sorted(set(indexes))
        expression = '+'.join(f'eq(n\\,{i})' for i in unique_indexes)
        tmp = dest.with_suffix('.tmp.mp4')
        padding_frames = len(indexes) - len(unique_indexes)
        padding = f',tpad=stop_mode=clone:stop={padding_frames}' if padding_frames else ''
        video_filter = f"select='{expression}'{padding},setpts=N/({CONFIG['video_fps']}*TB),scale={CONFIG['video_width']}:-2"
        command = [FFMPEG, '-nostdin', '-v', 'error', '-threads', '2', '-i', trial['source_video'], '-vf', video_filter, '-frames:v', str(len(indexes)), '-an', '-r', str(CONFIG['video_fps']), '-fps_mode', 'cfr', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(tmp)]
        subprocess.run(command, check=True, capture_output=True, timeout=600)
        tmp.replace(dest)

    encoded_pts = _encoded_pts(dest)
    if len(encoded_pts) != len(indexes) or max(abs(a - b) for a, b in zip(encoded_pts, expected_pts)) > 0.002:
        raise ValueError('v27_media:encoded_pts_or_count:' + clip['clip_id'])

    io = {'video_backend': 'opencv', 'fps': CONFIG['video_fps'], 'num_frames': CONFIG['video_max_frames']}
    images, metadata = VideoMediaIO(ImageMediaIO(), **io).load_file(dest)
    presentation_indexes = [int(i) for i in metadata['frames_indices']]
    if len(images) != len(presentation_indexes) or not _valid_presentation_indexes(presentation_indexes, len(indexes)):
        raise ValueError('v27_media:sampled_frame_mapping:' + clip['clip_id'])

    start_pts = prof['pts'][clip['start_frame']]
    frames = []
    for sample_index in presentation_indexes:
        source_index = indexes[sample_index]
        source_pts = prof['pts'][source_index]
        frames.append({
            'frame_id': f'f{source_index:07d}',
            'source_frame_index': source_index,
            'source_pts_s': source_pts,
            'local_pts_s': source_pts - start_pts,
            'sample_index': sample_index,
            'sample_reasons': reasons[str(source_index)],
        })

    height, width = smart_resize(len(images), *images.shape[1:3], min_pixels=4096, max_pixels=CONFIG['video_pixel_budget'])
    event_counts = {}
    for event in trial['events']:
        if event['action'] != 'null' and event['start_frame'] < clip['end_frame_exclusive'] and event['end_frame_exclusive'] > clip['start_frame']:
            event_counts[event['event_id']] = sum(event['start_frame'] <= f['source_frame_index'] < event['end_frame_exclusive'] for f in frames)
    anomaly_counts = {error['event_id']: sum(error['start_frame'] <= f['source_frame_index'] < error['end_frame_exclusive'] for f in frames) for error in errors}
    value = {
        'preparation_key': key,
        'clip_id': clip['clip_id'],
        'path': str(dest),
        'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
        'source_stat': prof['stat'],
        'source_interval_frames': [clip['start_frame'], clip['end_frame_exclusive']],
        'source_start_pts_s': start_pts,
        'source_end_pts_s': prof['pts'][clip['end_frame_exclusive']] if clip['end_frame_exclusive'] < len(prof['pts']) else prof['pts'][-1] + prof['last_frame_duration_s'],
        'encoded_frames': len(encoded_pts),
        'sampled_frames': frames,
        'actual_sample_count': len(frames),
        'sample_max_gap_s': max((y['local_pts_s'] - x['local_pts_s'] for x, y in zip(frames, frames[1:])), default=0),
        'event_sample_counts': event_counts,
        'events_without_sample': [k for k, v in event_counts.items() if not v],
        'anomaly_sample_counts': anomaly_counts,
        'qualifying_anomalies_without_sample': [k for k, v in anomaly_counts.items() if not v],
        'media_io_kwargs': {'video': io},
        'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': CONFIG['video_pixel_budget']}},
        'processor_shape': [height, width],
        'estimated_visual_tokens': math.ceil(len(images) / 2) * (height // 32) * (width // 32),
        'annotation_clock_max_error_s': prof['annotation_clock_max_error_s'],
        'whole_clip_temporal_coverage': True,
        'sampling_strategy': 'ATR anomaly centers and boundaries, TAS-B action centers, then uniform context; frame IDs map to source timestamps',
        'temporal_padding_frames': len(indexes) - len(set(indexes)),
        'history_used': False,
    }
    if value['qualifying_anomalies_without_sample']:
        raise ValueError('v27_media:uncovered_qualifying_anomaly:' + ','.join(value['qualifying_anomalies_without_sample']))
    save_json(cached, value)
    return value
