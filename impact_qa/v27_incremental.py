import asyncio
import copy
import time
from collections import Counter
from pathlib import Path

from impact_qa.common import ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.v26_data import CONFIG, FOLDER
from impact_qa.structured_video_client import StructuredVideoPool
from impact_qa.v27_pipeline import generated_schema, review_schema, selection_schema
from impact_qa.v27_questions import validate_generated, validate_review, validate_selection


PARENT = ROOT / CONFIG['parent_output_root']
PROMPT_DIR = ROOT / CONFIG['prompt_dir']


def _parent_questions():
    path = PARENT / 'questions.jsonl'
    return read_jsonl(path) if path.exists() else []


def _parent_clips():
    return {row['clip_id']: row for row in read_jsonl(PARENT / 'clips.jsonl')}


def _parent_plans():
    return sorted((PARENT / 'plans').glob('*.json'))


def _candidate_from_parent(question, existing_ids):
    if question.get('kind') != 'detailed_operation':
        return None
    fact = (question.get('reference_facts') or [{}])[0]
    if fact.get('phase_count') != 1:
        return None
    if question['candidate_id'] in existing_ids:
        return None
    phase = fact.get('operation_phases', [{}])[0]
    if len(phase.get('key_actions', [])) < 2:
        return None
    candidate = copy.deepcopy(question)
    source_id = question['candidate_id']
    candidate_id = question['clip_id'] + '_detailed_incremental_r1'
    candidate['candidate_id'] = candidate_id
    candidate['question_id'] = candidate_id
    candidate['pair_id'] = candidate_id
    candidate['source_candidate_id'] = source_id
    candidate['topic'] = 'Ask for a concise description of the meaningful tool-and-component actions within this single operation phase, in order. Do not list hand motions.'
    candidate['answer_constraints'] = {
        'required_terms': list(fact.get('required_phrases', [])),
        'max_words': 75,
        'max_sentences': 3,
        'summarize_phases': False,
        'single_phase_summary': True,
        'omit_hand_motion_changes': True,
    }
    return candidate


def _compact_candidate(candidate):
    fact = candidate['reference_facts'][0]
    phase = fact.get('operation_phases', [{}])[0]
    return {
        'candidate_id': candidate['candidate_id'],
        'kind': candidate['kind'],
        'topic': candidate['topic'],
        'answer_constraints': candidate['answer_constraints'],
        'selection_rule': 'include only when the single phase and at least two meaningful actions are visibly supported',
        'action_count': len(phase.get('key_actions', [])),
        'phase_count': 1,
        'gt_facts': [{
            'fact_id': fact['fact_id'],
            'operation_phases': [{key: phase[key] for key in ['operation', 'target', 'tools_in_phase', 'key_actions'] if key in phase}],
            'phase_count': 1,
            'event_count': fact.get('event_count', 0),
            'required_terms': fact.get('required_phrases', []),
        }],
    }


def prepare():
    FOLDER.mkdir(parents=True, exist_ok=True)
    for name in ['results', 'inputs', 'api_cache', 'api_cache_failures', 'runs', 'revisions']:
        (FOLDER / name).mkdir(parents=True, exist_ok=True)
    clips = _parent_clips()
    existing_ids = {row['question_id'] for row in _parent_questions()}
    candidates = []
    seen_clips = set()
    for plan_path in _parent_plans():
        plan = read_json(plan_path)
        for question in plan.get('open_qa_candidates', []):
            candidate = _candidate_from_parent(question, existing_ids)
            if candidate is None or candidate['clip_id'] in seen_clips:
                continue
            if candidate['clip_id'] not in clips:
                continue
            media_input = PARENT / 'inputs' / (candidate['clip_id'] + '.json')
            if not media_input.exists():
                continue
            candidate['clip'] = clips[candidate['clip_id']]
            candidate['media_input_path'] = str(media_input.relative_to(ROOT))
            candidates.append(candidate)
            seen_clips.add(candidate['clip_id'])
    candidates.sort(key=lambda row: row['candidate_id'])
    save_jsonl(FOLDER / 'candidates.jsonl', candidates)
    save_json(FOLDER / 'selection_summary.json', {
        'version': CONFIG['version'],
        'parent_output_root': CONFIG['parent_output_root'],
        'parent_question_count': len(existing_ids),
        'supplemental_candidate_count': len(candidates),
        'candidate_kind': 'detailed_operation_single_phase',
        'selection_policy': 'one extra candidate per clip; existing question IDs are excluded',
        'formal_release': False,
    })
    save_json(FOLDER / 'frozen.json', {
        'config': CONFIG,
        'parent_manifest_hash': fingerprint((PARENT / 'manifest.jsonl').read_text()),
        'parent_questions_hash': fingerprint((PARENT / 'questions.jsonl').read_text()),
        'prompt_hashes': {name: fingerprint((PROMPT_DIR / (name + '.txt')).read_text()) for name in ['select', 'generate', 'review']},
    })
    _export_status('prepared', candidates)
    print({'parent_questions': len(existing_ids), 'supplemental_candidates': len(candidates)}, flush=True)
    return candidates


