import asyncio
import fcntl
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import av
import httpx
import torch
from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
from vllm.multimodal.media.image import ImageMediaIO
from vllm.multimodal.media.video import VideoMediaIO

from impact_qa.common import ANNOTATIONS, FFMPEG, ROOT, read_json, read_jsonl, save_json
from impact_qa.event_v22 import TEXT, arr, choice, obj
from impact_qa.structured_video_client import StructuredVideoPool
from scripts.run_step_v24 import CONFIG, digest


FOLDER = ROOT / 'outputs/impact_qa/completion_v24'
VIDEO_ID = 'AL07EJ17_Reassembly_A_002_front'


def prepare():
    profile = next(r['media_profile'] for r in read_jsonl(ROOT / 'outputs/impact_qa/state_qa_inputs_v10/packets.jsonl') if r['target']['video_id'] == VIDEO_ID)
    source = Path(profile['path'])
    asr_path = ANNOTATIONS / 'ASR/annotations' / (VIDEO_ID + '_asr.json')
    asr = read_json(asr_path)
    index = next(i for i, c in enumerate(asr['components']) if c['name'] == 'anti_vibration_handle')
    if asr['fps'] != profile['fps'] or source.stat().st_size != profile['file_bytes']:
        raise ValueError('completion_v24:source_profile_mismatch')
    native = []
    with av.open(source) as container:
        container.streams.video[0].thread_count = 2
        for f in container.decode(video=0):
            native.append(float(f.pts * f.time_base))
    if len(native) != asr['frame_count'] or max(abs(t - i / asr['fps']) for i, t in enumerate(native)) > 0.00001:
        raise ValueError('completion_v24:source_frame_pts_mismatch')
    results = []
    for suffix, start, end, expected_state in [('handle_misassembled', 4800, 5000, -1), ('handle_completed', 4800, 5213, 1)]:
        case_id = 'completion_v24_' + suffix
        destination = FOLDER / 'media' / (case_id + '.mp4')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix('.tmp.mp4')
            subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', str(source), '-vf', f'select=between(n\\,{start}\\,{end}),setpts=PTS-STARTPTS,scale=960:-2', '-an', '-fps_mode', 'vfr', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(temporary)], check=True, capture_output=True, timeout=240)
            temporary.replace(destination)
        with av.open(destination) as container:
            pts = [float(f.pts * f.time_base) for f in container.decode(video=0)]
        if len(pts) != end - start + 1 or max(abs(t - (native[start + i] - native[start])) for i, t in enumerate(pts)) > 0.002:
            raise ValueError('completion_v24:crop_frame_pts_mismatch')
        io = {'video_backend': 'opencv', 'fps': 8, 'num_frames': 64}
        images, meta = VideoMediaIO(ImageMediaIO(), **io).load_file(destination)
        h, w = smart_resize(len(images), *images.shape[1:3], min_pixels=4096, max_pixels=16777216)
        frames = [{'frame_id': f'f{start + i:07d}', 'source_frame_index': start + i, 'source_pts_s': native[start + i]} for i in meta['frames_indices']]
        end_index = max(i for i, row in enumerate(asr['state_sequence']) if row['frame'] <= end)
        state = asr['state_sequence'][end_index]['state'][index]
        if state != expected_state or frames[-1]['source_frame_index'] < asr['state_sequence'][end_index]['frame']:
            raise ValueError('completion_v24:target_state_not_sampled')
        sources = [{'source_id': 'asr_end', 'path': str(asr_path.relative_to(ROOT)), 'sha256': digest(asr_path), 'pointer': f'/state_sequence/{end_index}/state/{index}', 'effective_from_frame': asr['state_sequence'][end_index]['frame'], 'queried_frame': end, 'component': 'anti_vibration_handle', 'state': state, 'meaning': {-1: 'misassembled', 0: 'unassembled', 1: 'correctly assembled'}[state]}]
        target = {'case_id': case_id, 'view': 'front', 'video_id': VIDEO_ID, 'component': 'anti_vibration_handle', 'source_interval_frames_inclusive': [start, end], 'source_interval_s': [native[start], native[end]], 'state_at_end': state, 'source_catalog': sources, 'frame_count': len(pts), 'sampling_source_pts_s': [f['source_pts_s'] for f in frames], 'source_video_sha256': digest(source)}
        video = {'path': str(destination), 'sha256': digest(destination), 'sampled_frames': frames, 'media_io_kwargs': {'video': io}, 'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': 16777216}}, 'estimated_visual_tokens': math.ceil(len(images) / 2) * (h // 32) * (w // 32), 'processor_shape': [h, w]}
        save_json(FOLDER / 'inputs' / (case_id + '.json'), {'target': target, 'video': video})
        results.append((target, video))
    save_json(FOLDER / 'manifest.json', [{'case_id': p['case_id'], 'path': v['path'], 'source_interval_s': p['source_interval_s'], 'frames': len(v['sampled_frames']), 'state_at_end': p['state_at_end']} for p, v in results])
    return results


def validate(value, target):
    q = value['items'][0]
    if q['verdict'] != ('yes' if target['state_at_end'] == 1 else 'no'):
        raise ValueError('completion_v24:state_polarity_mismatch')
    if 'handle' not in q['question'].lower() or 'end' not in q['question'].lower():
        raise ValueError('completion_v24:missing_component_or_time_scope')
    if any(s in (q['question'] + q['answer']).lower() for s in ['annotat', 'ground truth', 'asr', 'state label', 'entire device']):
        raise ValueError('completion_v24:provenance_leak_or_scope')


async def main():
    if not torch.cuda.is_available():
        raise RuntimeError('completion_v24:cuda_unavailable')
    for url in CONFIG['base_urls']:
        response = httpx.get(url + '/models', trust_env=False, timeout=10)
        response.raise_for_status()
    packets = prepare()
    save_json(FOLDER / 'precheck.json', {'torch': torch.__version__, 'cuda': torch.version.cuda, 'gpu_count': torch.cuda.device_count(), 'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used', '--format=csv,noheader'], text=True), 'first10': [{'case_id': p['case_id'], 'frames': len(v['sampled_frames']), 'state': p['state_at_end']} for p, v in packets]})
    pool = StructuredVideoPool(CONFIG, FOLDER)
    async def process(target, video):
        output = {'case_id': target['case_id'], 'status': 'error', 'formal_release': False, 'target': target, 'video': video}
        try:
            blind = {k: target[k] for k in ['case_id', 'view', 'source_interval_s', 'sampling_source_pts_s']}
            observed = await pool.call('completion_observe', (ROOT / 'prompts/impact_qa/v24_completion_observe.txt').read_text(), blind, obj({'description': TEXT, 'visible_end_state': TEXT, 'limitations': TEXT}), 1536, video=video)
            output['observation'] = observed['result']
            schema = obj({'items': arr(obj({'kind': choice(['step_completion']), 'question': TEXT, 'answer': TEXT, 'verdict': choice(['yes', 'no']), 'source_ids': arr(choice(['asr_end']), 1, 1), 'evidence_basis': TEXT, 'visual_support': choice(['supports_visible_outcome', 'cannot_independently_confirm', 'conflicts_with_gt']), 'visual_limitation': TEXT}), 1, 1)})
            qa = await pool.call('completion_qa', (ROOT / 'prompts/impact_qa/v24_completion_qa.txt').read_text(), dict(target, visual_observation=observed['result']), schema, 2048, video=video, validator=lambda value: validate(value, target))
            output.update(status='pending_review', qa=qa['result'], cache_keys=[observed['cache_key'], qa['cache_key']])
            if qa['result']['items'][0]['visual_support'] == 'conflicts_with_gt':
                output['status'] = 'held_visual_gt_conflict'
        except Exception as exc:
            output['error'] = str(exc)
        save_json(FOLDER / 'results' / (target['case_id'] + '.json'), output)
        return output
    try:
        results = await asyncio.gather(*(process(p, v) for p, v in packets))
        save_json(FOLDER / 'results.json', results)
        summary = {'cases': len(results), 'completed': sum(r['status'] == 'pending_review' for r in results), 'new_requests': len(pool.calls), 'input_tokens': sum((c.get('usage') or {}).get('prompt_tokens', 0) for c in pool.calls), 'output_tokens': sum((c.get('usage') or {}).get('completion_tokens', 0) for c in pool.calls), 'calls': pool.calls, 'formal_release': False}
        save_json(FOLDER / ('summary.json' if pool.calls else 'resume_summary.json'), summary)
        print(summary, flush=True)
    finally:
        await pool.close()


if __name__ == '__main__':
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main())
