import asyncio
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import read_json, save_json
from impact_qa.descriptive_v21 import CONFIG, FOLDER, ClientPool
from scripts.run_descriptive_v21 import gt_payload, public_frame, video_payload


async def main():
    from vllm.multimodal.media.image import ImageMediaIO
    from vllm.multimodal.media.video import VideoMediaIO
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize

    CONFIG['few_shots'] = 'prompts/impact_qa/v21/few_shots_structure_only.json'
    record = read_json(FOLDER / 'cases/atr_b5048432118ffc77_ego.json')
    case = record['case']
    clip = record['clips'][0]
    video = dict(clip['video'])
    io = {'video_backend': 'opencv', 'fps': -1, 'num_frames': 96}
    decoded, meta = VideoMediaIO(ImageMediaIO(), **io).load_file(Path(video['path']))
    if len(decoded) != len(clip['media_frames']):
        raise ValueError('repair_v21:dense_video_not_all_frames')
    nh, nw = smart_resize(len(decoded), *decoded.shape[1:3], min_pixels=4096, max_pixels=16777216)
    video.update(media_io_kwargs={'video': io}, sampled_frames=clip['media_frames'], decoded_frames=len(decoded), processor_shape=[nh, nw], estimated_visual_tokens=math.ceil(len(decoded) / 2) * (nh // 32) * (nw // 32))
    clip = dict(clip, video=video)
    images = [clip['core_frames'][round(i * (len(clip['core_frames']) - 1) / 7)] for i in range(8)]
    payload = video_payload(case, clip)
    payload['input_note'] = 'Every decoded video frame is supplied, plus eight larger still images. No previous generated description or fictional answer is supplied. Describe only this core interval. No event IDs are supplied; cite actual frame_ids and leave event_ids empty. Each atomic claim should cite 1–3 directly supporting frames, or a before/after pair for a change; do not repeat the entire frame manifest in every claim. Evidence should be sufficient and specific, not exhaustive lists.'
    result = {'case_id': case['case_id'], 'branch': 'video_led_no_factual_examples', 'native_video_frames': len(decoded), 'extra_still_images': len(images), 'core_frames': len(clip['core_frames']), 'status': 'error', 'stages': {}}
    pool = ClientPool()
    try:
        response = await pool.call('describe_event', dict(payload, annotation_gt=gt_payload(case, clip)), clip['media_frames'], images=images, video=video, suffix='repair_description', prompt_extra='Do not supply exact component identity from appearance alone. Describe uncertainty coherently: do not assert surface contact, a grasped named tool, or insertion while also saying that same fact is unresolved. Duration wording must fit the supplied approximately two-second core. Use observed states and changes, not intent. The annotation covers a larger interval; it cannot prove a tool is visibly held here.')
        result['description'] = response['result']
        result['stages']['description'] = response['cache_key']
        response = await pool.call('generate_open_qa', dict(payload, description=result['description'], annotation_gt=gt_payload(case, clip)), clip['media_frames'], images=images, video=video, suffix='repair_qa', prompt_extra='Generate the main detailed descriptive QA and at most one supported observed_sequence question. No fictional example answers are provided. Do not invent a tool switch, off-screen gap or tool identity. Use coarse appearance-based nouns if uncertainty remains. Only describe target_interval_s; all event_ids must be empty because no event table was supplied.')
        result['qa'] = response['result']
        result['stages']['qa'] = response['cache_key']
        response = await pool.call('audit', dict(payload, description=result['description'], qa=result['qa']), clip['media_frames'], images=images, video=video, suffix='repair_audit', prompt_extra='Every frame in sampled_frames is physically present in the dense video. Check ALL QA and description claims, specifically temporal order, unsupported object names, tool pickup versus reaching, and contact ambiguity. No annotation GT is supplied to you. Do not certify a statement solely because the description repeats it.')
        result['audit'] = response['result']
        result['stages']['audit'] = response['cache_key']
        result['status'] = 'completed_unvalidated'
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        await pool.close()
        save_json(FOLDER / 'repair_no_examples.json', result)
        print(json.dumps({'status': result['status'], 'error': result.get('error')}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
