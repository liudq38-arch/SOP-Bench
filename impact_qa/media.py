import concurrent.futures
import json
import math
import subprocess
from pathlib import Path

from .common import FFMPEG, OUT, fingerprint, read_json, save_json


def prepare_evidence(event, frames=24, width=672, refinement=False, targeted=False):
    variant = 'refined' if refinement else ('overview_targeted' if targeted else 'overview')
    folder = OUT / 'evidence' / event['event_id'] / variant
    manifest = folder / 'manifest.json'
    config = {'event_hash': event['record_hash'], 'frames': frames, 'width': width, 'refinement': refinement, 'sampler_version': 'targeted_v1' if targeted else '1'}
    key = fingerprint(config)
    reuse_frames = False
    if manifest.exists():
        existing = read_json(manifest)
        if existing['cache_key'] == key:
            if all(Path(x['path']).is_file() and Path(x['path']).stat().st_size for x in existing['images']):
                return existing
            reuse_frames = True
    folder.mkdir(parents=True, exist_ok=True)
    start = event['start_s'] if refinement else event['context_start_s']
    end = event['end_s_exclusive'] if refinement else event['context_end_s']
    duration = end - start
    rate = min(8 if refinement else 2, frames / duration)
    count = min(frames, max(2, math.ceil(duration * rate)))
    times = [start + (i + .5) * duration / count for i in range(count)]
    if targeted and not refinement:
        target_start, target_end = event['start_s'], event['end_s_exclusive']
        target_count = min(frames - 8, max(8, math.ceil((target_end - target_start) * 2)))
        before = [start + (i + .5) * (target_start - start) / 4 for i in range(4)] if target_start > start else []
        inside = [target_start + (i + .5) * (target_end - target_start) / target_count for i in range(target_count)]
        after = [target_end + (i + .5) * (end - target_end) / 4 for i in range(4)] if end > target_end else []
        times = before + inside + after
    def extract(pair):
        index, timestamp = pair
        output = folder / f'frame_{index:03d}.jpg'
        if not reuse_frames or not output.exists() or not output.stat().st_size:
            command = [FFMPEG, '-nostdin', '-v', 'error', '-threads', '1', '-ss', f'{timestamp:.6f}', '-i', event['video_path'], '-frames:v', '1', '-vf', f'scale={width}:-2', '-q:v', '3', '-y', str(output)]
            subprocess.run(command, check=True, capture_output=True)
        return {'evidence_id': f'{variant}_f{index:03d}', 'path': str(output), 'requested_time_s': timestamp, 'time_note': 'accurate seek to first decoded frame at/after requested time; precision limited to one source frame'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(extract, enumerate(times)))
    record = {'cache_key': key, 'config': config, 'event_id': event['event_id'], 'start_s': start, 'end_s': end, 'images': images, 'video_path': event['video_path'], 'refinement': refinement}
    save_json(manifest, record)
    return record


def create_review_clip(event):
    folder = OUT / 'review/clips'
    folder.mkdir(parents=True, exist_ok=True)
    clip = folder / (event['event_id'] + '.mp4')
    if not clip.exists():
        duration = event['context_end_s'] - event['context_start_s']
        subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-threads', '1', '-ss', str(event['context_start_s']), '-i', event['video_path'], '-t', str(duration), '-vf', 'scale=672:-2', '-an', '-c:v', 'libx264', '-threads', '1', '-preset', 'fast', '-crf', '24', '-movflags', '+faststart', '-y', str(clip)], check=True, capture_output=True)
    return clip


def prepare_focus_evidence(event):
    folder = OUT / 'evidence' / event['event_id'] / 'focus'
    manifest = folder / 'manifest.json'
    config = {'event_hash': event['record_hash'], 'sampler_version': 'focus_v1', 'target_frames': 12, 'full_width': 896, 'crop_width': 1024, 'crop_normalized_xywh': [.05, .25, .9, .75]}
    key = fingerprint(config)
    if manifest.exists():
        previous = read_json(manifest)
        if previous.get('cache_key') == key and all(Path(f['path']).is_file() for f in previous['images']):
            return previous
    folder.mkdir(parents=True, exist_ok=True)
    start, end = event['start_s'], event['end_s_exclusive']
    times = [start + (i + .5) * (end - start) / 12 for i in range(12)]
    jobs = [(i, False) for i in range(12)] + [(i, True) for i in [0, 4, 7, 11]]
    def extract(job):
        index, cropped = job
        evidence_id = f'focus_{"crop" if cropped else "full"}_{index:03d}'
        output = folder / (evidence_id + '.jpg')
        filtering = 'crop=iw*0.9:ih*0.75:iw*0.05:ih*0.25,scale=1024:-2' if cropped else 'scale=896:-2'
        subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-threads', '1', '-ss', f'{times[index]:.6f}', '-i', event['video_path'], '-frames:v', '1', '-vf', filtering, '-q:v', '2', '-y', str(output)], check=True, capture_output=True)
        return {'evidence_id': evidence_id, 'path': str(output), 'requested_time_s': times[index], 'time_scope': 'TARGET', 'view': 'enlarged lower-workspace crop; same instant as full frame' if cropped else 'full frame', 'crop_normalized_xywh': [.05, .25, .9, .75] if cropped else [0, 0, 1, 1], 'time_note': 'accurate seek; precision limited to one source frame'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(extract, jobs))
    record = {'cache_key': key, 'config': config, 'event_id': event['event_id'], 'start_s': start, 'end_s': end, 'images': images, 'video_path': event['video_path'], 'refinement': False}
    save_json(manifest, record)
    return record


def prepare_native_evidence(event):
    focused = prepare_focus_evidence(event)
    folder = OUT / 'target_clips'
    folder.mkdir(exist_ok=True)
    clip = folder / (event['event_id'] + '.mp4')
    if not clip.exists():
        subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-threads', '1', '-ss', str(event['start_s']), '-i', event['video_path'], '-t', str(event['annotation_duration_s']), '-vf', 'scale=1024:-2', '-an', '-c:v', 'libx264', '-threads', '1', '-preset', 'fast', '-crf', '20', '-y', str(clip)], check=True, capture_output=True)
    video = {'evidence_id': 'target_video', 'media_type': 'video', 'path': str(clip), 'requested_time_s': event['start_s'], 'source_start_s': event['start_s'], 'source_end_s': event['end_s_exclusive'], 'time_scope': 'TARGET', 'decoder_num_frames': 16, 'view': 'native target-only video; clip clock starts at 0', 'time_note': 'source time equals local clip time plus source_start_s; frame precision'}
    crops = [f for f in focused['images'] if 'crop' in f['evidence_id']]
    record = {'event_id': event['event_id'], 'images': [video] + crops, 'config': {'sampler_version': 'native_v1', 'media_io_kwargs': {'video': {'num_frames': 16, 'fps': -1}}, 'mm_processor_kwargs': {'num_frames': 16, 'do_sample_frames': False}, 'video_width': 1024, 'crop_count': 4, 'focus_cache_key': focused['cache_key']}}
    save_json(OUT / 'evidence' / event['event_id'] / 'native/manifest.json', record)
    return record
