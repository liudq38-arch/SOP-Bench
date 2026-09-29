import asyncio
import hashlib
import json
import time
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator
from transformers import AutoTokenizer

from impact_qa.common import OUT, ROOT, fingerprint, read_json, save_json


FOLDER = OUT / 'descriptive_v21'
CONFIG = read_json(ROOT / 'configs/impact_qa/descriptive_v21_pilot.json')
SCHEMA = read_json(ROOT / CONFIG['schema'])
STAGES = {'describe_frames': 'frame_batch', 'observe_video': 'video_observation', 'reconcile_gt': 'reconciliation', 'describe_event': 'description', 'generate_open_qa': 'open_qa_bundle', 'audit': 'audit'}
MODEL_PATH = Path('/data_1/ldq/models/Qwen3.5-27B')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def stage_schema(stage):
    return {'$ref': '#/$defs/' + STAGES[stage], '$defs': SCHEMA['$defs']}


def extract_ids(value, field):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == field:
                yield from item if isinstance(item, list) else [item]
            else:
                yield from extract_ids(item, field)
    elif isinstance(value, list):
        for item in value:
            yield from extract_ids(item, field)


def validate(stage, result, payload, frames):
    Draft202012Validator(stage_schema(stage)).validate(result)
    if result['case_id'] != payload['case_id'] or result['view'] != payload['view']:
        raise ValueError('descriptive_v21:case_or_view_mismatch')
    allowed = {f['frame_id']: f for f in frames}
    refs = set(extract_ids(result, 'frame_ids'))
    if refs - allowed.keys():
        raise ValueError(f'descriptive_v21:unknown_frames:{sorted(refs - allowed.keys())}')
    if stage == 'describe_frames':
        requested = [f['frame_id'] for f in payload['target_frames']]
        cards = result['cards']
        if [c['frame_id'] for c in cards] != requested or result['missing_frame_ids']:
            raise ValueError('descriptive_v21:frame_coverage')
        for card in cards:
            if abs(card['source_pts_s'] - allowed[card['frame_id']]['source_pts_s']) > 0.00001:
                raise ValueError('descriptive_v21:frame_timestamp')
            for change in card.get('changes_from_previous', []):
                previous = allowed.get(change['previous_frame_id'])
                if previous is None or previous['source_pts_s'] >= card['source_pts_s']:
                    raise ValueError('descriptive_v21:change_order')
    if stage == 'generate_open_qa':
        if sum(item['kind'] == 'event_description' for item in result['items']) != 1:
            raise ValueError('descriptive_v21:missing_main_qa')
        if len(result['items']) > 5:
            raise ValueError('descriptive_v21:too_many_qa')
    low, high = min(f['source_pts_s'] for f in frames), max(f['source_pts_s'] for f in frames)
    for field in ['source_interval_s', 'scope_interval_s']:
        values = list(extract_ids(result, field))
        for a, b in zip(values[::2], values[1::2]):
            if not low - 0.001 <= a <= b <= high + 0.001:
                raise ValueError(f'descriptive_v21:interval_outside_media:{a}:{b}:{low}:{high}')


class ClientPool:
    def __init__(self):
        self.clients = [httpx.AsyncClient(base_url=url, trust_env=False, timeout=600) for url in CONFIG['base_urls']]
        self.queue = asyncio.Queue()
        for i in range(len(self.clients)):
            self.queue.put_nowait(i)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
        self.model_identity = fingerprint({p.name: {'size': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns} for p in sorted(MODEL_PATH.glob('*')) if p.is_file()})
        self.calls = []

    async def close(self):
        await asyncio.gather(*(c.aclose() for c in self.clients))

    async def call(self, stage, payload, frames, images=None, video=None, suffix='', prompt_extra=''):
        prompt = (ROOT / CONFIG['prompts'][stage]).read_text()
        schema = stage_schema(stage)
        shots = read_json(ROOT / CONFIG['few_shots'])['examples']
        example = shots[1 if stage == 'describe_frames' else 2]
        example_key = STAGES[stage]
        if example_key in example and stage != 'describe_frames':
            sample = example[example_key]
            if stage == 'describe_frames':
                sample = dict(sample, cards=sample['cards'][:1])
            prompt += '\nFICTIONAL STYLE EXAMPLE, NEVER REAL EVIDENCE:\n' + json.dumps(sample, ensure_ascii=False)
        prompt += '\n' + prompt_extra
        text_payload = json.dumps(payload, ensure_ascii=False)
        content = [{'type': 'text', 'text': text_payload}]
        pixels = 0
        for f in images or []:
            content.extend([{'type': 'text', 'text': f['frame_id']}, {'type': 'image_url', 'image_url': {'url': Path(f['path']).as_uri()}}])
            pixels += ((f['width'] + 31) // 32) * ((f['height'] + 31) // 32)
        if video:
            content.append({'type': 'video_url', 'video_url': {'url': Path(video['path']).as_uri()}})
            pixels += video['estimated_visual_tokens']
        maximum = CONFIG['max_output_tokens'][stage]
        estimate = len(self.tokenizer.encode(prompt + text_payload + json.dumps(schema))) + pixels + 512
        if estimate + maximum + CONFIG['token_safety_margin'] > CONFIG['max_model_len']:
            raise ValueError(f'descriptive_v21:budget:{stage}:{estimate}+{maximum}')
        request = {'model': CONFIG['model'], 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': content}], 'max_tokens': maximum, 'temperature': CONFIG['temperature'], 'top_p': CONFIG['top_p'], 'seed': CONFIG['seed'], 'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_schema', 'json_schema': {'name': STAGES[stage], 'schema': schema, 'strict': True}}}
        if video:
            request['media_io_kwargs'] = video['media_io_kwargs']
            request['mm_processor_kwargs'] = video['mm_processor_kwargs']
        key = fingerprint([request, self.model_identity, [f['sha256'] for f in images or []], video['sha256'] if video else None])
        path = FOLDER / 'api_cache' / (key + '.json')
        if path.exists():
            record = read_json(path)
            if record['status'] == 'ok':
                validate(stage, record['result'], payload, frames)
                return record
            raise ValueError(f'descriptive_v21:cached_failure:{path}:{record.get("error")}')
        index = await self.queue.get()
        started = time.monotonic()
        record = {'cache_key': key, 'stage': stage, 'case_id': payload['case_id'], 'suffix': suffix, 'base_url': CONFIG['base_urls'][index], 'model_identity': self.model_identity, 'estimated_prompt_tokens': estimate, 'request': request, 'status': 'error'}
        try:
            for attempt in range(3):
                try:
                    response = await self.clients[index].post('/chat/completions', json=request)
                    response.raise_for_status()
                    break
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                        raise ValueError(f'descriptive_v21:http:{exc.response.status_code}:{exc.response.text[:2000]}') from exc
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)
            body = response.json()
            record.update(raw_response=body, usage=body.get('usage'), seconds=time.monotonic() - started)
            if body['choices'][0]['finish_reason'] == 'length':
                raise ValueError('descriptive_v21:truncated')
            result = json.loads(body['choices'][0]['message']['content'])
            record['result'] = result
            validate(stage, result, payload, frames)
            record['status'] = 'ok'
            return record
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}:{exc}'
            raise
        finally:
            record['seconds'] = time.monotonic() - started
            save_json(path, record)
            self.calls.append({k: v for k, v in record.items() if k not in ['request', 'raw_response', 'result']})
            print(json.dumps({k: record.get(k) for k in ['case_id', 'stage', 'suffix', 'status', 'seconds', 'usage', 'error']}), flush=True)
            self.queue.put_nowait(index)
