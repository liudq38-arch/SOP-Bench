import asyncio
import time
from collections import Counter
from pathlib import Path

from impact_qa.common import ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.v26_data import CONFIG, CONFIG_PATH, FOLDER, OPTIONS, digest, prepare_index
from impact_qa.v27_media import prepare_media
from impact_qa.structured_video_client import StructuredVideoPool
from impact_qa.v27_questions import (
    build_candidates,
    validate_generated,
    validate_review,
    validate_selection,
)


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def arr(items, lo, hi):
    return {'type': 'array', 'items': items, 'minItems': lo, 'maxItems': hi}


def enum(values):
    return {'type': 'string', 'enum': list(values)}


TEXT = {'type': 'string'}
VISUAL = ['supports_visible_outcome', 'cannot_independently_confirm', 'conflicts_with_gt']
PROMPT_DIR = CONFIG.get('prompt_dir', 'prompts/impact_qa/v27')
MCQ_VISUAL_CHUNK_SIZE = 8


def _chunks(rows, size):
    return [rows[index:index + size] for index in range(0, len(rows), size)]


def prompt_path(name):
    return ROOT / PROMPT_DIR / (name + '.txt')


def compact_candidates(candidates):
    result = []
    for candidate in candidates:
        value = {k: v for k, v in candidate.items() if k not in ['gt_facts', 'question']}
        if candidate['kind'] == 'detailed_operation':
            value['action_count'] = candidate.get('action_count', 0)
            value['phase_count'] = candidate.get('phase_count', 0)
        if candidate['kind'] == 'mcq_anomaly_clip':
            value['gt_facts'] = [
                {
                    'event_id': fact['event_id'],
                    'duration_s': fact['duration_s'],
                    'anomaly_types': [option['name'] for option, flag in zip(OPTIONS[1:], fact['labels']) if flag],
                    'interval_frames': fact['interval_frames'],
                }
                for fact in candidate['gt_facts']
            ]
        else:
            from impact_qa.v27_questions import _compact_gt_fact
            value['gt_facts'] = [_compact_gt_fact(fact, candidate['kind']) for fact in candidate['gt_facts']]
        result.append(value)
    return result


def apply_selection_budget(selection, candidates, maximum):
    value = {'items': [dict(row) for row in selection['items']]}
    by_id = {candidate['candidate_id']: candidate for candidate in candidates}
    gates = []
    for row in value['items']:
        candidate = by_id[row['candidate_id']]
        count = candidate.get('phase_count', 0) if candidate['kind'] == 'detailed_operation' else 0
        if row['include'] and candidate['kind'] == 'detailed_operation' and count > maximum:
            row['include'] = False
            row['reason'] = f'Excluded by the answer budget: {count} operation phases exceed the {maximum}-phase limit.'
            gates.append({'candidate_id': row['candidate_id'], 'phase_count': count, 'maximum': maximum, 'reason': row['reason']})
    return value, gates


def compact_plans(plans):
    result = []
    for candidate in plans:
        facts = []
        from impact_qa.v27_questions import _compact_gt_fact
        for fact in candidate['reference_facts']:
            facts.append(_compact_gt_fact(fact, candidate['kind']))
        result.append({
            'candidate_id': candidate['candidate_id'],
            'kind': candidate['kind'],
            'topic': candidate['topic'],
            'answer_constraints': candidate['answer_constraints'],
            'selection_visual_support': candidate.get('selection_visual_support'),
            'selection_evidence_frame_ids': candidate.get('selection_evidence_frame_ids', []),
            'gt_facts': facts,
        })
    return result


def selection_schema(candidates, frame_ids):
    item = obj({
        'candidate_id': enum([x['candidate_id'] for x in candidates]),
        'include': {'type': 'boolean'},
        'visual_support': enum(VISUAL),
        'evidence_frame_ids': arr(enum(frame_ids), 0, min(8, max(1, len(frame_ids)))),
        'reason': TEXT,
    })
    return obj({'items': arr(item, len(candidates), len(candidates))})


def generated_schema(candidates, frame_ids):
    fact_ids = sorted({f['fact_id'] for q in candidates for f in q['reference_facts']})
    item = obj({
        'candidate_id': enum([q['candidate_id'] for q in candidates]),
        'question': TEXT,
        'answer': TEXT,
        'source_fact_ids': arr(enum(fact_ids), 1, max(1, len(fact_ids))),
        'visual_support': enum(VISUAL),
        'evidence_frame_ids': arr(enum(frame_ids), 0, min(8, max(1, len(frame_ids)))),
        'evidence_note': TEXT,
    })
    return obj({'items': arr(item, len(candidates), len(candidates))})


