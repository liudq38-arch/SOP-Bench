import asyncio
import re
import time
from collections import Counter
from pathlib import Path

from impact_qa.common import ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.v26_data import CONFIG, CONFIG_PATH, FOLDER, digest
from impact_qa.v26_media import prepare_media
from impact_qa.v26_questions import build_questions, render_units, validate_generated, validate_plan


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def arr(items, lo, hi):
    return {'type': 'array', 'items': items, 'minItems': lo, 'maxItems': hi}


def enum(values):
    return {'type': 'string', 'enum': list(values)}


TEXT = {'type': 'string'}
VISUAL = ['not_applicable', 'supports_visible_outcome', 'cannot_independently_confirm', 'conflicts_with_gt']


def compact_plans(plans):
    compact = []
    for q in plans:
        facts = []
        for fact in q['reference_facts']:
            value = {k: v for k, v in fact.items() if k not in ['source_ids', 'event_ids', 'covered_event_ids']}
            if q['kind'] == 'action_sequence':
                value.pop('interval_s', None)
            facts.append(value)
        compact.append({'question_id': q['question_id'], 'kind': q['kind'], 'question': q['question'], 'reference_facts': facts})
    return compact


def generated_schema(plans):
    fids = [f['fact_id'] for q in plans for f in q['reference_facts']]
    unit = obj({'fact_id': enum(fids), 'text': TEXT})
    item = obj({'question_id': enum([q['question_id'] for q in plans]), 'units': arr(unit, 1, max(len(q['reference_facts']) for q in plans)), 'visual_support': enum(VISUAL), 'evidence_note': TEXT})
    return obj({'items': arr(item, len(plans), len(plans))})


def review_schema(plans):
    fids = [f['fact_id'] for q in plans for f in q['reference_facts']]
    item = obj({'question_id': enum([q['question_id'] for q in plans]), 'verdict': enum(['keep', 'hold']), 'severity': enum(['none', 'minor', 'major']), 'reason': TEXT, 'visual_support': enum(VISUAL), 'unsupported_fact_ids': arr(enum(fids), 0, len(fids))})
    return obj({'items': arr(item, len(plans), len(plans))})


def validate_review(value, plans, arm):
    if sorted(x['question_id'] for x in value['items']) != sorted(q['question_id'] for q in plans):
        raise ValueError('v26_review:question_coverage')
    allowed = {q['question_id']: {f['fact_id'] for f in q['reference_facts']} for q in plans}
    for r in value['items']:
        if any(f not in allowed[r['question_id']] for f in r['unsupported_fact_ids']):
            raise ValueError('v26_review:wrong_question_fact')
        if arm == 'A' and r['visual_support'] != 'not_applicable':
            raise ValueError('v26_review:arm_a_visual')
        if arm == 'B' and r['visual_support'] == 'not_applicable':
            raise ValueError('v26_review:arm_b_visual')
        if r['verdict'] == 'keep' and (r['severity'] != 'none' or r['unsupported_fact_ids'] or r['visual_support'] == 'conflicts_with_gt'):
            raise ValueError('v26_review:keep_conflict')


def freeze(manifest):
    files = [str(CONFIG_PATH.relative_to(ROOT)), 'impact_qa/v26_data.py', 'impact_qa/v26_questions.py', 'impact_qa/v26_media.py', 'impact_qa/v26_pipeline.py', 'impact_qa/structured_video_client.py', 'scripts/run_component_v26.py', 'prompts/impact_qa/v26_generate.txt', 'prompts/impact_qa/v26_review.txt']
    value = {'config': CONFIG, 'files': {p: digest(str(ROOT / p)) for p in files}, 'manifest_hash': fingerprint(manifest)}
    path = FOLDER / 'frozen.json'
    if path.exists() and read_json(path) != value:
        raise ValueError('v26_freeze:configuration_or_code_changed_requires_revision')
    save_json(path, value)
    return fingerprint(value)


