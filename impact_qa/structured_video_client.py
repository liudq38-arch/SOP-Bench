import asyncio
import json
import time
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator
from transformers import AutoTokenizer

from impact_qa.common import fingerprint, read_json, save_json


class StructuredVideoPool:
    def __init__(self, config, folder):
        self.config = config
        self.folder = Path(folder)
        self.clients = [httpx.AsyncClient(base_url=u, timeout=480, trust_env=False) for u in config['base_urls']]
        self.slots = asyncio.Queue()
        for i in range(len(self.clients)):
            for _ in range(config.get('per_service_concurrency', 1)):
                self.slots.put_nowait(i)
        model = Path(config['model_path'])
        self.identity = fingerprint({p.name: [p.stat().st_size, p.stat().st_mtime_ns] for p in model.iterdir() if p.is_file()})
        self.tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
        self.calls = []

    async def close(self):
        await asyncio.gather(*(c.aclose() for c in self.clients))

    async def call(self, stage, prompt, payload, schema, maximum, video=None, validator=None):
        Draft202012Validator.check_schema(schema)
        prompt += '\nOutput schema:\n' + json.dumps(schema, separators=(',', ':'))
        text_payload = json.dumps(payload, ensure_ascii=False)
        content = [{'type': 'text', 'text': text_payload}]
        if video:
            content.append({'type': 'video_url', 'video_url': {'url': Path(video['path']).as_uri()}})
        estimate = len(self.tokenizer.encode(prompt + text_payload)) + 512 + (video['estimated_visual_tokens'] if video else 0)
        if estimate + maximum + 1024 > self.config['max_model_len']:
            raise ValueError(f'structured_video:context_budget:{stage}:{estimate}')
        request = {'model': self.config['model'], 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': content}], 'temperature': self.config['temperature'], 'top_p': self.config['top_p'], 'seed': self.config['seed'], 'max_tokens': maximum, 'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_schema', 'json_schema': {'name': stage, 'schema': schema, 'strict': True}}}
        if video:
            request.update(media_io_kwargs=video['media_io_kwargs'], mm_processor_kwargs=video['mm_processor_kwargs'])
        key = fingerprint([request, self.identity, video['sha256'] if video else None])
        path = self.folder / 'api_cache' / f'{key}.json'
        def check(value):
            Draft202012Validator(schema).validate(value)
            if validator:
                validator(value)
        archived_failure = None
        if path.exists():
            record = read_json(path)
            if record['status'] == 'ok':
                check(record['result'])
                return record
            failure_dir = self.folder / 'api_cache_failures'
            failure_dir.mkdir(parents=True, exist_ok=True)
            archived_path = failure_dir / f'{key}.{time.time_ns()}.json'
            path.replace(archived_path)
            archived_failure = str(archived_path.relative_to(self.folder))
        index = await self.slots.get()
        start = time.monotonic()
        record = {'cache_key': key, 'stage': stage, 'case_id': payload['case_id'], 'request': request, 'model_identity': self.identity, 'base_url': self.config['base_urls'][index], 'estimated_prompt_tokens': estimate, 'video_frames': len(video['sampled_frames']) if video else 0, 'media_sha256': video['sha256'] if video else None, 'status': 'error'}
        if archived_failure:
            record['retried_after_cached_failure'] = archived_failure
        try:
            for attempt in range(3):
                try:
                    response = await self.clients[index].post('/chat/completions', json=request)
                    response.raise_for_status()
                    break
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                        raise ValueError(f'structured_video:http:{exc.response.status_code}:{exc.response.text[:1000]}') from exc
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)
            body = response.json()
            record.update(raw_response=body, usage=body.get('usage'))
            if body['choices'][0]['finish_reason'] != 'stop':
                raise ValueError(f'structured_video:finish:{body["choices"][0]["finish_reason"]}')
            record['result'] = json.loads(body['choices'][0]['message']['content'])
            check(record['result'])
            record['status'] = 'ok'
            return record
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}:{exc}'
            raise
        finally:
            record['seconds'] = time.monotonic() - start
            save_json(path, record)
            self.calls.append({k: v for k, v in record.items() if k not in ['request', 'raw_response', 'result']})
            print(json.dumps({k: record.get(k) for k in ['stage', 'case_id', 'status', 'seconds', 'usage', 'error']}), flush=True)
            self.slots.put_nowait(index)
