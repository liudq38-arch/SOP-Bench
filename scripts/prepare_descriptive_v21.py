import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import FFMPEG, OUT, read_jsonl, save_json, save_jsonl
from impact_qa.descriptive_v21 import FOLDER, digest


PAIRS = ['atr_17fd15858f5679ef', 'atr_b5048432118ffc77', 'atr_403f880f747b22eb']


def prepare(case):
    from vllm.multimodal.media.image import ImageMediaIO
    from vllm.multimodal.media.video import VideoMediaIO
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize

    destination = FOLDER / 'cases' / (case['case_id'] + '.json')
    if destination.exists():
        return json.loads(destination.read_text())
    source = Path(case['source_video'])
    a, b = case['source_interval_inclusive']
    selected = []
    first_pts = None
    folder = FOLDER / 'frames' / case['case_id']
    folder.mkdir(parents=True, exist_ok=True)
    with av.open(source) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        for index, frame in enumerate(container.decode(stream)):
            if index == 0:
                first_pts = float(frame.pts * frame.time_base)
            if index < a:
                continue
            if index > b:
                break
            image = frame.to_image()
            image.thumbnail((960, 960))
            path = folder / f'f{index:07d}.jpg'
            if not path.exists():
                image.save(path, quality=92)
            selected.append({'frame_id': f'f{index:07d}', 'source_frame_index': index, 'source_pts_s': float(frame.pts * frame.time_base), 'pts': frame.pts, 'time_base': str(frame.time_base), 'path': str(path), 'width': image.width, 'height': image.height, 'sha256': digest(path)})
    if len(selected) != b - a + 1 or any(y['source_pts_s'] <= x['source_pts_s'] for x, y in zip(selected, selected[1:])):
        raise ValueError(f'prepare_v21:native_frame_or_pts:{case["case_id"]}')
    chunks = []
    start = 0
    while start < len(selected):
        end = start + 1
        while end < len(selected) and selected[end]['source_pts_s'] - selected[start]['source_pts_s'] < 2.0:
            end += 1
        chunks.append((start, end))
        start = end
    clips = []
    for number, (start, end) in enumerate(chunks):
        core = selected[start:end]
        left, right = start, end
        while left > 0 and core[0]['source_pts_s'] - selected[left - 1]['source_pts_s'] <= 0.25:
            left -= 1
        while right < len(selected) and selected[right]['source_pts_s'] - core[-1]['source_pts_s'] <= 0.25:
            right += 1
        media_frames = selected[left:right]
        clip_id = f'{case["case_id"]}_c{number:02d}'
        path = FOLDER / 'clips' / (clip_id + '.mp4')
        path.parent.mkdir(parents=True, exist_ok=True)
        lo, hi = media_frames[0]['source_frame_index'], media_frames[-1]['source_frame_index']
        if not path.exists():
            tmp = path.with_suffix('.tmp.mp4')
            subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', str(source), '-vf', f'select=between(n\\,{lo}\\,{hi}),setpts=PTS-STARTPTS,scale=960:-2', '-an', '-fps_mode', 'vfr', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(tmp)], check=True, capture_output=True, timeout=240)
            tmp.replace(path)
        with av.open(path) as media:
            decoded = list(media.decode(video=0))
            local_pts = [float(f.pts * f.time_base) for f in decoded]
        if len(decoded) != len(media_frames):
            raise ValueError('prepare_v21:clip_frame_mapping')
        timing_error = max(abs(t - (f['source_pts_s'] - media_frames[0]['source_pts_s'])) for t, f in zip(local_pts, media_frames))
        if timing_error > 0.002:
            raise ValueError(f'prepare_v21:transcode_pts:{timing_error}')
        io = {'video_backend': 'opencv', 'fps': 8, 'num_frames': 64}
        images, meta = VideoMediaIO(ImageMediaIO(), **io).load_file(path)
        if len(images) < 4:
            io.update(fps=-1, num_frames=4)
            images, meta = VideoMediaIO(ImageMediaIO(), **io).load_file(path)
        h, w = images.shape[1:3]
        nh, nw = smart_resize(len(images), h, w, min_pixels=4096, max_pixels=16777216)
        sampled = [media_frames[i] for i in meta['frames_indices']]
        video = {'path': str(path), 'sha256': digest(path), 'media_io_kwargs': {'video': io}, 'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': 16777216}}, 'decoded_frames': len(images), 'estimated_visual_tokens': math.ceil(len(images) / 2) * (nh // 32) * (nw // 32), 'sampled_frames': sampled, 'processor_shape': [nh, nw], 'max_pts_mapping_error_s': timing_error}
        clips.append({'clip_id': clip_id, 'core_frames': core, 'media_frames': media_frames, 'video': video})
    record = {'case': case, 'source_sha256': digest(source), 'first_source_pts_s': first_pts, 'frames': selected, 'clips': clips, 'native_target_frame_count': len(selected), 'context_included': False, 'outside_target_behavior_not_answerable': True}
    save_json(destination, record)
    print(json.dumps({'case_id': case['case_id'], 'native_frames': len(selected), 'clips': len(clips)}), flush=True)
    return record


def main():
    cases = [c for c in read_jsonl(OUT / 'atr_v19/cases.jsonl') if c['pair_id'] in PAIRS]
    cases.sort(key=lambda c: (PAIRS.index(c['pair_id']), c['view']))
    with ThreadPoolExecutor(max_workers=3) as executor:
        records = list(executor.map(prepare, cases))
    save_jsonl(FOLDER / 'cases.jsonl', records)
    save_jsonl(FOLDER / 'first10_frames.jsonl', records[0]['frames'][:10])
    save_json(FOLDER / 'precheck.json', {'cases': len(records), 'native_frames': sum(len(r['frames']) for r in records), 'clips': sum(len(r['clips']) for r in records), 'all_inclusive_intervals_covered': True, 'max_clip_pts_mapping_error_s': max(c['video']['max_pts_mapping_error_s'] for r in records for c in r['clips']), 'context_included': False})


if __name__ == '__main__':
    main()