def review_schema(plans):
    fact_ids = sorted({f['fact_id'] for q in plans for f in q['reference_facts']})
    item = obj({'question_id': enum([q['candidate_id'] for q in plans]), 'verdict': enum(['keep', 'hold']), 'severity': enum(['none', 'minor', 'major']), 'reason': TEXT, 'visual_support': enum(VISUAL), 'unsupported_fact_ids': arr(enum(fact_ids), 0, max(1, len(fact_ids)))})
    return obj({'items': arr(item, len(plans), len(plans))})


def anomaly_visual_schema(frame_ids, event_count):
    item = obj({
        'event_id': TEXT,
        'visible_abnormal_operation': {'type': 'boolean'},
        'evidence_frame_ids': arr(enum(frame_ids), 0, min(2, max(1, len(frame_ids)))),
        'observed_description': TEXT,
    })
    return obj({'items': arr(item, event_count, event_count)})


def freeze(manifest):
    runner = CONFIG.get('runner_script', 'scripts/run_component_v27.py')
    files = [
        str(CONFIG_PATH.relative_to(ROOT)),
        'impact_qa/v26_data.py',
        'impact_qa/clip_repair.py',
        'impact_qa/v26_media.py',
        'impact_qa/v27_media.py',
        'impact_qa/structured_video_client.py',
        'impact_qa/v27_questions.py',
        'impact_qa/v27_pipeline.py',
        runner,
        'scripts/audit_clip_splits.py',
        str((Path(PROMPT_DIR) / 'select.txt').as_posix()),
        str((Path(PROMPT_DIR) / 'generate.txt').as_posix()),
        str((Path(PROMPT_DIR) / 'review.txt').as_posix()),
        str((Path(PROMPT_DIR) / 'mcq_visual.txt').as_posix()),
    ]
    value = {'config': CONFIG, 'files': {p: digest(str(ROOT / p)) for p in files}, 'manifest_hash': fingerprint(manifest)}
    path = FOLDER / 'frozen.json'
    if path.exists() and read_json(path) != value:
        revision = CONFIG.get('revision')
        if not revision:
            raise ValueError('v27_freeze:configuration_or_code_changed_requires_revision')
        previous = read_json(path)
        previous_revision = previous.get('config', {}).get('revision', 'r0')
        archive = FOLDER / 'revisions' / previous_revision / 'frozen.json'
        if not archive.exists():
            save_json(archive, previous)
        save_json(FOLDER / 'revisions' / revision / 'parent_frozen.json', previous)
    save_json(path, value)
    if CONFIG.get('revision'):
        save_json(FOLDER / 'revisions' / CONFIG['revision'] / 'frozen.json', value)
    return fingerprint(value)


def selection_payload(clip, trial, candidates, media):
    question_candidates = compact_candidates(candidates)
    frames = media['sampled_frames']
    for candidate in question_candidates:
        if candidate['kind'] != 'mcq_anomaly_clip':
            continue
        for error in candidate['gt_facts']:
            a, b = error['interval_frames']
            error['local_interval_s'] = [round((a - clip['start_frame']) / clip['fps'], 3), round((b - clip['start_frame']) / clip['fps'], 3)]
            error['sampled_frame_ids'] = [f['frame_id'] for f in frames if a <= f['source_frame_index'] < b]
    return {
        'case_id': clip['clip_id'] + '_V',
        'workflow': clip['workflow'],
        'clip_duration_s': clip['duration_s'],
        'video_sampling': [{'frame_id': f['frame_id'], 'local_s': f['local_pts_s']} for f in media['sampled_frames']],
        'question_candidates': question_candidates,
        'rules': {
            'selection_only': 'Select candidate IDs; do not write answers or invent facts.',
            'duration_min_seconds': 5.0,
            'mcq_visual_requirement': 'A clip-level anomaly MCQ may be included only when a qualifying ATR anomaly is visibly supported.',
        },
    }


