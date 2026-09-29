import asyncio
import fcntl
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import torch

from impact_qa.common import ROOT, read_json, read_jsonl, save_json
from impact_qa.event_v22 import TEXT, arr, choice, obj
from impact_qa.structured_video_client import StructuredVideoPool


FOLDER = ROOT / 'outputs/impact_qa/step_v24'
OLD = ROOT / 'outputs/impact_qa/history_v23'
CONFIG = read_json(ROOT / 'configs/impact_qa/history_v23.json')
KINDS = ['execution_correctness', 'tool_identity', 'observed_order', 'step_completion']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def packet(record, result):
    case = record['case']
    view = case['view']
    start, end = case['source_interval_inclusive']
    context = {r['source_id']: r for r in case['shared_gt']['atomic_context']}
    sources = []
    for source in case['source_catalog']:
        sid, value = source['source_id'], source['value']
        if sid != 'atr_' + view and not sid.startswith(view + '_'):
            continue
        if value['start_frame'] > end or value['end_frame'] < start:
            continue
        if digest(ROOT / source['path']) != source['sha256']:
            raise ValueError('step_v24:source_changed:' + sid)
        sources.append(dict(source, interpretation=context.get(sid), kind='atr' if sid.startswith('atr_') else 'atomic_action', visible_intersection_frames=[max(start, value['start_frame']), min(end, value['end_frame'])]))
    path = ROOT / f"annotations/impact/IMPACT-v1.1/annotations/TAS-S/{view}/{case['video_id']}.json"
    coarse = read_json(path)
    for i, row in enumerate(coarse['segments']):
        if row['f_start'] <= end and row['f_end'] >= start and row['label'] != 'null':
            sources.append({'source_id': f'tas_s_{i}', 'kind': 'step_name_only', 'path': str(path.relative_to(ROOT)), 'sha256': digest(path), 'pointer': f'/segments/{i}', 'value': {k: row[k] for k in ['label', 'f_start', 'f_end']}})
    asr = ROOT / f"annotations/impact/IMPACT-v1.1/annotations/ASR/annotations/{case['video_id']}_asr.json"
    if asr.exists():
        raise ValueError('step_v24:completion_state_adapter_required_for_new_case')
    revision = read_json(OLD / 'qa_visual_revision' / (case['case_id'] + '.json'))
    video = revision['video']
    if digest(video['path']) != video['sha256']:
        raise ValueError('step_v24:media_changed')
    payload = {'case_id': case['case_id'], 'view': view, 'source_interval_s': case['interval_s'], 'source_interval_inclusive': [start, end], 'source_catalog': sources, 'events': [e for row in result['ledger'] for e in row['events']], 'clip_ledger': result['ledger'], 'completion_evidence': None, 'completion_evidence_status': 'No same-trial ASR end-state label available; do not borrow another trial or view.', 'normative_order': None, 'correct_replacement_tool': None, 'video_start_source_pts_s': video['sampled_frames'][0]['source_pts_s'], 'sampling_source_pts_s': [f['source_pts_s'] for f in video['sampled_frames']]}
    return payload, video


def schema(payload):
    item = obj({'kind': choice(KINDS), 'operation': TEXT, 'question': TEXT, 'answer': TEXT, 'verdict': choice(['yes', 'no', 'descriptive', 'unknown']), 'eligibility': choice(['answerable', 'needs_more_evidence']), 'source_ids': arr(choice([s['source_id'] for s in payload['source_catalog']]), 1, 8), 'event_ids': arr(choice([e['event_id'] for e in payload['events']]), 1, 8), 'evidence_basis': TEXT})
    return obj({'items': arr(item, 4, 4)})