async def run_arm(pool, clip, plans, media, arm, frozen_hash):
    cid = clip['clip_id']
    path = FOLDER / 'results' / (cid + '_' + arm + '.json')
    media_key = media['sha256'] if media else fingerprint({'clip_id': cid, 'start_frame': clip['start_frame'], 'end_frame_exclusive': clip['end_frame_exclusive'], 'fps': clip['fps']})
    inputs_key = fingerprint([frozen_hash, plans, media_key, arm])
    if path.exists():
        record = read_json(path)
        if record.get('inputs_key') == inputs_key and record['status'] in ['completed', 'held']:
            return record
    record = {'clip_id': cid, 'arm': arm, 'inputs_key': inputs_key, 'status': 'running', 'started_at': time.time(), 'formal_release': False}
    save_json(path, record)
    video = media if arm == 'B' else None
    payload = {'case_id': cid + '_' + arm, 'arm': arm, 'workflow': clip['workflow'], 'clip_duration_s': (clip['end_frame_exclusive'] - clip['start_frame']) / clip['fps'], 'time_scope': 'All displayed times are relative to this complete clip. No external history is supplied.', 'question_plan': compact_plans(plans)}
    if arm == 'B':
        if media is None:
            raise ValueError('v26_media:video_arm_requires_media')
        payload['video_samples'] = [{'local_s': f['local_pts_s'], 'frame_id': f['frame_id']} for f in media['sampled_frames']]
        payload['sampling_warning'] = 'The complete clip is uniformly sampled; fine or short actions may not be independently visible.'
    try:
        prompt = (ROOT / 'prompts/impact_qa/v26_generate.txt').read_text()
        try:
            generation = await pool.call('v26_generate', prompt, payload, generated_schema(plans), CONFIG['generation_tokens'], video=video, validator=lambda v: validate_generated(v, plans, arm))
        except ValueError as exc:
            if not str(exc).startswith('v26_contract:'):
                raise
            record['contract_repair_reason'] = str(exc)
            repair_prompt = prompt + '\nOne previous response failed this contract: ' + str(exc) + '. Preserve all required phrases exactly and all fact IDs in order. This is the single allowed contract repair.'
            generation = await pool.call('v26_generate_repair', repair_prompt, payload, generated_schema(plans), CONFIG['generation_tokens'], video=video, validator=lambda v: validate_generated(v, plans, arm))
        record['generation'] = generation['result']
        record['generation_cache_key'] = generation['cache_key']
        save_json(path, record)
        review_payload = dict(payload, candidates=generation['result']['items'])
        review = await pool.call('v26_review', (ROOT / 'prompts/impact_qa/v26_review.txt').read_text(), review_payload, review_schema(plans), CONFIG['review_tokens'], video=video, validator=lambda v: validate_review(v, plans, arm))
        record['review'] = review['result']
        record['review_cache_key'] = review['cache_key']
        by_q = {q['question_id']: q for q in plans}
        decisions = {r['question_id']: r for r in review['result']['items']}
        results = []
        for generated in generation['result']['items']:
            q = by_q[generated['question_id']]
            decision = decisions[q['question_id']]
            keep = decision['verdict'] == 'keep' and generated['visual_support'] != 'conflicts_with_gt'
            results.append({**q, 'arm': arm, 'answer': render_units(q['kind'], generated['units'], q['reference_facts']), 'answer_units': generated['units'], 'visual_support': decision['visual_support'], 'generator_visual_support': generated['visual_support'], 'evidence_note': generated['evidence_note'], 'automatic_review': decision, 'status': 'candidate' if keep else 'held', 'human_review': 'unreviewed'})
        record['questions'] = results
        record['status'] = 'completed' if any(q['status'] == 'candidate' for q in results) else 'held'
    except Exception as exc:
        record.update(status='error', error=f'{type(exc).__name__}:{exc}')
    record['finished_at'] = time.time()
    save_json(path, record)
    return record


async def process_clip(pool, clip, frozen_hash):
    trial = read_json(FOLDER / 'trials' / (clip['video_id'] + '.json'))
    for s in trial['source_catalog'].values():
        if digest(str(ROOT / s['source_path'])) != s['sha256']:
            raise ValueError('v26_sources:changed_annotation:' + clip['video_id'])
    questions, mcq, excluded = build_questions(trial, clip)
    validate_plan(trial, clip, questions, mcq)
    media = await asyncio.to_thread(prepare_media, trial, clip) if CONFIG.get('prepare_media', True) else None
    save_json(FOLDER / 'inputs' / (clip['clip_id'] + '.json'), {'clip': clip, 'media': media, 'questions': questions, 'mcq': mcq, 'excluded': excluded, 'source_catalog': trial['source_catalog']})
    arms = CONFIG.get('arms', ['A', 'B'])
    if not arms:
        raise ValueError('v26_config:arms_empty')
    return await asyncio.gather(*(run_arm(pool, clip, questions, media, arm, frozen_hash) for arm in arms))


def export_status(state='running'):
    manifest = read_jsonl(FOLDER / 'manifest.jsonl')
    records = [read_json(p) for p in sorted((FOLDER / 'results').glob('*.json'))] if (FOLDER / 'results').exists() else []
    qs = [q for r in records for q in r.get('questions', [])]
    save_jsonl(FOLDER / 'questions.jsonl', qs)
    save_jsonl(FOLDER / 'reviews.jsonl', [{'question_id': q['question_id'], 'clip_id': q['clip_id'], 'arm': q['arm'], 'review': q['automatic_review'], 'human_review': 'unreviewed'} for q in qs])
    cases = []
    for clip in read_jsonl(FOLDER / 'clips.jsonl'):
        p = FOLDER / 'media_manifests' / (clip['clip_id'] + '.json')
        if p.exists():
            v = read_json(p)
            clip = dict(clip, clip_path=v['path'], clip_sha256=v['sha256'], source_start_s=v['source_start_pts_s'], source_end_s=v['source_end_pts_s'], clock='decoded_pts_validated', media_manifest=str(p.relative_to(ROOT)))
        cases.append(clip)
    save_jsonl(FOLDER / 'clips.jsonl', cases)
    progress = {'state': state, 'updated_at': time.time(), 'selected_clips': len(manifest), 'arm_status': dict(Counter(r['status'] for r in records)), 'question_status': dict(Counter(q['status'] for q in qs)), 'question_kinds': dict(Counter(q['kind'] for q in qs)), 'human_review': 'pending', 'formal_release': False}
    save_json(FOLDER / 'progress.json', progress)
    return progress