def validate_anomaly_visual(value, mcq, sampled_frames):
    expected = {row['event_id'] for row in mcq['qualifying_errors']}
    rows = value.get('items', [])
    if {row['event_id'] for row in rows} != expected or len(rows) != len(expected):
        raise ValueError('v27_mcq_visual:event_coverage')
    allowed = {f['frame_id'] for f in sampled_frames}
    errors = {e['event_id']: e for e in mcq['qualifying_errors']}
    frames = {f['frame_id']: f for f in sampled_frames}
    for row in rows:
        if any(frame_id not in allowed for frame_id in row['evidence_frame_ids']):
            raise ValueError('v27_mcq_visual:unknown_frame:' + row['event_id'])
        error = errors[row['event_id']]
        a, b = error['interval_frames']
        in_interval = [frame_id for frame_id in row['evidence_frame_ids'] if a <= frames[frame_id]['source_frame_index'] < b]
        if row['visible_abnormal_operation'] and (not in_interval or not row['observed_description'].strip()):
            raise ValueError('v27_mcq_visual:visible_requires_in_interval_evidence:' + row['event_id'])
        if not row['visible_abnormal_operation'] and row['evidence_frame_ids']:
            raise ValueError('v27_mcq_visual:negative_must_not_cite_evidence:' + row['event_id'])


