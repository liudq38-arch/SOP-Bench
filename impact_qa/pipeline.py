import asyncio
import json
import re
from pathlib import Path

from .api import Pool
from .common import OUT, ROOT, fingerprint, read_json, save_json
from .media import prepare_evidence, prepare_focus_evidence, prepare_native_evidence
from .validation import validate_evidence_graph, select_visual_facts, derive_pair_evidence


def validate_pairs(result, facts, images):
    issues = []
    fact_map = {f['id']: f for f in facts.get('facts', [])}
    image_ids = {x['evidence_id'] for x in images}
    image_scopes = {x['evidence_id']: x.get('time_scope') for x in images}
    pairs = result.get('qa_pairs', [])
    if not isinstance(pairs, list) or len(pairs) > 2:
        return ['invalid_pair_count']
    for i, pair in enumerate(pairs):
        if not isinstance(pair.get('question'), str) or not isinstance(pair.get('answer'), str):
            issues.append(f'{i}:invalid_question_answer')
        refs = pair.get('supporting_fact_ids', [])
        if not refs or any(f not in fact_map for f in refs):
            issues.append(f'{i}:invalid_fact_refs')
        elif any(not fact_map[f].get('usable_for_qa', False) for f in refs):
            issues.append(f'{i}:fact_marked_unusable')
        if not pair.get('evidence_ids') or any(e not in image_ids for e in pair.get('evidence_ids', [])):
            issues.append(f'{i}:invalid_visual_refs')
        if pair.get('dimension') != 'order' and any(image_scopes.get(e) in ['CONTEXT_BEFORE', 'CONTEXT_AFTER'] for e in pair.get('evidence_ids', [])):
            issues.append(f'{i}:context_evidence_for_target_claim')
    return issues


def scoped_images(images, event, version):
    if version in ['v1', 'v2']:
        return images
    return [dict(f, time_scope='TARGET' if event['start_s'] <= f['requested_time_s'] < event['end_s_exclusive'] else 'CONTEXT_BEFORE' if f['requested_time_s'] < event['start_s'] else 'CONTEXT_AFTER') for f in images]


