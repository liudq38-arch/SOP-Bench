import asyncio
import json
import math
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import FFMPEG, read_json, save_json
from impact_qa.descriptive_v21 import FOLDER, ClientPool, digest


def prepare():
    from vllm.multimodal.media.image import ImageMediaIO
    from vllm.multimodal.media.video import VideoMediaIO
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize

    record = read_json(FOLDER / 'cases/atr_403f880f747b22eb_ego.json')
    frames = record['frames']
    result = []
    policies = [('first_64', 0, 200, 8, 64), ('first_128', 0, 200, 16, 128), ('second_64', 175, len(frames), 8, 64)]
    for name, start, stop, fps, limit in policies:
        selected = frames[start:stop]
        path = FOLDER / 'clips' / f'long_probe_{start}_{stop}.mp4'
        if not path.exists():
            lo, hi = selected[0]['source_frame_index'], selected[-1]['source_frame_index']
            subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', record['case']['source_video'], '-vf', f'select=between(n\\,{lo}\\,{hi}),setpts=PTS-STARTPTS,scale=960:-2', '-an', '-fps_mode', 'vfr', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(path)], check=True, capture_output=True, timeout=240)
        io = {'video_backend': 'opencv', 'fps': fps, 'num_frames': limit}
        decoded, metadata = VideoMediaIO(ImageMediaIO(), **io).load_file(path)
        nh, nw = smart_resize(len(decoded), *decoded.shape[1:3], min_pixels=4096, max_pixels=16777216)
        sampled = [selected[i] for i in metadata['frames_indices']]
        video = {'path': str(path), 'sha256': digest(path), 'media_io_kwargs': {'video': io}, 'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': 16777216}}, 'decoded_frames': len(decoded), 'estimated_visual_tokens': math.ceil(len(decoded) / 2) * (nh // 32) * (nw // 32), 'processor_shape': [nh, nw], 'sampled_frames': sampled}
        payload = {'case_id': record['case']['case_id'], 'view': 'ego', 'output_language': 'en', 'window_id': name, 'source_interval_s': [selected[0]['source_pts_s'], selected[-1]['source_pts_s']], 'video_start_source_pts_s': selected[0]['source_pts_s'], 'sampled_frames': [{'frame_id': f['frame_id'], 'source_pts_s': f['source_pts_s']} for f in sampled], 'instruction': 'Describe the entire supplied video window in chronological order. Source time equals video-local time plus video_start_source_pts_s. Distinguish camera motion from physical motion, manipulation from successful fastening, and tool replacement from correction. No GT is supplied.'}
        result.append({'name': name, 'video': video, 'payload': payload})
    save_json(FOLDER / 'long_probe_inputs.json', result)
    return result


async def main():
    inputs = prepare()
    pool = ClientPool()
    peak = {}
    stop = asyncio.Event()

    async def sample_memory():
        while not stop.is_set():
            process = await asyncio.create_subprocess_exec('nvidia-smi', '--query-gpu=index,memory.used', '--format=csv,noheader,nounits', stdout=asyncio.subprocess.PIPE)
            stdout, _ = await process.communicate()
            for line in stdout.decode().splitlines():
                index, memory = [int(s.strip()) for s in line.split(',')]
                peak[str(index)] = max(peak.get(str(index), 0), memory)
            try:
                await asyncio.wait_for(stop.wait(), timeout=1)
            except asyncio.TimeoutError:
                pass

    async def run(item):
        try:
            response = await pool.call('observe_video', item['payload'], item['video']['sampled_frames'], video=item['video'], suffix=item['name'])
            return {'name': item['name'], 'status': 'ok', 'video': item['video'], 'result': response['result'], 'cache_key': response['cache_key'], 'usage': response['usage'], 'seconds': response['seconds']}
        except Exception as exc:
            return {'name': item['name'], 'status': 'error', 'error': str(exc), 'video': item['video']}

    monitor = asyncio.create_task(sample_memory())
    started = time.monotonic()
    try:
        results = await asyncio.gather(*(run(item) for item in inputs))
    finally:
        stop.set()
        await monitor
        await pool.close()
    save_json(FOLDER / 'long_probe_results.json', {'results': results, 'peak_gpu_mib': peak, 'elapsed_s': time.monotonic() - started, 'same_pixel_budget': 16777216, 'no_quality_or_max_capacity_claim': True})
    print(json.dumps({'statuses': [(r['name'], r['status'], r.get('error')) for r in results], 'peak_gpu_mib': peak}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
