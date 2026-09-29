import asyncio
import base64
import importlib.metadata
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import torch
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl, save_json


async def main():
    if not torch.cuda.is_available():
        raise RuntimeError('preflight: CUDA unavailable')
    report = {'torch': torch.__version__, 'cuda_runtime': torch.version.cuda, 'cuda_available': True, 'gpu_count': torch.cuda.device_count(), 'packages': {p: importlib.metadata.version(p) for p in ['vllm', 'transformers', 'httpx', 'av']}, 'tests': []}
    event = read_jsonl(OUT / 'development_events.jsonl')[0]
    evidence = read_json(OUT / 'evidence' / event['event_id'] / 'overview/manifest.json')
    image = evidence['images'][0]
    data = base64.b64encode(Path(image['path']).read_bytes()).decode()
    clip = OUT / 'review/clips' / (event['event_id'] + '.mp4')
    tests = [('text', [{'type': 'text', 'text': 'Return JSON with key ok and boolean value true.'}]), ('image', [{'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + data}}, {'type': 'text', 'text': 'Return JSON with key objects and a short list of visible objects.'}]), ('video', [{'type': 'video_url', 'video_url': {'url': clip.as_uri()}}, {'type': 'text', 'text': 'Return JSON with key action and a brief description of visible activity.'}])]
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000', timeout=300, trust_env=False) as client:
        response = await client.get('/health')
        response.raise_for_status()
        for name, content in tests:
            started = time.time()
            response = await client.post('/v1/chat/completions', json={'model': 'impact-qwen35-27b', 'messages': [{'role': 'user', 'content': content}], 'max_tokens': 256, 'temperature': 0, 'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_object'}})
            response.raise_for_status()
            result = response.json()
            json.loads(result['choices'][0]['message']['content'])
            report['tests'].append({'name': name, 'status': 'ok', 'seconds': time.time() - started, 'response': result})
            save_json(REPORTS / 'service_smoke.json', report)
            print(name, 'ok', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