async def process_event(client, event, version):
    prompts = {stage: (ROOT / f'prompts/impact_qa/{version}/{stage}.txt').read_text() for stage in ['observe', 'ground', 'generate', 'review']}
    destination = OUT / 'runs' / version / event['split'] / (event['event_id'] + '.json')
    run_key = fingerprint({'event': event, 'prompts': prompts, 'model': client.model, 'model_revision': client.model_revision, 'pipeline_version': '1'})
    if destination.exists():
        previous = read_json(destination)
        if previous.get('run_key') == run_key and previous.get('status') == 'ok':
            return previous
    record = {'event_id': event['event_id'], 'event': event, 'prompt_version': version, 'run_key': run_key, 'human_review_status': 'pending_human_review', 'status': 'running'}
    try:
        evidence = await asyncio.to_thread(prepare_native_evidence, event) if version in ['v6', 'v7'] else await asyncio.to_thread(prepare_focus_evidence, event) if version in ['v4', 'v5'] else await asyncio.to_thread(prepare_evidence, event, targeted=version not in ['v1', 'v2'])
        images = scoped_images(evidence['images'], event, version)
        context = {'task': 'angle grinder disassembly' if 'Disassembly' in event['video_id'] else 'angle grinder reassembly', 'target_hand': event['hand'], 'target_action_hint': event['action'], 'target_start_s': event['start_s'], 'target_end_s': event['end_s_exclusive'], 'frame_scope': 'Context frames can show other actions; evaluate only the stated target hand/action interval.'}
        observation_context = context if version == 'v1' else {k: v for k, v in context.items() if k != 'target_action_hint'}
        if version == 'v7':
            observation_context = dict(observation_context, action_focus_hint=event['verb'])
            record['observation_conditioning'] = 'original_annotation_verb_only; not blind perception'
        observation = await client.call('observe', prompts['observe'], observation_context, images)
        record['observation'] = observation['result']
        record['cache_keys'] = {'observation': observation['cache_key']}
        if observation['result'].get('needs_refinement'):
            refined = await asyncio.to_thread(prepare_evidence, event, 24, 1024, True)
            refined_images = scoped_images(refined['images'], event, version)
            if version in ['v6', 'v7']:
                refined_images = [f for f in images if f.get('media_type') == 'video'] + refined_images
            new_observation = await client.call('observe_refined', prompts['observe'], observation_context, refined_images)
            record['refined_observation'] = new_observation['result']
            record['cache_keys']['refined_observation'] = new_observation['cache_key']
            images = refined_images
            observation = new_observation
        annotation = {k: event[k] for k in ['hand', 'action', 'verb', 'object', 'phase', 'anomaly_types', 'annotation_duration_s', 'coarse_steps', 'neighbor_actions']}
        ground = await client.call('ground', prompts['ground'], {'target': context, 'annotation': annotation, 'observation': observation['result']})
        record['facts'] = ground['result']
        record['cache_keys']['ground'] = ground['cache_key']
        generation_payload = {'target': context, 'annotation': annotation, 'facts': ground['result'], 'observation': observation['result'], 'available_evidence_ids': [x['evidence_id'] for x in images]}
        if version == 'v4':
            generation_payload = {'target': observation_context, 'facts': [f for f in ground['result'].get('facts', []) if f.get('usable_for_qa') and f.get('support') in ['visual', 'both']], 'unknowns': ground['result'].get('unknowns', []), 'available_evidence_ids': [x['evidence_id'] for x in images]}
        selected_facts = None
        if version in ['v5', 'v6', 'v7']:
            selected_facts, withheld = select_visual_facts(observation['result'], ground['result'], images)
            record['withheld_facts'] = withheld
            record['generation_facts'] = selected_facts
            generation_payload = {'target': dict(observation_context, action_focus=event['verb']), 'facts': selected_facts, 'unknowns': ground['result'].get('unknowns', [])}
        generated = await client.call('generate', prompts['generate'], generation_payload)
        if version in ['v5', 'v6', 'v7']:
            generated = dict(generated, result=derive_pair_evidence(generated['result'], selected_facts))
        record['generation'] = generated['result']
        record['cache_keys']['generate'] = generated['cache_key']
        record['structural_issues'] = validate_evidence_graph(observation['result'], ground['result'], images) + validate_pairs(generated['result'], ground['result'], images)
        if version in ['v5', 'v6', 'v7']:
            record['source_graph_issues'] = record['structural_issues']
            issues = validate_pairs(generated['result'], {'facts': selected_facts}, images)
            dimensions = set()
            for i, pair in enumerate(generated['result'].get('qa_pairs', [])):
                if pair.get('dimension') in dimensions:
                    issues.append(f'{i}:duplicate_dimension')
                dimensions.add(pair.get('dimension'))
                if re.search(r'\b(static|motionless|throughout|never)\b|without (rotating|moving|removing)', pair.get('answer', ''), re.I):
                    issues.append(f'{i}:unsupported_continuous_motion_claim')
            record['structural_issues'] = issues
            record['pair_structural_issues'] = {str(i): [x for x in issues if not x.split(':')[0].isdigit() or x.startswith(f'{i}:')] for i in range(len(generated['result'].get('qa_pairs', [])))}
        review_payload = {'target': context, 'annotation': annotation, 'facts': {'facts': selected_facts} if version in ['v5', 'v6', 'v7'] else ground['result'], 'qa_pairs': generated['result'].get('qa_pairs', [])}
        if version == 'v7':
            review_payload = {'target': {k: v for k, v in observation_context.items() if k != 'action_focus_hint'}, 'qa_pairs': generated['result'].get('qa_pairs', [])}
        reviewed = await client.call('review', prompts['review'], review_payload, images)
        record['review'] = reviewed['result']
        record['cache_keys']['review'] = reviewed['cache_key']
        record['evidence'] = images
        pairs = record['generation'].get('qa_pairs', [])
        reviews = record['review'].get('reviews', [])
        if len(reviews) != len(pairs):
            record['structural_issues'].append('review_count_mismatch')
        if version in ['v5', 'v6', 'v7'] and sorted(x.get('qa_index', -1) for x in reviews) != list(range(len(pairs))):
            record['structural_issues'].append('review_indices_mismatch')
            for pair_issues in record['pair_structural_issues'].values():
                pair_issues.append('review_indices_mismatch')
        record['category_qa'] = {'question': f"For my {event['hand']} hand performing '{event['action'].replace('_', ' ')}' in the specified interval, is the action normal, anomalous, or recovery? If anomalous, identify all applicable types: temporal, spatial, handling, wrong part, wrong tool, procedural.", 'answer': {'phase': event['phase'], 'anomaly_types': event['anomaly_types'] if event['phase'] == 'anomaly' else []}, 'reference_source': event['annotation_ref'], 'visibility_status': ground['result'].get('visual_answerability', 'unknown'), 'label_conflicts': ground['result'].get('conflicts', []), 'review_status': 'pending_human_review'}
        record['status'] = 'ok'
    except Exception as exc:
        record['status'] = 'error'
        record['error'] = f'{type(exc).__name__}: {exc}'
    save_json(destination, record)
    print(json.dumps({'event_id': event['event_id'], 'split': event['split'], 'version': version, 'status': record['status'], 'pairs': len(record.get('generation', {}).get('qa_pairs', [])), 'error': record.get('error')}), flush=True)
    return record


async def run(events, version, concurrency, base_url):
    urls = [u.strip() for u in base_url.split(',') if u.strip()]
    client = Pool(urls, concurrency)
    event_limit = asyncio.Semaphore(concurrency * len(urls))
    async def guarded(event):
        async with event_limit:
            return await process_event(client, event, version)
    try:
        return await asyncio.gather(*(guarded(e) for e in events))
    finally:
        await client.close()