def _media_for(candidate):
    value = read_json(ROOT / candidate['media_input_path'])
    media = value.get('media')
    if not media or not Path(media['path']).exists():
        raise FileNotFoundError('incremental:parent_media_missing:' + candidate['clip_id'])
    return media


def _selection_payload(candidate, media):
    clip = candidate['clip']
    return {
        'case_id': candidate['candidate_id'] + '_V',
        'workflow': clip['workflow'],
        'clip_duration_s': clip['duration_s'],
        'video_sampling': [{'frame_id': f['frame_id'], 'local_s': f['local_pts_s']} for f in media['sampled_frames']],
        'question_candidates': [_compact_candidate(candidate)],
        'rules': {
            'selection_only': 'Select the candidate ID; do not write a question or answer.',
            'single_phase_allowed': True,
            'minimum_meaningful_actions': 2,
        },
    }


async def _run_candidate(pool, candidate):
    cid = candidate['candidate_id']
    result_path = FOLDER / 'results' / (cid + '.json')
    media = _media_for(candidate)
    record = {
        'candidate_id': cid,
        'source_candidate_id': candidate['source_candidate_id'],
        'clip_id': candidate['clip_id'],
        'kind': candidate['kind'],
        'status': 'running',
        'parent_output_root': CONFIG['parent_output_root'],
        'formal_release': False,
        'started_at': time.time(),
    }
    save_json(result_path, record)
    try:
        frames = [f['frame_id'] for f in media['sampled_frames']]
        selection = await pool.call(
            'v27_incremental_select',
            (PROMPT_DIR / 'select.txt').read_text(),
            _selection_payload(candidate, media),
            selection_schema([candidate], frames),
            CONFIG['selection_tokens'],
            video=media,
            validator=lambda value: validate_selection(value, [candidate], media['sampled_frames']),
        )
        row = selection['result']['items'][0]
        record['selection'] = selection['result']
        record['selection_cache_key'] = selection['cache_key']
        record['selected'] = bool(row['include'])
        record['selection_reason'] = row['reason']
        if not row['include']:
            record.update(status='completed', questions=[])
            save_json(result_path, record)
            return record

        selected = copy.deepcopy(candidate)
        selected['selection_evidence_frame_ids'] = row['evidence_frame_ids']
        selected['selection_visual_support'] = row['visual_support']
        payload = {
            'case_id': cid + '_V',
            'workflow': candidate['clip']['workflow'],
            'clip_duration_s': candidate['clip']['duration_s'],
            'time_scope': 'All times are relative to the complete clip.',
            'video_samples': [{'local_s': f['local_pts_s'], 'frame_id': f['frame_id']} for f in media['sampled_frames']],
            'open_qa_topics': [_compact_candidate(selected)],
            'selection_decision': [{'candidate_id': cid, 'visual_support': row['visual_support'], 'evidence_frame_ids': row['evidence_frame_ids']}],
        }
        generation_errors = []
        for attempt in range(4):
            generation_prompt = (PROMPT_DIR / 'generate.txt').read_text()
            if generation_errors:
                required = ', '.join(selected['answer_constraints'].get('required_terms', []))
                generation_prompt += (
                    '\nPrevious contract violation: ' + generation_errors[-1]
                    + '. Regenerate the same single QA. The answer must contain these exact supplied names verbatim: '
                    + required + '. Do not shorten, merge, or paraphrase those names. '
                    + 'For each required name, copy the complete phrase exactly as supplied into the answer. '
                    + 'Output JSON only.'
                )
            try:
                generated = await pool.call(
                    'v27_incremental_generate' if attempt == 0 else f'v27_incremental_generate_repair_{attempt}',
                    generation_prompt,
                    payload,
                    generated_schema([selected], frames),
                    CONFIG['generation_tokens'],
                    video=media,
                    validator=lambda value: validate_generated(value, [selected], media['sampled_frames']),
                )
                break
            except ValueError as exc:
                if 'v27_contract:' not in str(exc) or attempt == 3:
                    raise
                generation_errors.append(str(exc))
                record['generation_contract_repairs'] = list(generation_errors)
        record['generation'] = generated['result']
        record['generation_cache_key'] = generated['cache_key']
        review = await pool.call(
            'v27_incremental_review',
            (PROMPT_DIR / 'review.txt').read_text(),
            dict(payload, candidates=generated['result']['items']),
            review_schema([selected]),
            CONFIG['review_tokens'],
            video=media,
            validator=lambda value: validate_review(value, [selected]),
        )
        record['review'] = review['result']
        record['review_cache_key'] = review['cache_key']
        item = generated['result']['items'][0]
        decision = review['result']['items'][0]
        keep = decision['verdict'] == 'keep' and item['visual_support'] != 'conflicts_with_gt'
        record['questions'] = [{
            'question_id': cid,
            'pair_id': cid,
            'clip_id': candidate['clip_id'],
            'kind': 'detailed_operation',
            'question': item['question'],
            'answer': item['answer'],
            'source_fact_ids': item['source_fact_ids'],
            'gt_source_ids': candidate['gt_source_ids'],
            'arm': 'V_incremental_r1',
            'visual_support': decision['visual_support'],
            'generator_visual_support': item['visual_support'],
            'evidence_frame_ids': item['evidence_frame_ids'],
            'evidence_note': item['evidence_note'],
            'automatic_review': decision,
            'status': 'candidate' if keep else 'held',
            'human_review': 'unreviewed',
            'source_candidate_id': candidate['source_candidate_id'],
            'parent_output_root': CONFIG['parent_output_root'],
        }]
        record['status'] = 'completed'
    except Exception as exc:
        record.update(status='error', error=f'{type(exc).__name__}:{exc}', questions=[])
    record['finished_at'] = time.time()
    save_json(result_path, record)
    return record


