import asyncio
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
from vllm.multimodal.media.image import ImageMediaIO
from vllm.multimodal.media.video import VideoMediaIO

from impact_qa.common import ROOT, read_json, read_jsonl, save_json
from impact_qa.history_v23 import CONFIG, FOLDER, schema, validate_qa
from impact_qa.structured_video_client import StructuredVideoPool


async def main():
    originals = read_json(FOLDER / 'results.json')
    records = {r['case']['case_id']: r for r in read_jsonl(ROOT / CONFIG['source_cases'])}
    media = {r['case_id']: r for r in read_json(FOLDER / 'review_media.json')}
    pool = StructuredVideoPool(CONFIG, FOLDER / 'qa_visual_revision')
    async def process(result):
        case_id = result['case_id']
        record = records[case_id]
        case = record['case']
        item = media[case_id]
        io = {'video_backend': 'opencv', 'fps': 8, 'num_frames': 64}
        images, meta = VideoMediaIO(ImageMediaIO(), **io).load_file(Path(item['path']))
        sampled = [record['frames'][i] for i in meta['frames_indices']]
        h, w = smart_resize(len(images), *images.shape[1:3], min_pixels=4096, max_pixels=16777216)
        video = {'path': item['path'], 'sha256': item['sha256'], 'sampled_frames': sampled, 'media_io_kwargs': {'video': io}, 'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': 16777216}}, 'estimated_visual_tokens': math.ceil(len(images) / 2) * (h // 32) * (w // 32), 'processor_shape': [h, w]}
        events = [e for row in result['ledger'] for e in row['events']]
        atr = next(s for s in case['source_catalog'] if s['source_id'] == 'atr_' + case['view'])
        payload = {'case_id': case_id, 'view': case['view'], 'clip_ledger': result['ledger'], 'integrated_account': result['integration'], 'atr_ground_truth': atr, 'source_interval_s': case['interval_s'], 'video_start_source_pts_s': item['source_start_pts_s'], 'sampling_source_pts_s': [f['source_pts_s'] for f in sampled], 'normative_sequence': None, 'normative_tool': None}
        def validate(value):
            validate_qa(value)
            for q in value['items']:
                if any(e['event_id'] in q['question'] + q['answer'] for e in events):
                    raise ValueError('history_v23:internal_ids_in_prose')
        output = {'case_id': case_id, 'status': 'error', 'video': video, 'formal_release': False}
        try:
            response = await pool.call('qa', (ROOT / 'prompts/impact_qa/diagnostics/history_v23_qa_visual.txt').read_text(), payload, schema('qa', events), CONFIG['max_tokens']['qa'], video=video, validator=validate)
            output.update(status='pending_review', qa=response['result'], cache_key=response['cache_key'])
        except Exception as exc:
            output['error'] = str(exc)
        save_json(FOLDER / 'qa_visual_revision' / (case_id + '.json'), output)
        return output
    try:
        results = await asyncio.gather(*(process(r) for r in originals))
        save_json(FOLDER / 'qa_visual_revision/results.json', results)
        save_json(FOLDER / 'qa_visual_revision/summary.json', {'cases': len(results), 'completed': sum(r['status'] == 'pending_review' for r in results), 'open_qa': sum(len(r.get('qa', {}).get('items', [])) for r in results), 'new_requests': len(pool.calls), 'input_tokens': sum((r.get('usage') or {}).get('prompt_tokens', 0) for r in pool.calls), 'output_tokens': sum((r.get('usage') or {}).get('completion_tokens', 0) for r in pool.calls), 'formal_release': False})
    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())
