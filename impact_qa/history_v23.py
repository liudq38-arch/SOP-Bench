from impact_qa.common import ROOT, fingerprint, read_json, save_json
from impact_qa.event_v22 import TEXT, arr, choice, obj


CONFIG = read_json(ROOT / 'configs/impact_qa/history_v23.json')
FOLDER = ROOT / CONFIG['output_root']
MEMORY = obj({'summary': {'type': 'string', 'maxLength': 1800}, 'objects_and_states': arr(TEXT, 0, 6), 'ongoing_actions': arr(TEXT, 0, 4), 'unresolved': arr(TEXT, 0, 4)})


def schema(stage, events):
    ids = [e['event_id'] for e in events]
    if stage == 'describe':
        event = obj({'description': TEXT, 'phase': choice(['start', 'ongoing', 'end', 'uncertain']), 'continues_event_id': choice(['none'] + ids)})
        return obj({'description': TEXT, 'events': arr(event, 1, 8), 'uncertainties': arr(TEXT, 0, 5), 'memory_after': MEMORY})
    if stage == 'integrate':
        section = obj({'description': TEXT, 'event_ids': arr(choice(ids), 1, len(ids))})
        return obj({'sections': arr(section, 1, 16), 'contradictions_or_uncertainties': arr(TEXT, 0, 10), 'overall_description': TEXT})
    if stage == 'qa':
        item = obj({'kind': choice(['event_description', 'event_occurrence', 'observed_order']), 'question': TEXT, 'answer': TEXT, 'event_ids': arr(choice(ids), 1, len(ids))})
        return obj({'items': arr(item, 1, 3), 'skipped_questions': arr(TEXT, 0, 5)})
    raise ValueError(f'history_v23:stage:{stage}')


def history_input(ledger):
    recent = ledger[-CONFIG['recent_clips']:]
    return {'memory_before': ledger[-1]['memory_after'] if ledger else {'summary': '', 'objects_and_states': [], 'ongoing_actions': [], 'unresolved': []}, 'recent_history': [{'clip_id': r['clip_id'], 'source_interval_s': r['source_interval_s'], 'description': r['description'], 'events': r['events'], 'uncertainties': r['uncertainties']} for r in recent], 'history_has_earlier_clips': len(ledger) > len(recent), 'history_count': len(ledger)}


def validate_integration(value, events):
    required = {e['event_id'] for e in events}
    covered = {i for s in value['sections'] for i in s['event_ids']}
    if covered != required:
        raise ValueError(f'history_v23:integration_event_coverage:{sorted(required - covered)}')


def validate_qa(value):
    kinds = [q['kind'] for q in value['items']]
    if kinds.count('event_description') != 1 or len(kinds) != len(set(kinds)):
        raise ValueError('history_v23:qa_kind_contract')


async def process(pool, record):
    case = record['case']
    case_id = case['case_id']
    folder = FOLDER / 'runs' / case_id
    ledger = []
    output = {'case_id': case_id, 'view': case['view'], 'scope': 'complete_selected_ATR_interval_not_full_source_video', 'source_interval_s': case['interval_s'], 'status': 'running', 'formal_release': False, 'ledger': ledger}
    try:
        for clip in record['clips']:
            prior = [e for row in ledger[-CONFIG['recent_clips']:] for e in row['events']]
            payload = {'case_id': case_id, 'view': case['view'], 'clip_id': clip['clip_id'], 'core_source_interval_s': [clip['core_frames'][0]['source_pts_s'], clip['core_frames'][-1]['source_pts_s']], 'video_start_source_pts_s': clip['media_frames'][0]['source_pts_s'], 'core_local_interval_s': [clip['core_frames'][0]['source_pts_s'] - clip['media_frames'][0]['source_pts_s'], clip['core_frames'][-1]['source_pts_s'] - clip['media_frames'][0]['source_pts_s']], 'sampling': {'frames': len(clip['video']['sampled_frames']), 'source_pts_s': [f['source_pts_s'] for f in clip['video']['sampled_frames']]}, **history_input(ledger)}
            response = await pool.call('describe', (ROOT / 'prompts/impact_qa/v23/describe.txt').read_text(), payload, schema('describe', prior), CONFIG['max_tokens']['describe'], video=clip['video'])
            value = response['result']
            events = [dict(e, event_id=f'{clip["clip_id"]}_h{i:02d}', source_clip_id=clip['clip_id'], source_interval_s=payload['core_source_interval_s'], temporal_precision='clip_level_not_exact_action_boundary') for i, e in enumerate(value['events'])]
            row = dict(value, events=events, clip_id=clip['clip_id'], source_interval_s=payload['core_source_interval_s'], cache_key=response['cache_key'], history_before_hash=fingerprint(history_input(ledger)), video_path=clip['video']['path'])
            ledger.append(row)
            save_json(folder / (clip['clip_id'] + '.json'), row)
            save_json(folder / 'result.json', output)
        all_events = [e for row in ledger for e in row['events']]
        payload = {'case_id': case_id, 'view': case['view'], 'source_interval_s': case['interval_s'], 'clip_ledger': ledger, 'note': 'Complete selected interval only; no footage outside this interval was provided.'}
        response = await pool.call('integrate', (ROOT / 'prompts/impact_qa/v23/integrate.txt').read_text(), payload, schema('integrate', all_events), CONFIG['max_tokens']['integrate'], validator=lambda v: validate_integration(v, all_events))
        output['integration'] = response['result']
        output['integration_cache_key'] = response['cache_key']
        atr = next(s for s in case['source_catalog'] if s['source_id'] == 'atr_' + case['view'])
        qa_payload = dict(payload, integrated_account=output['integration'], atr_ground_truth={'source_path': atr['path'], 'source_sha256': atr['sha256'], 'source_pointer': atr['pointer'], 'value': atr['value']}, normative_sequence=None, normative_correct_tool=None)
        response = await pool.call('qa', (ROOT / 'prompts/impact_qa/v23/qa.txt').read_text(), qa_payload, schema('qa', all_events), CONFIG['max_tokens']['qa'], validator=validate_qa)
        output['qa'] = response['result']
        output['qa_cache_key'] = response['cache_key']
        output['status'] = 'completed_pending_review'
    except Exception as exc:
        output['status'] = 'error'
        output['error'] = f'{type(exc).__name__}:{exc}'
    finally:
        save_json(folder / 'result.json', output)
    return output
