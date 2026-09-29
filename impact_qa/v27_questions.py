import re

from impact_qa.common import fingerprint
from impact_qa.v26_data import OPTIONS, clip_errors, human, normal_scope
from impact_qa.v26_questions import TOOL_NAMES, clock_interval, overlap, state_at


ANOMALY_MIN_SECONDS = 5.0
VISUAL_SUPPORT = ['supports_visible_outcome', 'cannot_independently_confirm', 'conflicts_with_gt']
KINDS = ['overall_operation', 'detailed_operation', 'step_completion', 'observed_order', 'operation_duration', 'mcq_anomaly_clip']
GENERIC_TOOL_LABELS = {'tool', 'tools'}
SUPPORT_VERBS = {'hold', 'transfer'}
TOOL_PICKUP_VERBS = {'pick_up'}
ACTION_PRIORITY = {
    'insert': 0,
    'tighten': 1,
    'hand_tighten': 1,
    'loosen': 1,
    'hand_loosen': 1,
    'unscrew': 1,
    'screw_on': 1,
    'remove': 2,
    'extract': 2,
    'dismount': 2,
    'detach': 2,
    'attach': 2,
    'mount': 2,
    'seat': 2,
    'thread': 2,
    'hand_spin': 3,
    'align': 4,
    'adjust': 4,
    'flip': 5,
    'place': 6,
    'store': 7,
}


def _specific_tool_names(names):
    names = list(names)
    specific = [name for name in names if re.sub(r'[^a-z0-9]+', ' ', human(name).lower()).strip() not in GENERIC_TOOL_LABELS]
    return specific or names
OPERATION_PREFIXES = (
    'hand_tighten', 'hand_loosen', 'screw_on', 'unscrew', 'dismount', 'extract',
    'install', 'attach', 'insert', 'mount', 'remove', 'detach', 'seat', 'retrieve',
    'store', 'tighten', 'loosen', 'thread', 'align', 'adjust', 'flip', 'hand_spin',
)
ORDER_OPERATION_PREFIXES = {
    'install', 'attach', 'insert', 'mount', 'seat', 'screw_on', 'remove',
    'detach', 'dismount', 'extract', 'unscrew',
}


def make_fact(key, text, refs, required=None, interval=None, event_ids=None, verdict=None, numeric=None):
    value = {
        'fact_id': 'f_' + fingerprint(key)[:12],
        'reference_text': text,
        'source_ids': sorted(set(refs)),
        'required_phrases': required or [],
        'event_ids': event_ids or [],
    }
    if interval is not None:
        value['interval_s'] = interval
    if verdict is not None:
        value['verdict'] = verdict
    if numeric is not None:
        value['numeric'] = numeric
    return value


def render_units(units, facts):
    by_id = {u['fact_id']: u['text'].strip() for u in units}
    return '\n'.join(by_id[f['fact_id']] for f in facts)


def open_candidate(clip, kind, slot, topic, facts, constraints):
    candidate_id = clip['clip_id'] + '_' + slot
    return {
        'candidate_id': candidate_id,
        'question_id': candidate_id,
        'pair_id': candidate_id,
        'clip_id': clip['clip_id'],
        'kind': kind,
        'topic': topic,
        'reference_facts': facts,
        'answer_constraints': constraints,
        'gt_source_ids': sorted({s for f in facts for s in f['source_ids']}),
        'human_review': 'unreviewed',
    }


def _events(trial, clip):
    events = [e for e in trial['events'] if e['action'] != 'null' and overlap(e, clip)]
    full = [e for e in events if clip['start_frame'] <= e['start_frame'] and e['end_frame_exclusive'] <= clip['end_frame_exclusive']]
    return events, full


def _summary_fact(trial, clip, events):
    tools = _specific_tool_names(sorted({e['noun'] for e in events if e['noun'] in TOOL_NAMES}))
    parts = sorted({e['noun'] for e in events if e['noun'] not in TOOL_NAMES})
    changed = sorted({c['component'] for c in trial.get('state_changes', []) if clip['start_frame'] <= c['frame'] < clip['end_frame_exclusive']})
    operation = 'assembly' if clip['workflow'] == 'assemble' else 'disassembly'
    subjects = [human(x) for x in changed] or [human(x) for x in parts] or ['the recorded components']
    main_components = [human(x) for x in changed if not _is_minor_component(x)]
    if not main_components:
        main_components = [human(x) for x in parts if not _is_minor_component(x)]
    main_components = list(dict.fromkeys(main_components))[:3]
    text = f"Overall, I carry out {operation} work on {', '.join(subjects)} during this clip."
    if tools:
        text += ' I handle these tools: ' + ', '.join(human(x) for x in tools) + '.'
    if parts:
        text += ' I handle these parts: ' + ', '.join(human(x) for x in parts) + '.'
    refs = [s for e in events for s in e['source_ids']]
    refs.extend(c.get('source_id') for c in trial.get('state_changes', []) if clip['start_frame'] <= c['frame'] < clip['end_frame_exclusive'] and c.get('source_id'))
    required = [operation]
    fact = make_fact([clip['clip_id'], 'overall_operation'], text, refs, required)
    fact['role'] = 'overall'
    fact['operation'] = operation
    fact['tools'] = [human(x) for x in tools]
    fact['parts'] = [human(x) for x in parts]
    fact['components'] = [human(x) for x in changed]
    fact['main_components'] = main_components
    return fact