def validate(value, payload):
    if sorted(q['kind'] for q in value['items']) != sorted(KINDS):
        raise ValueError('step_v24:missing_or_duplicate_kind')
    ids = [e['event_id'] for e in payload['events']] + [s['source_id'] for s in payload['source_catalog']]
    for q in value['items']:
        if not q['operation'].strip() or any(s in q['question'] + q['answer'] for s in ids):
            raise ValueError('step_v24:invalid_prose')
        if any(s in q['question'].lower() for s in ['describe', 'summarize', 'what happened in the video']):
            raise ValueError('step_v24:generic_description_question')
        if any(s in (q['question'] + q['answer']).lower() for s in ['annotat', 'ground truth', 'error_wrong_tool', 'completion_state', 'on the gearbox housing drive shaft']):
            raise ValueError('step_v24:annotation_leakage_or_unsupported_receiver')
        if 'bearing plate' in q['question'].lower() and not any(s.startswith('tas_s_') for s in q['source_ids']):
            raise ValueError('step_v24:missing_step_name_source')
        if q['kind'] == 'tool_identity' and q['verdict'] != 'descriptive':
            raise ValueError('step_v24:duplicated_correctness_question')
        if (q['verdict'] == 'unknown') != (q['eligibility'] == 'needs_more_evidence'):
            raise ValueError('step_v24:eligibility_mismatch')
        if q['kind'] == 'step_completion' and payload['completion_evidence'] is None and q['verdict'] != 'unknown':
            raise ValueError('step_v24:unsupported_completion_verdict')


async def main():
    if not torch.cuda.is_available():
        raise RuntimeError('step_v24:cuda_unavailable')
    for url in CONFIG['base_urls']:
        response = httpx.get(url + '/models', timeout=10, trust_env=False)
        response.raise_for_status()
        if CONFIG['model'] not in [r['id'] for r in response.json()['data']]:
            raise RuntimeError('step_v24:model_missing')
    records = {r['case']['case_id']: r for r in read_jsonl(ROOT / CONFIG['source_cases'])}
    packets = [packet(records[r['case_id']], r) for r in read_json(OLD / 'results.json')]
    save_json(FOLDER / 'precheck.json', {'torch': torch.__version__, 'cuda': torch.version.cuda, 'gpu_count': torch.cuda.device_count(), 'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used', '--format=csv,noheader'], text=True), 'first10_inputs': [{'case_id': p['case_id'], 'sources': len(p['source_catalog']), 'frames': len(v['sampled_frames']), 'completion_evidence': p['completion_evidence']} for p, v in packets]})
    pool = StructuredVideoPool(CONFIG, FOLDER)
    async def run(payload, video):
        save_json(FOLDER / 'inputs' / (payload['case_id'] + '.json'), payload)
        output = {'case_id': payload['case_id'], 'status': 'error', 'formal_release': False}
        try:
            response = await pool.call('step_qa', (ROOT / 'prompts/impact_qa/v24_step_qa.txt').read_text(), payload, schema(payload), 4096, video=video, validator=lambda value: validate(value, payload))
            items = response['result']['items']
            output.update(status='pending_review', qa={'items': [q for q in items if q['eligibility'] == 'answerable']}, held_items=[q for q in items if q['eligibility'] != 'answerable'], cache_key=response['cache_key'])
        except Exception as exc:
            output['error'] = str(exc)
        save_json(FOLDER / 'results' / (payload['case_id'] + '.json'), output)
        return output
    try:
        results = await asyncio.gather(*(run(p, v) for p, v in packets))
        save_json(FOLDER / 'results.json', results)
        summary = {'cases': len(results), 'completed': sum(r['status'] == 'pending_review' for r in results), 'qa': sum(len(r.get('qa', {}).get('items', [])) for r in results), 'held': sum(len(r.get('held_items', [])) for r in results), 'new_requests': len(pool.calls), 'input_tokens': sum((r.get('usage') or {}).get('prompt_tokens', 0) for r in pool.calls), 'output_tokens': sum((r.get('usage') or {}).get('completion_tokens', 0) for r in pool.calls), 'calls': pool.calls, 'formal_release': False}
        save_json(FOLDER / ('summary.json' if pool.calls else 'resume_summary.json'), summary)
        print(json.dumps(summary), flush=True)
    finally:
        await pool.close()


if __name__ == '__main__':
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main())
