import asyncio
import json
import time
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator
from transformers import AutoTokenizer

from impact_qa.common import ROOT, fingerprint, read_json, save_json
from impact_qa.descriptive_v21 import digest


CONFIG = read_json(ROOT / 'configs/impact_qa/event_v22.json')
FOLDER = ROOT / CONFIG['output_root']


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def arr(items, minimum=0, maximum=20):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum}


def choice(values):
    return {'type': 'string', 'enum': list(values)}


TEXT = {'type': 'string'}


def schema_for(stage, payload, frames):
    fid = choice([f['frame_id'] for f in frames])
    if stage == 'observe':
        core = choice(payload['allowed_core_frame_ids'])
        fact = obj({'kind': choice(['state', 'transition']), 'hand': choice(['left', 'right', 'both', 'unknown', 'not_applicable']), 'text': TEXT, 'evidence_frame_ids': arr(core, 1, 4), 'confidence': choice(['high', 'medium', 'low'])})
        return obj({'facts': arr(fact, 0, 7), 'unknowns': arr(TEXT, 0, 4)})
    if stage == 'verify':
        verdict = obj({'claim_id': choice([c['event_id'] for c in payload['claims']]), 'verdict': choice(['supported', 'contradicted', 'unverifiable']), 'reason': TEXT, 'evidence_frame_ids': arr(fid, 1, 4)})
        omission = obj({'text': TEXT, 'evidence_frame_ids': arr(fid, 1, 3)})
        return obj({'verdicts': arr(verdict, len(payload['claims']), len(payload['claims'])), 'omissions': arr(omission, 0, 3)})
    if stage == 'reconcile':
        source_ids = [g['source_id'] for g in payload['gt_rows']]
        event_ids = [e['event_id'] for e in payload['events']]
        row = obj({'source_id': choice(source_ids or ['none']), 'relation': choice(['consistent_visible', 'not_visible', 'conflict']), 'reason': TEXT, 'evidence_frame_ids': arr(fid, 0, 3)})
        return obj({'rows': arr(row, len(source_ids), len(source_ids)), 'visual_error_event_ids': arr(choice(event_ids or ['none']), 0, len(event_ids))})
    if stage == 'compose':
        return obj({'status': choice(['answerable', 'unanswerable']), 'question': TEXT, 'ordered_event_ids': arr(choice(payload['allowed_event_ids']), 0, len(payload['allowed_event_ids'])), 'reason': TEXT})
    raise ValueError(f'event_v22:unknown_stage:{stage}')


def public_frame(f):
    return {k: f[k] for k in ['frame_id', 'source_pts_s', 'source_frame_index']}


def key_images(frames, count=8):
    return [frames[i] for i in sorted({round(i * (len(frames) - 1) / (min(count, len(frames)) - 1)) for i in range(min(count, len(frames)))})] if len(frames) > 1 else frames


def media_manifest(video, images):
    return sorted({f['frame_id']: f for f in video['sampled_frames'] + images}.values(), key=lambda f: f['source_pts_s'])


def base_payload(case, clip, images):
    frames = media_manifest(clip['video'], images)
    core_ids = {f['frame_id'] for f in clip['core_frames']}
    return {'case_id': case['case_id'], 'view': case['view'], 'clip_id': clip['clip_id'], 'target_interval_s': [clip['core_frames'][0]['source_pts_s'], clip['core_frames'][-1]['source_pts_s']], 'video_start_source_pts_s': clip['media_frames'][0]['source_pts_s'], 'time_mapping': 'video-local seconds + video_start_source_pts_s = source time; listed PTS are authoritative', 'allowed_core_frame_ids': [f['frame_id'] for f in frames if f['frame_id'] in core_ids], 'video_sample_frames': [public_frame(f) for f in clip['video']['sampled_frames']], 'labeled_images': [public_frame(f) for f in images], 'output_language': 'en'}


def gt_rows(case, clip):
    a, b = clip['core_frames'][0]['source_frame_index'], clip['core_frames'][-1]['source_frame_index']
    context = {x['source_id']: x for x in case['shared_gt']['atomic_context']}
    result = []
    for source in case['source_catalog']:
        sid, value = source['source_id'], source['value']
        if not sid.startswith(case['view'] + '_') or 'start_frame' not in value:
            continue
        if value['start_frame'] > b or value['end_frame'] < a:
            continue
        result.append({'source_id': sid, 'source_path': source['path'], 'source_pointer': source['pointer'], 'source_sha256': source['sha256'], 'annotation_interval_inclusive': [value['start_frame'], value['end_frame']], 'intersection_inclusive': [max(a, value['start_frame']), min(b, value['end_frame'])], 'scope_relation': 'full_annotation_inside_core' if a <= value['start_frame'] <= value['end_frame'] <= b else 'annotation_extends_beyond_core', 'hand': value['entity'], 'action': context[sid]['action'], 'noun': context[sid]['noun'], 'phase': value['phase'], 'anomaly_labels': context[sid]['anomaly_labels']})
    return result


