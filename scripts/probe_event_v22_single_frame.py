import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.api import Client
from impact_qa.common import ROOT, fingerprint, read_json, read_jsonl, save_json


FOLDER = ROOT / 'outputs/impact_qa/event_v22'


async def main():
    frames = [(r['case']['case_id'], f) for r in read_jsonl(ROOT / 'outputs/impact_qa/descriptive_v21/cases.jsonl') for f in r['frames']]
    requested = [('atr_17fd15858f5679ef_ego', 717), ('atr_17fd15858f5679ef_front', 826), ('atr_b5048432118ffc77_ego', 2921), ('atr_b5048432118ffc77_front', 3501), ('atr_403f880f747b22eb_ego', 2501), ('atr_403f880f747b22eb_front', 3046)]
    targets = [(cid, next(f for c, f in frames if c == cid and f['source_frame_index'] == i)) for cid, i in requested]
    prompt = (ROOT / 'prompts/impact_qa/diagnostics/v22_single_frame_probe.txt').read_text()
    results = []
    async def run_model(model, port, model_path):
        client = Client(f'http://127.0.0.1:{port}/v1', concurrency=1)
        client.model = model
        path = Path(model_path)
        client.model_revision = fingerprint({p.name: [p.stat().st_size, p.stat().st_mtime_ns] for p in path.iterdir() if p.is_file()})
        try:
            for cid, f in targets:
                media = dict(f, evidence_id=f['frame_id'], requested_time_s=f['source_pts_s'])
                response = await client.call('event_v22_single_frame', prompt, {'case_id': cid, 'frame_id': f['frame_id']}, images=[media], max_tokens=700)
                result = {'case_id': cid, 'frame_id': f['frame_id'], 'model': model, 'cache_key': response['cache_key'], 'result': response['result'], 'seconds': response['seconds'], 'usage': response['usage'], 'human_gold': False}
                if result['result'].get('frame_id') != f['frame_id']:
                    result['validation_error'] = 'frame_id_mismatch'
                save_json(FOLDER / 'single_frame' / f'{model}_{cid}_{f["frame_id"]}.json', result)
                results.append(result)
                print(json.dumps(result), flush=True)
        finally:
            await client.close()
    await asyncio.gather(run_model('impact-qwen35-27b', 8000, '/data_1/ldq/models/Qwen3.5-27B'), run_model('impact-qwen3vl8b', 8003, '/data_1/ldq/models/Qwen3-VL-8B-Instruct'))
    save_json(FOLDER / 'single_frame_results.json', results)


if __name__ == '__main__':
    asyncio.run(main())