async def run_clip(pool, clip, frozen_hash):
    cid = clip['clip_id']
    path = FOLDER / 'results' / (cid + '_V.json')
    trial = read_json(FOLDER / 'trials' / (clip['video_id'] + '.json'))
    for source_record in trial['source_catalog'].values():
        if digest(str(ROOT / source_record['source_path'])) != source_record['sha256']:
            raise ValueError('v27_sources:changed_annotation:' + clip['video_id'])
    plans, mcq, candidates, excluded = build_candidates(trial, clip)
    media = await asyncio.to_thread(prepare_media, trial, clip)
    save_json(FOLDER / 'inputs' / (cid + '.json'), {'clip': clip, 'media': media, 'plans': plans, 'mcq': mcq, 'candidates': candidates, 'excluded': excluded, 'source_catalog': trial['source_catalog']})
    selection = None
    record = {'clip_id': cid, 'arm': 'V', 'status': 'running', 'started_at': time.time(), 'formal_release': False, 'candidate_count': len(candidates)}
    save_json(path, record)
    try:
        select_prompt = prompt_path('select').read_text()
        select_payload = selection_payload(clip, trial, candidates, media)
        select = await pool.call('v27_select', select_prompt, select_payload, selection_schema(candidates, [f['frame_id'] for f in media['sampled_frames']]), CONFIG['selection_tokens'], video=media, validator=lambda value: validate_selection(value, candidates, media['sampled_frames']))
        selection, budget_gates = apply_selection_budget(select['result'], candidates, CONFIG.get('max_detail_phases', 8))
        record['model_selection'] = select['result']
        record['selection'] = selection
        record['selection_budget_gates'] = budget_gates
        record['selection_cache_key'] = select['cache_key']
        by_id = {row['candidate_id']: row for row in selection['items']}
        selected_ids = [row['candidate_id'] for row in selection['items'] if row['include']]
        selected_plans = [q for q in plans if q['candidate_id'] in selected_ids]
        for candidate in selected_plans:
            selected = by_id[candidate['candidate_id']]
            candidate['selection_evidence_frame_ids'] = selected['evidence_frame_ids']
            candidate['selection_visual_support'] = selected['visual_support']
        selected_mcq = mcq if mcq and by_id[mcq['question_id']]['include'] else None
        record['selected_question_ids'] = selected_ids
        record['selection_exclusions'] = [dict(x, selection_reason=by_id[x.get('candidate_id', '')]['reason']) for x in candidates if x['candidate_id'] not in selected_ids]
        generated_items = []
        anomaly_visual = None
        if selected_mcq:
            visual_items = []
            visual_cache_keys = []
            video_samples = [{'local_s': f['local_pts_s'], 'frame_id': f['frame_id']} for f in media['sampled_frames']]
            for chunk_index, error_chunk in enumerate(_chunks(selected_mcq['qualifying_errors'], MCQ_VISUAL_CHUNK_SIZE), 1):
                chunk_mcq = {**selected_mcq, 'qualifying_errors': error_chunk}
                visual_payload = {
                    'case_id': f'{cid}_V_mcq_visual_{chunk_index:03d}',
                    'clip_duration_s': clip['duration_s'],
                    'video_samples': video_samples,
                    'candidate_windows': [
                        {'event_id': e['event_id'], 'local_interval_s': [
                            (e['interval_frames'][0] - clip['start_frame']) / clip['fps'],
                            (e['interval_frames'][1] - clip['start_frame']) / clip['fps'],
                        ], 'sampled_frame_ids': [f['frame_id'] for f in media['sampled_frames'] if e['interval_frames'][0] <= f['source_frame_index'] < e['interval_frames'][1]]}
                        for e in error_chunk
                    ],
                    'instruction': 'Do not infer from a label. Independently report whether visibly abnormal operation is present within each interval.',
                }
                visual = await pool.call(
                    'v27_mcq_visual_check',
                    prompt_path('mcq_visual').read_text(),
                    visual_payload,
                    anomaly_visual_schema([f['frame_id'] for f in media['sampled_frames']], len(error_chunk)),
                    CONFIG['selection_tokens'],
                    video=media,
                    validator=lambda value, candidate=chunk_mcq: validate_anomaly_visual(value, candidate, media['sampled_frames']),
                )
                visual_items.extend(visual['result']['items'])
                visual_cache_keys.append(visual['cache_key'])
            anomaly_visual = {'items': visual_items}
            validate_anomaly_visual(anomaly_visual, selected_mcq, media['sampled_frames'])
            record['mcq_visual_check'] = anomaly_visual
            record['mcq_visual_cache_keys'] = visual_cache_keys
        if selected_plans:
            payload = {
                'case_id': cid + '_V',
                'workflow': clip['workflow'],
                'clip_duration_s': clip['duration_s'],
                'time_scope': 'All times are relative to the complete clip.',
                'video_samples': [{'local_s': f['local_pts_s'], 'frame_id': f['frame_id']} for f in media['sampled_frames']],
                'open_qa_topics': compact_plans(selected_plans),
                'selection_decision': [{'candidate_id': row['candidate_id'], 'visual_support': row['visual_support'], 'evidence_frame_ids': row['evidence_frame_ids']} for row in selection['items'] if row['include']],
            }
            generation_prompt = prompt_path('generate').read_text()
            generation_schema = generated_schema(selected_plans, [f['frame_id'] for f in media['sampled_frames']])
            generation_validator = lambda value: validate_generated(value, selected_plans, media['sampled_frames'])
            repair_errors = []
            for attempt in range(4):
                stage = 'v27_generate' if attempt == 0 else f'v27_generate_repair_{attempt}'
                repair_prompt = generation_prompt
                if repair_errors:
                    repair_prompt += (
                        '\nPrevious response contract violations: '
                        + ' | '.join(repair_errors[-3:])
                        + '. Regenerate every selected QA and satisfy every listed requirement. '
                        + 'Preserve exact grounded component and tool names. Keep questions natural and answers concise. '
                        + 'Return only the required JSON schema.'
                    )
                try:
                    generate = await pool.call(
                        stage, repair_prompt, payload, generation_schema,
                        CONFIG['generation_tokens'], video=media, validator=generation_validator,
                    )
                    break
                except ValueError as exc:
                    if 'v27_contract:' not in str(exc) or attempt == 3:
                        raise
                    repair_errors.append(str(exc))
                    record['generation_contract_repairs'] = list(repair_errors)
            record['generation'] = generate['result']
            record['generation_cache_key'] = generate['cache_key']
            review_payload = dict(payload, candidates=generate['result']['items'])
            review = await pool.call('v27_review', prompt_path('review').read_text(), review_payload, review_schema(selected_plans), CONFIG['review_tokens'], video=media, validator=lambda value: validate_review(value, selected_plans))
            record['review'] = review['result']
            record['review_cache_key'] = review['cache_key']
            decisions = {row['question_id']: row for row in review['result']['items']}
            by_q = {q['candidate_id']: q for q in selected_plans}
            for generated in generate['result']['items']:
                q = by_q[generated['candidate_id']]
                decision = decisions[q['candidate_id']]
                keep = decision['verdict'] == 'keep' and generated['visual_support'] != 'conflicts_with_gt'
                generated_items.append({
                    'question_id': q['candidate_id'], 'pair_id': q['pair_id'], 'clip_id': cid,
                    'kind': q['kind'], 'question': generated['question'], 'answer': generated['answer'],
                    'source_fact_ids': generated['source_fact_ids'], 'gt_source_ids': q['gt_source_ids'],
                    'arm': 'V', 'visual_support': decision['visual_support'],
                    'generator_visual_support': generated['visual_support'],
                    'evidence_frame_ids': generated['evidence_frame_ids'],
                    'evidence_note': generated['evidence_note'], 'automatic_review': decision,
                    'status': 'candidate' if keep else 'held', 'human_review': 'unreviewed',
                })
        if selected_mcq:
            decision = by_id[selected_mcq['question_id']]
            visible_event_ids = {row['event_id'] for row in anomaly_visual['items'] if row['visible_abnormal_operation']} if anomaly_visual else set()
            visible_errors = [e for e in selected_mcq['qualifying_errors'] if e['event_id'] in visible_event_ids]
            visual_ok = bool(visible_errors)
            if visual_ok:
                observed_by_id = {row['event_id']: row for row in anomaly_visual['items']}
                abnormal_segments = []
                for error in visible_errors:
                    observed = observed_by_id[error['event_id']]
                    start_s = (error['interval_frames'][0] - clip['start_frame']) / clip['fps']
                    end_s = (error['interval_frames'][1] - clip['start_frame']) / clip['fps']
                    anomaly_names = [option['name'] for option, flag in zip(selected_mcq['options'][1:], error['labels']) if flag]
                    abnormal_segments.append({
                        'event_id': error['event_id'],
                        'start_s': round(start_s, 3),
                        'end_s': round(end_s, 3),
                        'duration_s': error['duration_s'],
                        'anomaly_types': anomaly_names,
                        'evidence_frame_ids': observed['evidence_frame_ids'],
                        'observed_description': observed['observed_description'],
                    })
                evidence = sorted({f for row in anomaly_visual['items'] for f in row['evidence_frame_ids']})
                supported_option_ids = [option['id'] for i, option in enumerate(selected_mcq['options'][1:]) if any(error['labels'][i] for error in visible_errors)]
                supported_source_ids = sorted({source for error in visible_errors for source in error['source_ids']})
                visible_names = [option['name'] for option in selected_mcq['options'] if option['id'] in supported_option_ids]
                segment_text = ' '.join(
                    f"From {row['start_s']:.2f} to {row['end_s']:.2f} seconds: {row['observed_description']} (type: {', '.join(row['anomaly_types'])})."
                    for row in abnormal_segments
                )
                answer = 'Yes. ' + segment_text
                supported_mcq = {**selected_mcq, 'qualifying_errors': visible_errors, 'correct_option_ids': supported_option_ids, 'gt_source_ids': supported_source_ids, 'visually_supported_event_ids': sorted(visible_event_ids)}
                generated_items.append({**supported_mcq, 'arm': 'V', 'answer': answer, 'abnormal_segments': abnormal_segments, 'visual_support': decision['visual_support'], 'evidence_frame_ids': evidence, 'selection_reason': decision['reason'], 'independent_visual_check': anomaly_visual, 'unseen_qualifying_event_ids': sorted({e['event_id'] for e in selected_mcq['qualifying_errors']} - visible_event_ids), 'status': 'candidate', 'human_review': 'unreviewed'})
            else:
                record.setdefault('selection_exclusions', []).append({'candidate_id': selected_mcq['question_id'], 'reason': 'blind_visual_check_did_not_support_abnormal_operation'})
        record['questions'] = generated_items
        record['status'] = 'completed' if generated_items else 'held'
    except Exception as exc:
        record.update(status='error', error=f'{type(exc).__name__}:{exc}')
    record['finished_at'] = time.time()
    save_json(path, record)
    return record