def validate(stage, value, payload, frames):
    Draft202012Validator(schema_for(stage, payload, frames)).validate(value)
    by_id = {f['frame_id']: f for f in frames}
    if stage == 'observe':
        for f in value['facts']:
            times = [by_id[i]['source_pts_s'] for i in f['evidence_frame_ids']]
            if times != sorted(set(times)) or (f['kind'] == 'transition' and len(times) < 2):
                raise ValueError('event_v22:invalid_transition_order')
    if stage in ['verify', 'reconcile']:
        key, rows, requested = ('claim_id', value['verdicts'], [c['event_id'] for c in payload['claims']]) if stage == 'verify' else ('source_id', value['rows'], [r['source_id'] for r in payload['gt_rows']])
        if sorted(r[key] for r in rows) != sorted(requested):
            raise ValueError('event_v22:incomplete_or_duplicate_verdicts')
    if stage == 'compose':
        ids = value['ordered_event_ids']
        if len(ids) != len(set(ids)) or (value['status'] == 'answerable' and not ids):
            raise ValueError('event_v22:invalid_answer_event_selection')
        events = {e['event_id']: e for e in payload['events']}
        times = [events[i]['evidence_span_s'][0] for i in ids]
        if times != sorted(times):
            raise ValueError('event_v22:answer_order')


def events_from(value, clip_id, frames):
    by_id = {f['frame_id']: f for f in frames}
    return [dict(f, event_id=f'{clip_id}_e{i:02d}', first_frame_id=f['evidence_frame_ids'][0], last_frame_id=f['evidence_frame_ids'][-1], evidence_span_s=[by_id[f['evidence_frame_ids'][0]]['source_pts_s'], by_id[f['evidence_frame_ids'][-1]]['source_pts_s']], evidence_kind='sampled_observation_span_not_action_duration') for i, f in enumerate(value['facts'])]


def render_answer(selection, events):
    by_id = {e['event_id']: e for e in events}
    if selection['status'] != 'answerable':
        return None
    selected = [by_id[i] for i in selection['ordered_event_ids']]
    return {'kind': 'event_description', 'question': selection['question'], 'answer': ' '.join(e['text'].strip() for e in selected), 'claims': selected, 'status': 'model_screened_pending_human', 'answer_assembly': 'verbatim_screened_event_sentences', 'formal_release': False}


