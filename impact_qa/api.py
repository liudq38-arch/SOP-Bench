import asyncio
import base64
import json
import time
from pathlib import Path

import httpx

from .common import OUT, fingerprint, read_json, save_json


class Client:
    def __init__(self, base_url='http://127.0.0.1:8000/v1', concurrency=2):
        self.base_url = base_url
        self.http = httpx.AsyncClient(base_url=base_url, timeout=480, trust_env=False)
        self.limit = asyncio.Semaphore(concurrency)
        self.model = 'impact-qwen35-27b'
        model_path = Path('/data_1/ldq/models/Qwen3.5-27B')
        self.model_revision = fingerprint({'config': read_json(model_path / 'config.json'), 'index': read_json(model_path / 'model.safetensors.index.json'), 'weight_files': [(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(model_path.glob('*.safetensors'))]})

    async def close(self):
        await self.http.aclose()

    async def call(self, stage, prompt, payload, images=None, max_tokens=2048):
        images = images or []
        key = fingerprint({'model': self.model, 'model_revision': self.model_revision, 'stage': stage, 'prompt': prompt, 'payload': payload, 'images': images, 'max_tokens': max_tokens, 'temperature': .1, 'thinking': False})
        target = OUT / 'api_cache' / (key + '.json')
        if target.exists():
            cached = read_json(target)
            if cached.get('status') == 'ok':
                return cached
        content = [{'type': 'text', 'text': json.dumps(payload, ensure_ascii=False)}]
        for frame in images:
            if frame.get('media_type') == 'video':
                content.append({'type': 'text', 'text': f"Video {frame['evidence_id']}: original interval {frame['source_start_s']:.3f}–{frame['source_end_s']:.3f}s; local video clock starts at 0. TARGET."})
                content.append({'type': 'video_url', 'video_url': {'url': Path(frame['path']).as_uri()}})
                continue
            content.append({'type': 'text', 'text': f"Frame {frame['evidence_id']}; video time {frame['requested_time_s']:.3f} seconds. {frame.get('time_scope', '')} {frame.get('view', '')}"})
            data = base64.b64encode(Path(frame['path']).read_bytes()).decode()
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + data}})
        request = {'model': self.model, 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': content}], 'temperature': .1, 'top_p': .8, 'max_tokens': max_tokens, 'seed': 20260918, 'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_object'}}
        if any(f.get('media_type') == 'video' for f in images):
            request['media_io_kwargs'] = {'video': {'num_frames': 16, 'fps': -1}}
            request['mm_processor_kwargs'] = {'num_frames': 16, 'do_sample_frames': False}
        async with self.limit:
            for attempt in range(3):
                started = time.time()
                try:
                    response = await self.http.post('/chat/completions', json=request)
                    response.raise_for_status()
                    body = response.json()
                    choice = body['choices'][0]
                    raw = choice['message']['content']
                    parsed = json.loads(raw)
                    if choice.get('finish_reason') == 'length':
                        raise ValueError('generation_truncated')
                    record = {'cache_key': key, 'status': 'ok', 'stage': stage, 'seconds': time.time() - started, 'usage': body.get('usage'), 'result': parsed, 'raw_response': body, 'request_metadata': {'base_url': self.base_url, 'media_io_kwargs': request.get('media_io_kwargs'), 'mm_processor_kwargs': request.get('mm_processor_kwargs'), 'prompt': prompt, 'payload': payload, 'image_refs': images, 'max_tokens': max_tokens, 'model': self.model, 'model_revision': self.model_revision}}
                    save_json(target, record)
                    return record
                except Exception as exc:
                    error = f'{stage}: {type(exc).__name__}: {exc}'
                    save_json(target, {'cache_key': key, 'status': 'error', 'stage': stage, 'attempt': attempt + 1, 'error': error})
                    if attempt == 2:
                        raise RuntimeError(error) from exc
                    await asyncio.sleep(2 ** attempt)


class Pool:
    def __init__(self, base_urls, per_service_concurrency=4):
        self.clients = [Client(url, per_service_concurrency) for url in base_urls]
        self.model = self.clients[0].model
        self.model_revision = self.clients[0].model_revision
        self.slots = asyncio.Queue()
        for _ in range(per_service_concurrency):
            for client in self.clients:
                self.slots.put_nowait(client)

    async def close(self):
        await asyncio.gather(*(client.close() for client in self.clients))

    async def call(self, *args, **kwargs):
        client = await self.slots.get()
        try:
            return await client.call(*args, **kwargs)
        finally:
            self.slots.put_nowait(client)