def prepare():
    manifest, summary = prepare_index()
    plans, mcqs, candidates, exclusions = [], [], [], []
    for clip in manifest:
        trial = read_json(FOLDER / 'trials' / (clip['video_id'] + '.json'))
        qs, mcq, cs, excluded = build_candidates(trial, clip)
        plans.extend(qs)
        if mcq:
            mcqs.append(mcq)
        candidates.extend(cs)
        exclusions.extend([dict(x, clip_id=clip['clip_id']) for x in excluded])
        save_json(FOLDER / 'plans' / (clip['clip_id'] + '.json'), {'clip': clip, 'open_qa_candidates': qs, 'fixed_mcq': [mcq] if mcq else [], 'selection_candidates': cs, 'excluded': excluded})
    save_jsonl(FOLDER / 'open_qa_candidates.jsonl', plans)
    save_jsonl(FOLDER / 'fixed_mcq.jsonl', mcqs)
    save_jsonl(FOLDER / 'selection_candidates.jsonl', candidates)
    save_jsonl(FOLDER / 'question_exclusions.jsonl', exclusions)
    save_jsonl(FOLDER / 'first10_open_qa_candidates.jsonl', plans[:10])
    print({'summary': summary, 'open_qa_candidates': len(plans), 'fixed_mcq_candidates': len(mcqs), 'selection_candidates': len(candidates)}, flush=True)
    return manifest