def _load_incremental_records():
    rows = []
    for path in sorted((FOLDER / 'results').glob('*.json')):
        try:
            value = read_json(path)
        except Exception:
            continue
        if value.get('candidate_id'):
            rows.append(value)
    return rows


def _export_status(state, candidates):
    records = _load_incremental_records()
    incremental_questions = [q for r in records for q in r.get('questions', [])]
    parent_questions = _parent_questions()
    existing = {q['question_id'] for q in parent_questions}
    merged = parent_questions + [q for q in incremental_questions if q['question_id'] not in existing]
    save_jsonl(FOLDER / 'incremental_questions.jsonl', incremental_questions)
    save_jsonl(FOLDER / 'merged_questions.jsonl', merged)
    save_jsonl(FOLDER / 'merged_reviews.jsonl', [
        {'question_id': q['question_id'], 'clip_id': q['clip_id'], 'review': q.get('automatic_review', {}), 'human_review': q.get('human_review', 'unreviewed')}
        for q in merged
    ])
    counts = Counter(r.get('status') for r in records)
    qcounts = Counter(q.get('status') for q in incremental_questions)
    progress = {
        'state': state,
        'updated_at': time.time(),
        'parent_question_count': len(parent_questions),
        'supplemental_candidate_count': len(candidates),
        'supplemental_resolved_count': sum(1 for r in records if r.get('status') in ['completed', 'held']),
        'supplemental_pending_count': len(candidates) - sum(1 for r in records if r.get('status') in ['completed', 'held']),
        'supplemental_record_status': dict(counts),
        'supplemental_question_count': len(incremental_questions),
        'supplemental_question_status': dict(qcounts),
        'merged_question_count': len(merged),
        'formal_release': False,
        'human_review': 'pending',
    }
    save_json(FOLDER / 'progress.json', progress)
    return progress


async def run(limit=0):
    import httpx
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('incremental_preflight:cuda_unavailable')
    for url in CONFIG['base_urls']:
        response = httpx.get(url + '/models', timeout=10, trust_env=False)
        response.raise_for_status()
        if CONFIG['model'] not in [item['id'] for item in response.json()['data']]:
            raise RuntimeError('incremental_preflight:wrong_model:' + url)
    candidates = read_jsonl(FOLDER / 'candidates.jsonl')
    records = {r.get('candidate_id'): r for r in _load_incremental_records() if r.get('status') in ['completed', 'held']}
    pending = [c for c in candidates if c['candidate_id'] not in records]
    selected = pending[:limit] if limit else pending
    pool = StructuredVideoPool(CONFIG, FOLDER)
    queue = asyncio.Queue()
    for candidate in selected:
        queue.put_nowait(candidate)

    async def worker():
        while True:
            try:
                candidate = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                value = await _run_candidate(pool, candidate)
                print({'candidate_id': candidate['candidate_id'], 'status': value.get('status'), 'selected': value.get('selected'), 'question_count': len(value.get('questions', []))}, flush=True)
            finally:
                queue.task_done()

    try:
        await asyncio.gather(*(worker() for _ in range(CONFIG['workers'])))
    finally:
        await pool.close()
        save_json(FOLDER / 'runs' / (str(time.time_ns()) + '.json'), {'limit': limit, 'requests': pool.calls})
        progress = _export_status('pilot_finished' if limit else 'full_finished', candidates)
        print(progress, flush=True)
