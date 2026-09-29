import hashlib
import math
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import ImageDraw

from impact_qa.common import fingerprint, read_json, save_json


def prepare_window_media(unit, window, config, folder):
    clip = unit['clip']
    source = Path(clip['source_video'])
    stat = source.stat()
    key = fingerprint([str(source), stat.st_size, stat.st_mtime_ns, window['start_frame'], window['end_frame_exclusive'], config['sample_fps'], config['video_width'], config['video_pixel_budget'], clip['start_frame'], config.get('detail_crop'), config.get('target_overlay',False), [e['event_id'] for e in window['events']] if config.get('target_overlay') else [], 'labelled_v1'])
    cache = folder / 'media_manifests' / (key + '.json')
    if cache.exists():
        value = read_json(cache)
        if hashlib.sha256(Path(value['path']).read_bytes()).hexdigest() != value['sha256']:
            raise ValueError('mcq_grouped_media:cache_hash:' + key)
        return value
    fps = clip['fps']
    a, b = window['start_frame'], window['end_frame_exclusive']
    count = max(4, math.ceil((b-a) / fps * config['sample_fps']))
    count += count % 2
    indexes = sorted(set(np.rint(np.linspace(a, b-1, count)).astype(int).tolist()))
    wanted = set(indexes)
    images, mapped = [], []
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        container.seek(max(0, int((a / fps) / stream.time_base)), stream=stream, backward=True)
        for frame in container.decode(stream):
            t = float(frame.pts * frame.time_base)
            idx = round(t * fps)
            if idx >= b:
                break
            if idx not in wanted:
                continue
            if abs(t - idx/fps) > 0.002:
                raise ValueError('mcq_grouped_media:non_cfr_clock:' + str(source))
            original = frame.to_image()
            image = original
            if config.get('detail_crop'):
                x1,y1,x2,y2=config['detail_crop']
                image=original.crop((round(x1*original.width),round(y1*original.height),round(x2*original.width),round(y2*original.height)))
            width = config['video_width']
            height = round(image.height * width / image.width / 2) * 2
            image = image.resize((width, height))
            if config.get('detail_crop'):
                inset_width=round(width*0.25)
                inset=original.resize((inset_width,round(original.height*inset_width/original.width)))
                image.paste(inset,(width-inset_width,22))
                ImageDraw.Draw(image).rectangle((width-inset_width,22,width-1,22+inset.height),outline='yellow',width=2)
            local = (idx-clip['start_frame'])/fps
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, width, 20), fill='black')
            draw.text((5, 4), f'f{idx:07d}  parent clip {local:.3f}s', fill='white')
            if config.get('target_overlay'):
                hands=sorted({e['hand'] for e in window['events'] if e['start_frame'] <= idx < e['end_frame_exclusive']})
                draw.rectangle((0,height-22,width,height),fill='black')
                draw.text((5,height-17),'TARGET: '+', '.join(hands) if hands else 'CONTEXT ONLY',fill='yellow' if hands else 'white')
            images.append(image)
            mapped.append({'frame_id': f'f{idx:07d}', 'source_frame_index': idx, 'source_pts_s': t, 'local_pts_s': local, 'encoded_s': (len(images)-1)/config['sample_fps']})
    if [r['source_frame_index'] for r in mapped] != indexes:
        raise ValueError('mcq_grouped_media:source_frame_mapping:' + key)
    dest = folder / 'media' / (key + '.mp4')
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix('.tmp.mp4')
    with av.open(str(tmp), 'w') as out:
        stream = out.add_stream('libx264', rate=config['sample_fps'])
        stream.width, stream.height = images[0].size
        stream.pix_fmt = 'yuv420p'
        stream.options = {'crf': '20', 'preset': 'veryfast'}
        for i, image in enumerate(images):
            frame = av.VideoFrame.from_image(image)
            frame.pts = i
            frame.time_base = Fraction(1, config['sample_fps'])
            for packet in stream.encode(frame):
                out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    tmp.replace(dest)
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
    from vllm.multimodal.media.image import ImageMediaIO
    from vllm.multimodal.media.video import VideoMediaIO
    io = {'video_backend': 'opencv', 'fps': config['sample_fps'], 'num_frames': len(mapped)}
    frames, metadata = VideoMediaIO(ImageMediaIO(), **io).load_file(dest)
    if list(metadata['frames_indices']) != list(range(len(mapped))):
        raise ValueError('mcq_grouped_media:server_decoder_mapping:' + key)
    height, width = smart_resize(len(frames), *frames.shape[1:3], min_pixels=4096, max_pixels=config['video_pixel_budget'])
    value = {'path': str(dest.resolve()), 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'source_video': str(source), 'source_interval_frames': [a,b], 'sampled_frames': mapped, 'actual_sample_count': len(mapped), 'sample_max_gap_s': max(np.diff([r['source_pts_s'] for r in mapped]), default=0), 'media_io_kwargs': {'video': io}, 'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': config['video_pixel_budget']}}, 'estimated_visual_tokens': math.ceil(len(frames)/2)*(height//32)*(width//32), 'sampling_strategy': 'uniform_local_window_with_source_frame_labels', 'sample_fps':config['sample_fps'], 'detail_crop':config.get('detail_crop'), 'full_frame_inset':bool(config.get('detail_crop')), 'preparation_key': key}
    save_json(cache, value)
    return value