def export_status(state='running'):
    manifest = read_jsonl(FOLDER / 'manifest.jsonl')
    records = [read_json(p) for p in sorted((FOLDER / 'results').glob('*_V.json'))] if (FOLDER / 'results').exists() else []
    questions = [q for r in records for q in r.get('questions', [])]
    resolved = {r.get('clip_id') for r in records if r.get('status') in ['completed', 'held']}
    preparation_errors = list((FOLDER / 'preparation_errors').glob('*.json')) if (FOLDER / 'preparation_errors').exists() else []
    save_jsonl(FOLDER / 'questions.jsonl', questions)
    save_jsonl(FOLDER / 'reviews.jsonl', [{'question_id': q['question_id'], 'clip_id': q['clip_id'], 'arm': 'V', 'review': q.get('automatic_review', {'verdict': 'selection_keep' if q['kind'] == 'mcq_anomaly_clip' else 'missing'}), 'human_review': 'unreviewed'} for q in questions])
    progress = {'state': state, 'updated_at': time.time(), 'selected_clips': len(manifest), 'resolved_clips': len(resolved), 'pending_clip_count': len(manifest) - len(resolved), 'preparation_error_count': len(preparation_errors), 'arm_status': dict(Counter(r.get('status') for r in records)), 'question_status': dict(Counter(q.get('status') for q in questions)), 'question_kinds': dict(Counter(q.get('kind') for q in questions)), 'selected_question_count': sum(len(r.get('selected_question_ids', [])) for r in records), 'human_review': 'pending', 'formal_release': False}
    save_json(FOLDER / 'progress.json', progress)
    return progress


async def run(limit=0):
    import subprocess
    import torch
    import httpx
    if not torch.cuda.is_available():
        raise RuntimeError('v27_preflight:cuda_unavailable')
    for url in CONFIG['base_urls']:
        response = httpx.get(url + '/models', timeout=10, trust_env=False)
        response.raise_for_status()
        if CONFIG['model'] not in [item['id'] for item in response.json()['data']]:
            raise RuntimeError('v27_preflight:wrong_model:' + url)
    save_json(FOLDER / 'preflight.json', {'timestamp': time.time(), 'python': str(Path.cwd()), 'torch': torch.__version__, 'cuda': torch.version.cuda, 'gpu_count': torch.cuda.device_count(), 'services': CONFIG['base_urls'], 'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used', '--format=csv,noheader'], text=True)})
    manifest = read_jsonl(FOLDER / 'manifest.jsonl')
    frozen_hash = freeze(manifest)
    completed = {}
    results_dir = FOLDER / 'results'
    if results_dir.exists():
        for path in results_dir.glob('*_V.json'):
            try:
                value = read_json(path)
            except Exception:
                continue
            if value.get('status') in ['completed', 'held']:
                completed[value.get('clip_id')] = value['status']
    pending = [clip for clip in manifest if clip['clip_id'] not in completed]
    selected = pending[:limit] if limit else pending
    pool = StructuredVideoPool(CONFIG, FOLDER)
    queue = asyncio.Queue()
    status_lock = asyncio.Lock()
    for clip in selected:
        queue.put_nowait(clip)
    async def worker():
        while True:
            try:
                clip = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                record = await run_clip(pool, clip, frozen_hash)
                if record.get('status') in ['completed', 'held']:
                    (FOLDER / 'preparation_errors' / (clip['clip_id'] + '.json')).unlink(missing_ok=True)
                print({'clip_id': clip['clip_id'], 'status': record['status'], 'selected': record.get('selected_question_ids', [])}, flush=True)
            except Exception as exc:
                save_json(FOLDER / 'preparation_errors' / (clip['clip_id'] + '.json'), {'clip_id': clip['clip_id'], 'module': 'run_clip', 'error': f'{type(exc).__name__}:{exc}'})
                print({'clip_id': clip['clip_id'], 'error': str(exc)}, flush=True)
            finally:
                queue.task_done()
                async with status_lock:
                    export_status()
    try:
        await asyncio.gather(*(worker() for _ in range(CONFIG['workers'])))
    finally:
        await pool.close()
        save_json(FOLDER / 'runs' / (str(time.time_ns()) + '.json'), {'limit': limit, 'requests': pool.calls})
        state = 'smoke_finished' if limit else 'full_finished'
        progress = export_status(state)
        if not limit and (progress['pending_clip_count'] or progress['preparation_error_count'] or progress['arm_status'].get('error', 0)):
            progress = export_status('full_finished_with_errors')
        print(progress, flush=True)