def _is_minor_component(value):
    tokens = set(re.findall(r'[a-z0-9]+', value.lower()))
    return bool(tokens.intersection({'screw', 'screws', 'washer', 'washers', 'spring', 'springs', 'bolt', 'bolts', 'nut', 'nuts'}))


def _normalize_name(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', value.lower())).strip()


def _distinct_targets(first, second):
    a, b = _normalize_name(first), _normalize_name(second)
    if not a or not b or a == b:
        return False
    at, bt = set(a.split()), set(b.split())
    return not (at <= bt or bt <= at)


def _operation_label(label):
    for prefix in OPERATION_PREFIXES:
        if label == prefix or label.startswith(prefix + '_'):
            target = label[len(prefix):].strip('_')
            return prefix, human(target) if target else ''
    return None, human(label)


def _phase_gerund(verb, target):
    gerunds = {
        'install': 'installing', 'attach': 'attaching', 'insert': 'inserting',
        'mount': 'mounting', 'seat': 'seating', 'screw_on': 'screwing on',
        'remove': 'removing', 'detach': 'detaching', 'dismount': 'dismounting',
        'extract': 'extracting', 'unscrew': 'unscrewing', 'hand_tighten': 'hand-tightening',
        'hand_loosen': 'hand-loosening', 'tighten': 'tightening', 'loosen': 'loosening',
        'thread': 'threading', 'align': 'aligning', 'adjust': 'adjusting', 'flip': 'turning over',
        'hand_spin': 'turning by hand', 'retrieve': 'retrieving', 'store': 'storing',
    }
    action = gerunds.get(verb, human(verb))
    return f"{action} the {target}" if target else action


def _phase_past(verb, target):
    past = {
        'install': 'installed', 'attach': 'attached', 'insert': 'inserted',
        'mount': 'mounted', 'seat': 'seated', 'screw_on': 'screwed on',
        'remove': 'removed', 'detach': 'detached', 'dismount': 'dismounted',
        'extract': 'extracted', 'unscrew': 'unscrewed', 'hand_tighten': 'hand-tightened',
        'hand_loosen': 'hand-loosened', 'tighten': 'tightened', 'loosen': 'loosened',
        'thread': 'threaded', 'align': 'aligned', 'adjust': 'adjusted', 'flip': 'turned over',
        'hand_spin': 'turned by hand', 'retrieve': 'retrieved', 'store': 'stored',
    }
    action = past.get(verb, human(verb))
    return f"{action} the {target}" if target else action


def _event_action(e):
    verb, noun = e['verb'], human(e['noun'])
    if verb in SUPPORT_VERBS or (verb in TOOL_PICKUP_VERBS and e['noun'] not in TOOL_NAMES):
        return None
    if verb in {'store', 'place'} and e['noun'] in TOOL_NAMES:
        return None
    aliases = {
        'hand_tighten': 'tighten', 'hand_loosen': 'loosen', 'hand_spin': 'hand_spin',
        'dismount': 'remove', 'detach': 'remove', 'extract': 'remove', 'unscrew': 'loosen',
        'screw_on': 'tighten', 'attach': 'install', 'insert': 'install', 'mount': 'install',
        'seat': 'install', 'thread': 'install',
    }
    action = aliases.get(verb, verb)
    if verb == 'pick_up':
        phrase = f"pick up the {noun}"
    else:
        phrase = f"{_phase_gerund(action, noun)}"
    return {'key': (action, _normalize_name(noun)), 'phrase': phrase, 'priority': ACTION_PRIORITY.get(verb, 8), 'start_frame': e['start_frame'], 'event_id': e['event_id']}


def _operation_phases(trial, clip, events):
    phases = []
    for episode in trial.get('episodes', []):
        start = max(clip['start_frame'], episode['start_frame'])
        end = min(clip['end_frame_exclusive'], episode['end_frame_exclusive'])
        if end <= start:
            continue
        verb, target = _operation_label(episode['label'])
        if not target or not verb:
            continue
        phase_events = [e for e in events if e['start_frame'] < end and e['end_frame_exclusive'] > start]
        tool_names = []
        for event in phase_events:
            if event['noun'] in TOOL_NAMES and event['noun'] not in tool_names:
                tool_names.append(event['noun'])
        actions, seen = [], set()
        for event in phase_events:
            action = _event_action(event)
            if action and action['key'] not in seen:
                seen.add(action['key'])
                actions.append(action)
        actions.sort(key=lambda x: (x['start_frame'], x['priority'], x['phrase']))
        if len(actions) > 3:
            important = sorted(actions, key=lambda x: (x['priority'], x['start_frame']))[:3]
            chosen = {x['event_id'] for x in important}
            actions = [x for x in actions if x['event_id'] in chosen]
        phases.append({
            'label': episode['label'],
            'operation': verb,
            'target': target,
            'summary': _phase_gerund(verb, target),
            'interval_s': clock_interval({'start_frame': start, 'end_frame_exclusive': end}, clip),
            'tools_in_phase': [human(x) for x in _specific_tool_names(tool_names)],
            'key_actions': [x['phrase'] for x in actions],
            'event_ids': [e['event_id'] for e in phase_events],
            'source_ids': sorted(set(episode['source_ids'] + [s for e in phase_events for s in e['source_ids']])),
        })
    phases.sort(key=lambda x: (x['interval_s'][0], x['interval_s'][1], x['target']))
    return phases


def _detail_facts(trial, clip, events):
    phases = _operation_phases(trial, clip, events)
    if not phases:
        return []
    phase_text = []
    tools = _specific_tool_names(sorted({tool for phase in phases for tool in phase['tools_in_phase']}))
    targets = []
    for index, phase in enumerate(phases, 1):
        if phase['target'] not in targets:
            targets.append(phase['target'])
        details = ', '.join(phase['key_actions'])
        tool_text = ', '.join(phase['tools_in_phase'])
        line = f"Phase {index}: {phase['summary']}"
        if details:
            line += f"; recorded key actions: {details}"
        if tool_text:
            line += f"; tools recorded in this phase: {tool_text}"
        phase_text.append(line)
    text = 'Summarize the main operation phases in this order: ' + '; '.join(phase_text) + '.'
    all_event_ids = [e['event_id'] for e in events]
    refs = sorted({s for e in events for s in e['source_ids']} | {s for phase in phases for s in phase['source_ids']})
    required = [human(x) for x in targets + tools]
    fact = make_fact([clip['clip_id'], 'detailed_operation', [p['label'] for p in phases]], text, refs, required)
    fact.update(role='operation_summary', operation_phases=phases, covered_event_ids=all_event_ids, event_count=len(events), phase_count=len(phases), key_tool_names=tools)
    return [fact]


def _completion_questions(trial, clip, events):
    last = state_at(trial, clip['end_frame_exclusive'] - 1)
    if not last or not trial.get('components'):
        return [], [{'kind': 'step_completion', 'reason': 'missing_same_view_state_gt'}]
    target_state = 1 if clip['workflow'] == 'assemble' else 0
    changes = [
        row for row in trial['state_changes']
        if clip['start_frame'] <= row['frame'] < clip['end_frame_exclusive']
    ]
    completed = sorted({
        row['component_index'] for row in changes
        if row['state'] == target_state and last['state'][row['component_index']] == target_state
    })
    if not completed:
        return [], [{'kind': 'step_completion', 'reason': 'no_component_completion_transition_in_clip'}]
    completed_names = [human(trial['components'][index]['name']) for index in completed]
    operation = 'installation' if clip['workflow'] == 'assemble' else 'removal'
    verb = 'install' if clip['workflow'] == 'assemble' else 'remove'
    result = []
    incomplete = [
        index for index, state in enumerate(last['state'])
        if state != target_state and index not in completed
    ]
    preferred_state = 0 if clip['workflow'] == 'assemble' else 1
    incomplete.sort(key=lambda index: (last['state'][index] != preferred_state, index))
    if incomplete:
        index = incomplete[0]
        name = human(trial['components'][index]['name'])
        if clip['workflow'] == 'assemble':
            state_text = 'uninstalled at clip end' if last['state'][index] == 0 else 'not in the fully installed state at clip end'
            topic = f"Ask whether installation of {name} was completed in this clip; if not, ask which component installations were completed."
        else:
            state_text = 'still installed at clip end' if last['state'][index] == 1 else 'not in the fully removed state at clip end'
            topic = f"Ask whether {name} was completely removed in this clip; if not, ask which component removals were completed."
        wording = f"The queried component, {name}, is {state_text}. During this clip, the completed {operation} components are {', '.join(completed_names)}."
        refs = [last['source_id'], trial['component_source_ids'][str(index)]]
        refs.extend(row['source_id'] for row in changes if row['component_index'] in completed and row.get('source_id'))
        refs.extend(trial['component_source_ids'][str(done)] for done in completed)
        fact = make_fact([clip['clip_id'], 'step_completion_no', index, completed], wording, refs, [name] + completed_names, verdict='no')
        fact.update(
            state=last['state'][index],
            queried_component=name,
            completed_components=completed_names,
            operation=operation,
            queried_source_frame=clip['end_frame_exclusive'] - 1,
            state_effective_frame=last['frame'],
        )
        constraints = {
            'expected_polarity': 'no', 'queried_component': name,
            'completed_components': completed_names, 'operation': operation,
            'must_name_completed_components': True,
        }
        result.append(open_candidate(clip, 'step_completion', 'completion_no_' + str(index), topic, [fact], constraints))
    index = completed[0]
    name = human(trial['components'][index]['name'])
    if clip['workflow'] == 'assemble':
        topic = f"Ask whether installation of {name} was completed during this clip."
        wording = f"The clip completes installation of {name}; its end state is fully installed."
    else:
        topic = f"Ask whether {name} was completely removed during this clip."
        wording = f"The clip completes removal of {name}; its end state is fully removed."
    refs = [row['source_id'] for row in changes if row['component_index'] == index and row.get('source_id')]
    refs.extend([last['source_id'], trial['component_source_ids'][str(index)]])
    fact = make_fact([clip['clip_id'], 'step_completion_yes', index], wording, refs, [name], verdict='yes')
    fact.update(
        state=target_state,
        queried_component=name,
        completed_components=[name],
        operation=operation,
        queried_source_frame=clip['end_frame_exclusive'] - 1,
        state_effective_frame=last['frame'],
    )
    constraints = {
        'expected_polarity': 'yes', 'queried_component': name,
        'completed_components': [name], 'operation': operation,
        'must_name_completed_components': True,
    }
    result.append(open_candidate(clip, 'step_completion', 'completion_yes_' + str(index), topic, [fact], constraints))
    return result[:2], []


def _operation_windows(trial, clip):
    windows = []
    for episode in trial.get('episodes', []):
        a, b = episode['start_frame'], episode['end_frame_exclusive']
        if not (clip['start_frame'] <= a and b <= clip['end_frame_exclusive']):
            continue
        verb, target = _operation_label(episode['label'])
        if verb not in ORDER_OPERATION_PREFIXES or not target:
            continue
        windows.append({
            'start_frame': a,
            'end_frame_exclusive': b,
            'target': target,
            'verb': verb,
            'source_ids': list(episode['source_ids']),
            'basis': 'tas_b_episode',
        })
    distinct = {}
    for window in windows:
        duration = (window['end_frame_exclusive'] - window['start_frame']) / clip['fps']
        if duration + 1e-9 < 5.0:
            continue
        key = (window['verb'], _normalize_name(window['target']))
        value = {**window, 'duration_s': duration, 'interval_s': clock_interval({'start_frame': window['start_frame'], 'end_frame_exclusive': window['end_frame_exclusive']}, clip)}
        previous = distinct.get(key)
        if previous is None or (value['duration_s'], -value['start_frame']) > (previous['duration_s'], -previous['start_frame']):
            distinct[key] = value
    return sorted(distinct.values(), key=lambda x: (x['start_frame'], x['end_frame_exclusive'], x['target']))


def _duration_questions(trial, clip):
    windows = _operation_windows(trial, clip)
    if len(windows) > 2:
        windows = [windows[0], windows[-1]]
    result = []
    seed = int(fingerprint([clip['clip_id'], 'duration_question_style'])[:2], 16)
    for index, window in enumerate(windows):
        duration = window['duration_s']
        start_s, end_s = window['interval_s']
        style = 'duration' if (seed + index) % 2 == 0 else 'start_end'
        operation_text = f"action of {_phase_gerund(window['verb'], window['target'])}"
        if style == 'duration':
            display = f'{duration:.1f}'
            fact_text = f"The {operation_text} lasts {display} seconds in this clip."
            topic = f"Ask how long the {operation_text} lasts in this clip."
            numeric = {'mode': 'duration', 'seconds': duration, 'display': display, 'unit': 'seconds'}
        else:
            display_start, display_end = f'{start_s:.1f}', f'{end_s:.1f}'
            fact_text = f"The {operation_text} starts at {display_start} seconds and ends at {display_end} seconds in the clip."
            topic = f"Ask when the {operation_text} starts and ends in the clip."
            numeric = {
                'mode': 'start_end', 'start_seconds': start_s, 'end_seconds': end_s,
                'display_start': display_start, 'display_end': display_end, 'unit': 'seconds',
            }
        fact = make_fact(
            [clip['clip_id'], 'operation_duration', index, style], fact_text,
            window['source_ids'], [window['target']], window['interval_s'], numeric=numeric,
        )
        fact['operation_window'] = {
            'start_frame': window['start_frame'], 'end_frame_exclusive': window['end_frame_exclusive'],
            'target': window['target'], 'verb': window['verb'], 'answer_mode': style,
        }
        constraints = {'answer_mode': style, 'operation_window': fact['operation_window'], 'numeric': numeric}
        result.append(open_candidate(clip, 'operation_duration', 'duration_' + str(index), topic, [fact], constraints))
    return result


def _order_question(trial, clip, full):
    operations = []
    for episode in trial.get('episodes', []):
        if not (clip['start_frame'] <= episode['start_frame'] < episode['end_frame_exclusive'] <= clip['end_frame_exclusive']):
            continue
        verb, target = _operation_label(episode['label'])
        if verb not in ORDER_OPERATION_PREFIXES or not target:
            continue
        operations.append({
            'verb': verb, 'target': target, 'label': episode['label'],
            'start_frame': episode['start_frame'], 'end_frame_exclusive': episode['end_frame_exclusive'],
            'source_ids': episode['source_ids'],
        })
    pairs = []
    for index, first in enumerate(operations):
        for second in operations[index + 1:]:
            if not _distinct_targets(first['target'], second['target']):
                continue
            if first['end_frame_exclusive'] <= second['start_frame']:
                before, after = first, second
            elif second['end_frame_exclusive'] <= first['start_frame']:
                before, after = second, first
            else:
                continue
            gap = after['start_frame'] - before['end_frame_exclusive']
            pairs.append((gap, before['start_frame'], before, after))
    if not pairs:
        return None
    pairs.sort(key=lambda row: (row[0], row[1], row[2]['target'], row[3]['target']))
    choice = int(fingerprint([clip['clip_id'], 'observed_order'])[:4], 16) % min(len(pairs), 3)
    _, _, before, after = pairs[choice]
    before_q = _phase_gerund(before['verb'], before['target'])
    after_q = _phase_gerund(after['verb'], after['target'])
    before_a = _phase_past(before['verb'], before['target'])
    after_a = _phase_past(after['verb'], after['target'])
    fact = make_fact(
        [clip['clip_id'], 'observed_order', before['label'], after['label']],
        f"I {before_a} before I {after_a}.",
        before['source_ids'] + after['source_ids'],
        [before['target'], after['target']],
    )
    fact.update(
        observed_relation='before',
        order_pair={
            'before': {'operation': before['label'], 'target': before['target'], 'interval_frames': [before['start_frame'], before['end_frame_exclusive']]},
            'after': {'operation': after['label'], 'target': after['target'], 'interval_frames': [after['start_frame'], after['end_frame_exclusive']]},
        },
    )
    topic = f"Ask which came first in this clip: {before_q} or {after_q}. Answer with the observed order only; do not judge whether it is correct."
    constraints = {
        'observed_order': [before['target'], after['target']],
        'operation_pair': [before['label'], after['label']],
        'answer_relation': 'before',
    }
    return open_candidate(clip, 'observed_order', 'order', topic, [fact], constraints)


def fixed_clip_mcq(trial, clip):
    qualifying = [e for e in clip_errors(trial, clip) if e['duration_s'] + 1e-9 >= ANOMALY_MIN_SECONDS]
    if not qualifying:
        return None
    labels = [int(any(e['labels'][i] for e in qualifying)) for i in range(6)]
    correct = [OPTIONS[i + 1]['id'] for i, flag in enumerate(labels) if flag]
    refs = sorted({s for e in qualifying for s in e['source_ids']})
    qid = clip['clip_id'] + '_mcq_clip_anomaly'
    return {
        'question_id': qid,
        'pair_id': qid,
        'clip_id': clip['clip_id'],
        'kind': 'mcq_anomaly_clip',
        'question': 'Does this clip contain an abnormal operation? If yes, select all applicable anomaly types and identify the abnormal time segments.',
        'options': OPTIONS,
        'correct_option_ids': correct,
        'qualifying_errors': [
            {'event_id': e['event_id'], 'duration_s': e['duration_s'], 'labels': e['labels'], 'source_ids': e['source_ids'], 'interval_frames': [e['start_frame'], e['end_frame_exclusive']]}
            for e in qualifying
        ],
        'minimum_anomaly_seconds': ANOMALY_MIN_SECONDS,
        'answer_requires_per_segment_time_and_visual_evidence': True,
        'gt_source_ids': refs,
        'generation': 'deterministic_gt_after_visual_selection',
        'human_review': 'unreviewed',
    }


def build_candidates(trial, clip):
    events, full = _events(trial, clip)
    plans, excluded = [], []
    if events:
        overall_fact = _summary_fact(trial, clip, events)
        plans.append(open_candidate(
            clip, 'overall_operation', 'overall',
            'Ask what the main assembly or disassembly operation is in this clip.',
            [overall_fact],
            {
                'required_terms': overall_fact['required_phrases'],
                'required_tool_options': overall_fact['tools'],
                'required_object_options': overall_fact['main_components'],
                'operation': overall_fact['operation'],
                'max_words': 55,
                'forbid_timestamps': True,
            },
        ))
        facts = _detail_facts(trial, clip, events)
        action_count = sum(len(phase['key_actions']) for phase in facts[0]['operation_phases']) if facts else 0
        if facts and action_count >= 2:
            constraints = {
                'required_terms': facts[0]['required_phrases'],
                'max_words': 95,
                'max_sentences': 4,
                'summarize_phases': True,
                'omit_hand_motion_changes': True,
            }
            plans.append(open_candidate(
                clip, 'detailed_operation', 'detailed',
                'Ask for a concise description of the main tool-and-component operation phases in chronological order. Do not ask for every atomic hand action.',
                facts, constraints,
            ))
        else:
            excluded.append({'kind': 'detailed_operation', 'reason': 'fewer_than_two_distinct_main_actions'})
    else:
        excluded.extend([{'kind': 'overall_operation', 'reason': 'no_non_null_event'}, {'kind': 'detailed_operation', 'reason': 'no_non_null_event'}])
    completions, completion_excluded = _completion_questions(trial, clip, events)
    plans.extend(completions)
    excluded.extend(completion_excluded)
    if not events:
        excluded.append({'kind': 'observed_order', 'reason': 'no_events'})
    else:
        order = _order_question(trial, clip, full)
        if order:
            plans.append(order)
        else:
            excluded.append({'kind': 'observed_order', 'reason': 'no_distinct_complete_nonoverlapping_component_operation_pair'})
    durations = _duration_questions(trial, clip)
    if durations:
        plans.extend(durations)
    else:
        excluded.append({'kind': 'operation_duration', 'reason': 'no_distinct_action_episode_at_least_5_seconds'})
    mcq = fixed_clip_mcq(trial, clip)
    if mcq is None:
        excluded.append({'kind': 'mcq_anomaly_clip', 'reason': 'no_complete_atr_anomaly_at_least_5_seconds'})
    validate_plan(trial, clip, plans, [mcq] if mcq else [])
    candidates = []
    for q in plans:
        candidate = {
            'candidate_id': q['candidate_id'], 'kind': q['kind'], 'topic': q['topic'],
            'answer_constraints': q['answer_constraints'], 'gt_facts': q['reference_facts'],
            'selection_rule': 'select only when the complete clip visibly supports a useful, non-redundant answer',
        }
        if q['kind'] == 'detailed_operation':
            candidate['action_count'] = q['reference_facts'][0]['event_count']
            candidate['phase_count'] = q['reference_facts'][0]['phase_count']
        candidates.append(candidate)
    if mcq:
        candidates.append({'candidate_id': mcq['question_id'], 'kind': mcq['kind'], 'topic': 'The fixed question asks whether this clip contains an anomaly, and if so its GT-defined type and interval.', 'question': mcq['question'], 'gt_facts': mcq['qualifying_errors'], 'selection_rule': 'include only when at least one qualifying anomaly is visually supported by the clip'})
    return plans, mcq, candidates, excluded


def normalized(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9.]+', ' ', text.lower())).strip()


def validate_plan(trial, clip, plans, mcqs):
    ids = [q['question_id'] for q in plans + mcqs]
    if len(ids) != len(set(ids)) or len(plans) > 10 or len(mcqs) > 1:
        raise ValueError('v27_plan:duplicate_or_excess_questions')
    for q in plans + mcqs:
        if not q.get('gt_source_ids') or any(s not in trial['source_catalog'] for s in q['gt_source_ids']):
            raise ValueError('v27_plan:missing_source:' + q['question_id'])
    durations = [q for q in plans if q['kind'] == 'operation_duration']
    for index, first in enumerate(durations):
        a = first['reference_facts'][0]
        for second in durations[index + 1:]:
            b = second['reference_facts'][0]
            same_target = normalized(a['operation_window']['target']) == normalized(b['operation_window']['target'])
            overlaps = a['interval_s'][0] < b['interval_s'][1] and b['interval_s'][0] < a['interval_s'][1]
            if same_target and overlaps:
                raise ValueError('v27_plan:duplicate_overlapping_duration_target')
    detailed = next((q for q in plans if q['kind'] == 'detailed_operation'), None)
    expected = [e['event_id'] for e in trial['events'] if e['action'] != 'null' and overlap(e, clip)]
    observed = detailed['reference_facts'][0].get('covered_event_ids', []) if detailed and detailed['reference_facts'] else []
    if detailed and (len(detailed['reference_facts']) != 1 or observed != expected):
        raise ValueError('v27_plan:detailed_sequence_coverage')
    for q in plans:
        for f in q['reference_facts']:
            if q['kind'] == 'operation_duration':
                start, end = f['interval_s']
                if end - start + 1e-9 < ANOMALY_MIN_SECONDS:
                    raise ValueError('v27_plan:duration_below_5_seconds')
    for q in mcqs:
        if 'A' in q['correct_option_ids'] or not q['correct_option_ids'] or any(e['duration_s'] < ANOMALY_MIN_SECONDS for e in q['qualifying_errors']):
            raise ValueError('v27_plan:mcq_anomaly_filter')
    for q in plans:
        if q['kind'] == 'observed_order':
            pair = q['reference_facts'][0].get('order_pair')
            if not pair or not _distinct_targets(pair['before']['target'], pair['after']['target']):
                raise ValueError('v27_plan:order_pair_must_use_distinct_targets')
        if q['kind'] == 'step_completion':
            fact = q['reference_facts'][0]
            if fact.get('verdict') == 'no' and not fact.get('completed_components'):
                raise ValueError('v27_plan:negative_completion_requires_completed_component')


def validate_selection(value, candidates, sampled_frames):
    expected = {c['candidate_id']: c for c in candidates}
    rows = value.get('items', [])
    if {r['candidate_id'] for r in rows} != set(expected) or len(rows) != len(expected):
        raise ValueError('v27_select:candidate_coverage')
    allowed_frames = {f['frame_id'] for f in sampled_frames}
    frames = {f['frame_id']: f for f in sampled_frames}
    for row in rows:
        candidate = expected[row['candidate_id']]
        if any(f not in allowed_frames for f in row['evidence_frame_ids']):
            raise ValueError('v27_select:unknown_evidence_frame:' + row['candidate_id'])
        if row['include'] and row['visual_support'] == 'conflicts_with_gt':
            raise ValueError('v27_select:cannot_include_visual_conflict:' + row['candidate_id'])
        if row['include'] and row['visual_support'] == 'supports_visible_outcome' and not row['evidence_frame_ids']:
            raise ValueError('v27_select:visible_support_requires_evidence:' + row['candidate_id'])
        if row['include'] and candidate['kind'] == 'mcq_anomaly_clip' and (row['visual_support'] != 'supports_visible_outcome' or not row['evidence_frame_ids']):
            raise ValueError('v27_select:mcq_requires_visual_support:' + row['candidate_id'])
        if row['include'] and candidate['kind'] == 'mcq_anomaly_clip':
            evidence = set(row['evidence_frame_ids'])
            interval_frames = {
                frame_id
                for error in candidate['gt_facts']
                for frame_id, frame in frames.items()
                if error['interval_frames'][0] <= frame['source_frame_index'] < error['interval_frames'][1]
            }
            if not evidence.intersection(interval_frames):
                raise ValueError('v27_select:mcq_evidence_outside_atr_intervals:' + row['candidate_id'])


def _contains(text, phrase):
    value, target = normalized(text), normalized(phrase)
    return bool(target) and target in value


def _compact_gt_fact(fact, kind):
    value = {'fact_id': fact['fact_id']}
    if kind == 'overall_operation':
        value.update({key: fact.get(key, []) for key in ['operation', 'tools', 'parts', 'components', 'main_components']})
    elif kind == 'detailed_operation':
        value['operation_phases'] = [
            {key: phase[key] for key in ['operation', 'target', 'tools_in_phase', 'key_actions'] if key in phase}
            for phase in fact.get('operation_phases', [])
        ]
        value['phase_count'] = fact.get('phase_count', len(value['operation_phases']))
        value['event_count'] = fact.get('event_count', 0)
    elif kind == 'step_completion':
        value.update({key: fact[key] for key in ['verdict', 'queried_component', 'completed_components', 'operation', 'state'] if key in fact})
    elif kind == 'observed_order':
        value['order_pair'] = fact.get('order_pair')
        value['observed_relation'] = fact.get('observed_relation')
    elif kind == 'operation_duration':
        value['operation_window'] = fact.get('operation_window')
        value['numeric'] = fact.get('numeric')
        value['interval_s'] = fact.get('interval_s')
    if kind != 'overall_operation':
        value['required_terms'] = fact.get('required_phrases', [])
    return value


def validate_generated(value, candidates, sampled_frames):
    expected = {q['candidate_id'] for q in candidates}
    rows = value.get('items', [])
    if {r['candidate_id'] for r in rows} != expected or len(rows) != len(expected):
        raise ValueError('v27_contract:candidate_coverage')
    by_id = {q['candidate_id']: q for q in candidates}
    allowed_frames = {frame['frame_id'] for frame in sampled_frames}
    for row in rows:
        candidate = by_id[row['candidate_id']]
        kind = candidate['kind']
        question_text = row['question'].strip()
        answer_text = row['answer'].strip()
        if not question_text.endswith('?') or not answer_text:
            raise ValueError('v27_contract:empty_or_non_question:' + row['candidate_id'])
        if len(re.findall(r"\b[\w'-]+\b", question_text)) > 45:
            raise ValueError('v27_contract:question_too_long:' + row['candidate_id'])
        if re.search(r'\b(annotation|annotated|ground truth|dataset|ASR|GT)\b', question_text + ' ' + answer_text, re.I):
            raise ValueError('v27_contract:internal_prose:' + row['candidate_id'])
        if row['visual_support'] == 'conflicts_with_gt':
            raise ValueError('v27_contract:generated_visual_conflict:' + row['candidate_id'])
        fact_by_id = {fact['fact_id']: fact for fact in candidate['reference_facts']}
        if set(row['source_fact_ids']) != set(fact_by_id):
            raise ValueError('v27_contract:source_fact_coverage:' + row['candidate_id'])
        if any(frame_id not in allowed_frames for frame_id in row['evidence_frame_ids']):
            raise ValueError('v27_contract:unknown_evidence_frame:' + row['candidate_id'])
        selected_frames = set(candidate.get('selection_evidence_frame_ids', []))
        if any(frame_id not in selected_frames for frame_id in row['evidence_frame_ids']):
            raise ValueError('v27_contract:evidence_not_selected:' + row['candidate_id'])
        if row['visual_support'] == 'supports_visible_outcome' and not row['evidence_frame_ids']:
            raise ValueError('v27_contract:visible_claim_without_frame:' + row['candidate_id'])
        required = [] if kind == 'overall_operation' else list(candidate.get('answer_constraints', {}).get('required_terms', []))
        if kind != 'overall_operation':
            required.extend(term for fact in candidate['reference_facts'] for term in fact.get('required_phrases', []))
        for term in dict.fromkeys(required):
            if not _contains(answer_text, term):
                raise ValueError('v27_contract:missing_grounded_term:' + row['candidate_id'] + ':' + term)
        for fact in candidate['reference_facts']:
            numeric = fact.get('numeric')
            if numeric and numeric.get('mode') == 'duration' and not re.search(r'(?<![\d.])' + re.escape(numeric['display']) + r'(?![\d.])', answer_text):
                raise ValueError('v27_contract:numeric_duration:' + row['candidate_id'])
            if numeric and numeric.get('mode') == 'start_end':
                for field in ['display_start', 'display_end']:
                    if not re.search(r'(?<![\d.])' + re.escape(numeric[field]) + r'(?![\d.])', answer_text):
                        raise ValueError('v27_contract:numeric_bounds:' + row['candidate_id'])
        constraints = candidate.get('answer_constraints', {})
        if kind == 'overall_operation':
            operation = constraints.get('operation')
            operation_pattern = r'\b(assemble|assembly|assembling|assembled)\b' if operation == 'assembly' else r'\b(disassemble|disassembly|dismantle|dismantling|dismantled)\b'
            if not re.search(operation_pattern, answer_text, re.I):
                raise ValueError('v27_contract:overall_operation_missing:' + row['candidate_id'])
            tool_options = constraints.get('required_tool_options', [])
            object_options = constraints.get('required_object_options', [])
            if tool_options and not any(_contains(answer_text, term) for term in tool_options):
                raise ValueError('v27_contract:overall_tool_missing:' + row['candidate_id'])
            if object_options and not any(_contains(answer_text, term) for term in object_options):
                raise ValueError('v27_contract:overall_object_missing:' + row['candidate_id'])
            if len(re.findall(r"\b[\w'-]+\b", answer_text)) > constraints.get('max_words', 55):
                raise ValueError('v27_contract:overall_answer_too_long:' + row['candidate_id'])
            if constraints.get('forbid_timestamps') and re.search(r'\b\d+(?:\.\d+)?\s*(?:s|sec|seconds)\b', answer_text, re.I):
                raise ValueError('v27_contract:overall_timestamp:' + row['candidate_id'])
        elif kind == 'detailed_operation':
            word_count = len(re.findall(r"\b[\w'-]+\b", answer_text))
            if word_count > constraints.get('max_words', 95):
                raise ValueError('v27_contract:detailed_answer_too_long:' + row['candidate_id'])
            sentence_count = len([part for part in re.split(r'(?<=[.!?])\s+', answer_text) if part.strip()])
            if sentence_count > constraints.get('max_sentences', 4):
                raise ValueError('v27_contract:detailed_sentence_count:' + row['candidate_id'])
            if re.search(r'\bmy\s+(?:left|right)\s+hand\b', answer_text, re.I):
                raise ValueError('v27_contract:detailed_hand_motion_list:' + row['candidate_id'])
        elif kind == 'step_completion':
            polarity = constraints.get('expected_polarity')
            if polarity and not re.match(r'^\s*' + polarity + r'\b', answer_text, re.I):
                raise ValueError('v27_contract:completion_polarity:' + row['candidate_id'])
            target = constraints.get('queried_component')
            if target and not _contains(question_text, target):
                raise ValueError('v27_contract:completion_target_missing_from_question:' + row['candidate_id'])
        elif kind == 'observed_order':
            before, after = constraints['observed_order']
            if not _contains(question_text, before) or not _contains(question_text, after):
                raise ValueError('v27_contract:order_targets_missing_from_question:' + row['candidate_id'])
            clean_answer = normalized(answer_text)
            before_match = re.search(r'\b' + re.escape(normalized(before)) + r'\b', clean_answer)
            after_match = re.search(r'\b' + re.escape(normalized(after)) + r'\b', clean_answer)
            before_position = before_match.start() if before_match else -1
            after_position = after_match.start() if after_match else -1
            if before_position < 0 or after_position < 0 or before_position >= after_position or not re.search(r'\b(before|then|followed by|first)\b', answer_text, re.I):
                raise ValueError('v27_contract:order_relation_or_sequence:' + row['candidate_id'])
        elif kind == 'operation_duration':
            if not re.search(r'\b(how long|duration|what time|when|from what time|at what time|start and end|begin and finish)\b', question_text, re.I):
                raise ValueError('v27_contract:duration_question_focus:' + row['candidate_id'])
            target = constraints.get('operation_window', {}).get('target')
            if target and (not _contains(question_text, target) or not _contains(answer_text, target)):
                raise ValueError('v27_contract:duration_target_missing:' + row['candidate_id'])
        if len(re.findall(r"\b[\w'-]+\b", answer_text)) > 140:
            raise ValueError('v27_contract:answer_too_long:' + row['candidate_id'])


def validate_review(value, plans):
    if sorted(r['question_id'] for r in value['items']) != sorted(q['candidate_id'] for q in plans):
        raise ValueError('v27_review:question_coverage')
    allowed = {q['candidate_id']: {f['fact_id'] for f in q['reference_facts']} for q in plans}
    for row in value['items']:
        if any(f not in allowed[row['question_id']] for f in row['unsupported_fact_ids']):
            raise ValueError('v27_review:wrong_fact')
        if row['verdict'] == 'keep' and (row['severity'] != 'none' or row['unsupported_fact_ids'] or row['visual_support'] == 'conflicts_with_gt'):
            raise ValueError('v27_review:keep_conflict')