class Pool:
    def __init__(self):
        self.clients = [httpx.AsyncClient(base_url=u, timeout=480, trust_env=False) for u in CONFIG['base_urls']]
        self.queue = asyncio.Queue()
        for i in range(len(self.clients)):
            self.queue.put_nowait(i)
        model_path = Path(CONFIG['model_path'])
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self.identity = fingerprint({p.name: [p.stat().st_size, p.stat().st_mtime_ns] for p in model_path.iterdir() if p.is_file()})
        self.calls = []

    async def close(self):
        await asyncio.gather(*(c.aclose() for c in self.clients))

    async def call(self, stage, payload, video, images, run_id):
        frames = media_manifest(video, images)
        schema = schema_for(stage, payload, frames)
        prompt = (ROOT / f'prompts/impact_qa/v22/{stage}.txt').read_text()
        prompt += '\nOUTPUT JSON SCHEMA (use compact JSON, no indentation, no extra keys):\n' + json.dumps(schema, separators=(',', ':'))
        text_payload = json.dumps(payload, ensure_ascii=False)
        content = [{'type': 'text', 'text': text_payload}, {'type': 'video_url', 'video_url': {'url': Path(video['path']).as_uri()}}]
        for f in images:
            content.extend([{'type': 'text', 'text': f"{f['frame_id']} source_time={f['source_pts_s']:.6f}"}, {'type': 'image_url', 'image_url': {'url': Path(f['path']).as_uri()}}])
        pixels = sum(((f['width'] + 31) // 32) * ((f['height'] + 31) // 32) for f in images) + video['estimated_visual_tokens']
        estimate = len(self.tokenizer.encode(prompt + text_payload + json.dumps(schema))) + pixels + 512
        if estimate + CONFIG['max_tokens'][stage] + CONFIG['token_safety_margin'] > CONFIG['max_model_len']:
            raise ValueError(f'event_v22:context_budget:{stage}:{estimate}')
        request = {'model': CONFIG['model'], 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': content}], 'temperature': CONFIG['temperature'], 'top_p': CONFIG['top_p'], 'seed': CONFIG['seed'], 'max_tokens': CONFIG['max_tokens'][stage], 'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_schema', 'json_schema': {'name': stage, 'schema': schema, 'strict': True}}, 'media_io_kwargs': video['media_io_kwargs'], 'mm_processor_kwargs': video['mm_processor_kwargs']}
        key = fingerprint([request, self.identity, video['sha256'], [f['sha256'] for f in images], digest(Path(__file__))])
        path = FOLDER / 'api_cache' / f'{key}.json'
        if path.exists():
            record = read_json(path)
            if record['status'] != 'ok':
                raise ValueError(f'event_v22:cached_failure:{record.get("error")}')
            validate(stage, record['result'], payload, frames)
            return record
        index = await self.queue.get()
        start = time.monotonic()
        record = {'cache_key': key, 'stage': stage, 'run_id': run_id, 'case_id': payload['case_id'], 'request': request, 'model_identity': self.identity, 'base_url': CONFIG['base_urls'][index], 'media_sha256': video['sha256'], 'actual_frame_ids': [f['frame_id'] for f in frames], 'video_frames': len(video['sampled_frames']), 'extra_images': len(images), 'estimated_prompt_tokens': estimate, 'status': 'error'}
        try:
            for attempt in range(3):
                try:
                    response = await self.clients[index].post('/chat/completions', json=request)
                    response.raise_for_status()
                    break
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                        raise ValueError(f'event_v22:http:{exc.response.status_code}:{exc.response.text[:1500]}') from exc
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)
            body = response.json()
            record.update(raw_response=body, usage=body.get('usage'))
            if body['choices'][0]['finish_reason'] != 'stop':
                raise ValueError(f'event_v22:finish:{body["choices"][0]["finish_reason"]}')
            result = json.loads(body['choices'][0]['message']['content'])
            record['result'] = result
            validate(stage, result, payload, frames)
            record['status'] = 'ok'
            return record
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}:{exc}'
            raise
        finally:
            record['seconds'] = time.monotonic() - start
            save_json(path, record)
            brief = {k: v for k, v in record.items() if k not in ['request', 'raw_response', 'result']}
            self.calls.append(brief)
            print(json.dumps(brief), flush=True)
            self.queue.put_nowait(index)


async def verify_events(pool, case, clip, events, run_id):
    by_id = {f['frame_id']: f for f in clip['media_frames']}
    verdicts, omissions, keys = [], [], []
    for start in range(0, len(events), 3):
        group = events[start:start + 3]
        refs = {i for e in group for i in e['evidence_frame_ids']}
        images = sorted([by_id[i] for i in refs], key=lambda f: f['source_pts_s'])
        if len(images) > CONFIG['max_verifier_images']:
            raise ValueError('event_v22:verifier_image_budget')
        payload = dict(base_payload(case, clip, images), claims=group)
        response = await pool.call('verify', payload, clip['video'], images, run_id)
        verdicts.extend(response['result']['verdicts'])
        omissions.extend(response['result']['omissions'])
        keys.append(response['cache_key'])
    return {'verdicts': verdicts, 'omissions': omissions, 'cache_keys': keys}


async def process_clip(pool, record, clip, branch='B'):
    case = record['case']
    run_id = f'{branch}/{clip["clip_id"]}'
    path = FOLDER / 'runs' / branch / f'{clip["clip_id"]}.json'
    output = {'run_id': run_id, 'case_id': case['case_id'], 'clip_id': clip['clip_id'], 'branch': branch, 'video_path': clip['video']['path'], 'core_interval_s': [clip['core_frames'][0]['source_pts_s'], clip['core_frames'][-1]['source_pts_s']], 'formal_release': False, 'human_review': False, 'stages': {}, 'status': 'error'}
    images = key_images(clip['core_frames'], CONFIG['key_images'])
    payload = base_payload(case, clip, images)
    try:
        r = await pool.call('observe', payload, clip['video'], images, run_id)
        output['stages']['observe'] = r['cache_key']
        output['observation'] = r['result']
        events = events_from(r['result'], clip['clip_id'], media_manifest(clip['video'], images))
        output['events'] = events
        save_json(path, output)
        verification = await verify_events(pool, case, clip, events, run_id)
        output['verification'] = verification
        supported = {r['claim_id'] for r in verification['verdicts'] if r['verdict'] == 'supported'}
        accepted = [e for e in events if e['event_id'] in supported]
        if not accepted:
            output['status'] = 'held_no_supported_facts'
            return output
        evidence = dict(payload, events=accepted, gt_rows=gt_rows(case, clip), normative_reference=None, annotation_warning='GT spans may extend beyond this core. No GT-only answer facts allowed.')
        r = await pool.call('reconcile', evidence, clip['video'], images, run_id)
        output['reconciliation'] = r['result']
        output['stages']['reconcile'] = r['cache_key']
        rejected = set(r['result']['visual_error_event_ids'])
        accepted = sorted([e for e in accepted if e['event_id'] not in rejected], key=lambda e: (e['evidence_span_s'][0], e['evidence_span_s'][1]))
        output['screened_events'] = accepted
        if not accepted:
            output['status'] = 'held_reconciliation'
            return output
        evidence.update(events=accepted, allowed_event_ids=[e['event_id'] for e in accepted], reconciliation=output['reconciliation'])
        r = await pool.call('compose', evidence, clip['video'], images, run_id)
        output['stages']['compose'] = r['cache_key']
        output['selection'] = r['result']
        output['qa'] = render_answer(r['result'], accepted)
        output['status'] = 'pending_human' if output['qa'] else 'held_unanswerable'
    except Exception as exc:
        output['error'] = f'{type(exc).__name__}:{exc}'
    finally:
        save_json(path, output)
    return output
