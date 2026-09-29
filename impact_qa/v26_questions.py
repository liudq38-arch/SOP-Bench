import re

from impact_qa.common import fingerprint
from impact_qa.v26_data import OPTIONS, clip_errors, human, normal_scope


KINDS = ['action_sequence', 'step_completion', 'tools_parts', 'observed_order', 'duration']
TOOL_NAMES = {'tool', 'combination_wrench', 'flat_head_screwdriver', 'phillips_screwdriver', 'torx_screwdriver'}


def overlap(a, b):
    return a['start_frame'] < b['end_frame_exclusive'] and b['start_frame'] < a['end_frame_exclusive']


def state_at(trial, frame):
    rows = [r for r in trial['state_rows'] if r['frame'] <= frame]
    return rows[-1] if rows else None


def relation(a, b):
    if a['end_frame_exclusive'] <= b['start_frame']:
        return 'before'
    if b['end_frame_exclusive'] <= a['start_frame']:
        return 'after'
    return 'overlap'


def occurrence_name(event, events):
    matches = [e for e in events if e['action'] == event['action'] and e['hand'] == event['hand']]
    rank = next(i + 1 for i, e in enumerate(matches) if e['event_id'] == event['event_id'])
    ordinal = {1: 'first', 2: 'second', 3: 'third'}.get(rank, str(rank) + ('th' if 10 <= rank % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(rank % 10, 'th')))
    return f"my {ordinal} fully shown {event['hand']}-hand {human(event['verb'])} operation involving the {human(event['noun'])}"


def clock_interval(e, clip):
    return [(max(e['start_frame'], clip['start_frame']) - clip['start_frame']) / clip['fps'], (min(e['end_frame_exclusive'], clip['end_frame_exclusive']) - clip['start_frame']) / clip['fps']]


def make_fact(key, text, refs, required=None, interval=None, event_ids=None, verdict=None, numeric=None):
    value = {'fact_id': 'f_' + fingerprint(key)[:12], 'reference_text': text, 'source_ids': sorted(set(refs)), 'required_phrases': required or [], 'event_ids': event_ids or []}
    if interval is not None:
        value['interval_s'] = interval
    if verdict is not None:
        value['verdict'] = verdict
    if numeric is not None:
        value['numeric'] = numeric
    return value


def question(clip, kind, slot, text, facts):
    qid = clip['clip_id'] + '_' + slot
    return {'question_id': qid, 'pair_id': qid, 'clip_id': clip['clip_id'], 'kind': kind, 'question': text, 'reference_facts': facts, 'reference_answer': render_units(kind, [{'fact_id': f['fact_id'], 'text': f['reference_text']} for f in facts], facts), 'gt_source_ids': sorted({s for f in facts for s in f['source_ids']}), 'human_review': 'unreviewed'}


def render_units(kind, units, facts):
    by_id = {u['fact_id']: u['text'].strip() for u in units}
    return '\n'.join(by_id[f['fact_id']] for f in facts)


def fixed_mcq(trial, clip):
    scopes = []
    for error in clip_errors(trial, clip):
        atoms = [e for e in trial['events'] if e['hand'] == error['hand'] and overlap(e, error) and e['phase'] == 'anomaly']
        if not atoms:
            continue
        local_labels = [int(any(e['labels'][i] for e in atoms)) for i in range(6)]
        if local_labels != error['labels']:
            continue
        scopes.append((error, [OPTIONS[i + 1]['id'] for i, flag in enumerate(local_labels) if flag], sorted(set(error['source_ids'] + [s for e in atoms for s in e['source_ids']]))))
    normal = normal_scope(trial, clip)
    if normal:
        scopes.append((normal, ['A'], normal['source_ids']))
    result = []
    for e, labels, refs in scopes:
        times = clock_interval(e, clip)
        qid = clip['clip_id'] + '_mcq_' + e['event_id']
        action_name = e.get('action') or (e.get('action_names') or [None])[0]
        action = f" ({human(action_name)})" if action_name else ''
        result.append({'question_id': qid, 'pair_id': qid, 'clip_id': clip['clip_id'], 'kind': 'mcq_anomaly_types', 'question': f"Which descriptions apply to my {e['hand']}-hand operation{action} from {times[0]:.2f} to {times[1]:.2f} seconds in this clip? Select all that apply.", 'options': OPTIONS, 'correct_option_ids': labels, 'target_hand': e['hand'], 'interval_s': times, 'source_interval_frames': [e['start_frame'], e['end_frame_exclusive']], 'gt_source_ids': refs, 'generation': 'deterministic_gt', 'human_review': 'unreviewed'})
    return result


def build_questions(trial, clip):
    events = [e for e in trial['events'] if e['action'] != 'null' and overlap(e, clip)]
    full = [e for e in events if clip['start_frame'] <= e['start_frame'] and e['end_frame_exclusive'] <= clip['end_frame_exclusive']]
    questions, excluded = [], []
    last = state_at(trial, clip['end_frame_exclusive'] - 1)
    tools = sorted({e['noun'] for e in events if e['noun'] in TOOL_NAMES})
    parts = sorted({e['noun'] for e in events if e['noun'] not in TOOL_NAMES})
    changed_components = sorted({c['component'] for c in trial.get('state_changes', []) if clip['start_frame'] <= c['frame'] < clip['end_frame_exclusive']})
    operation = 'assembly' if clip['workflow'] == 'assemble' else 'disassembly'
    component_names = [human(name) for name in changed_components]
    subject_names = component_names or [human(name) for name in parts]
    subject = ', '.join(subject_names) if subject_names else 'the recorded components'
    summary_parts = [f"Overall, I carry out {operation} work on {subject} during this clip."]
    if tools:
        summary_parts.append('I handle these tools: ' + ', '.join(human(name) for name in tools) + '.')
    if parts:
        summary_parts.append('I handle these parts: ' + ', '.join(human(name) for name in parts) + '.')
    summary_refs = [s for e in events for s in e['source_ids']]
    summary_refs.extend(c.get('source_id') for c in trial.get('state_changes', []) if clip['start_frame'] <= c['frame'] < clip['end_frame_exclusive'] and c.get('source_id'))
    summary_required = ['overall', operation] + [human(name) for name in tools + parts + changed_components]
    facts = [make_fact([clip['clip_id'], 'sequence', 'overall'], ' '.join(summary_parts), summary_refs, summary_required)]
    facts[0]['role'] = 'overall'
    facts[0]['covered_event_ids'] = [e['event_id'] for e in events]
    for e in events:
        verb, noun = human(e['verb']), human(e['noun'])
        fact = make_fact([clip['clip_id'], 'sequence', e['event_id']], f"I {verb} the {noun} with my {e['hand']} hand.", e['source_ids'], [verb, noun, e['hand'] + ' hand'], clock_interval(e, clip), [e['event_id']])
        fact['role'] = 'event'
        facts.append(fact)
    if facts:
        text = f"What complete {operation} operation do I carry out in this clip? First summarize the overall operation, naming all tools and parts, then describe every recorded hand action in chronological order."
        questions.append(question(clip, 'action_sequence', 'sequence', text, facts))
    relevant = {e['noun'] for e in events}
    if last and trial.get('components'):
        target_state = 1 if clip['workflow'] == 'assemble' else 0
        changed = {c['component_index'] for c in trial['state_changes'] if clip['start_frame'] <= c['frame'] < clip['end_frame_exclusive']}
        choices = []
        for desired in [target_state, None]:
            indices = [i for i, value in enumerate(last['state']) if value == target_state] if desired == target_state else [i for i, value in enumerate(last['state']) if value != target_state]
            indices.sort(key=lambda i: (i not in changed, trial['components'][i]['name'] not in relevant, i))
            if indices:
                choices.append(indices[0])
            if len(choices) == 2:
                break
        for ci in choices:
            name = human(trial['components'][ci]['name'])
            state = last['state'][ci]
            verdict = 'yes' if state == target_state else 'no'
            if clip['workflow'] == 'assemble':
                wording = {1: f"Yes. By the end of this clip, the {name} is correctly installed.", 0: f"No. By the end of this clip, the {name} is not installed.", -1: f"No. By the end of this clip, the {name} is installed incorrectly."}[state]
                prompt = f"By the end of this clip, have I correctly installed the {name}?"
            else:
                wording = {0: f"Yes. By the end of this clip, the {name} has been completely removed.", 1: f"No. By the end of this clip, the {name} remains installed.", -1: f"No. By the end of this clip, the {name} is not in the fully removed state."}[state]
                prompt = f"By the end of this clip, have I completely removed the {name}?"
            fact = make_fact([clip['clip_id'], 'state', ci], wording, [last['source_id'], trial['component_source_ids'][str(ci)]], [name], verdict=verdict)
            fact.update(state=state, queried_source_frame=clip['end_frame_exclusive'] - 1, state_effective_frame=last['frame'])
            questions.append(question(clip, 'step_completion', 'completion_' + str(ci), prompt, [fact]))
    else:
        excluded.append({'clip_id': clip['clip_id'], 'kind': 'step_completion', 'reason': 'missing_same_view_state_gt'})
    if events:
        wording = []
        if tools:
            wording.append('The tools I handle are ' + ', '.join(human(n) for n in tools) + '.')
        if parts:
            wording.append('The parts I handle are ' + ', '.join(human(n) for n in parts) + '.')
        fact = make_fact([clip['clip_id'], 'inventory'], ' '.join(wording), [s for e in events for s in e['source_ids']], [human(n) for n in tools + parts], event_ids=[e['event_id'] for e in events])
        questions.append(question(clip, 'tools_parts', 'inventory', 'Which tools and parts do I handle during this clip?', [fact]))
    outcome = 1 if clip['workflow'] == 'assemble' else 0
    accomplished = [c for c in trial['state_changes'] if clip['start_frame'] <= c['frame'] < clip['end_frame_exclusive'] and c['state'] == outcome and last and last['state'][c['component_index']] == outcome]
    if accomplished:
        names = sorted({human(c['component']) for c in accomplished})
        verb = 'correctly installed' if outcome == 1 else 'removed'
        final = 'correctly installed' if outcome == 1 else 'uninstalled'
        fact = make_fact([clip['clip_id'], 'accomplished'], f"The parts I {verb} during this clip and that remain {final} at its end are: " + ', '.join(names) + '.', [last['source_id']] + [c[k] for c in accomplished for k in ['source_id', 'previous_source_id', 'component_source_id']], names)
        questions.append(question(clip, 'tools_parts', 'accomplished', f"Which components do I {'correctly install' if outcome == 1 else 'remove'} during this clip that remain {'correctly installed' if outcome == 1 else 'uninstalled'} at its end?", [fact]))
    else:
        tool_errors = [e for e in clip_errors(trial, clip) if e['labels'][4]]
        if tool_errors:
            target = tool_errors[0]
            atomic = [e for e in full if e['hand'] == target['hand'] and overlap(e, target) and e['labels'][4] and e['noun'] in TOOL_NAMES]
            if atomic:
                e = atomic[0]
                a, b = clock_interval(e, clip)
                noun = human(e['noun'])
                fact = make_fact([clip['clip_id'], 'wrong_tool', e['event_id']], f"No. I use an unsuitable tool for this operation involving the {noun}.", target['source_ids'] + e['source_ids'], [noun], verdict='no')
                questions.append(question(clip, 'tools_parts', 'tool_correctness', f"Do I use a suitable tool for my {e['hand']}-hand {human(e['verb'])} operation involving the {noun} from {a:.2f} to {b:.2f} seconds?", [fact]))
    pair = None
    for a in full:
        for b in full:
            if a['event_id'] != b['event_id'] and a['action'] != b['action'] and a['end_frame_exclusive'] <= b['start_frame']:
                pair = (a, b)
                break
        if pair:
            break
    if pair:
        a, b = pair
        if int(fingerprint(clip['clip_id'])[-1], 16) % 2:
            a, b = b, a
        rel = relation(a, b)
        ta, tb = clock_interval(a, clip), clock_interval(b, clip)
        phrase_a = f"{human(a['verb'])} the {human(a['noun'])} with my {a['hand']} hand"
        phrase_b = f"{human(b['verb'])} the {human(b['noun'])} with my {b['hand']} hand"
        first, second = (phrase_a, phrase_b) if rel == 'before' else (phrase_b, phrase_a)
        fact = make_fact([clip['clip_id'], 'order'], f"I {first} before I {second}.", a['source_ids'] + b['source_ids'], [human(a['noun']), human(b['noun'])], event_ids=[a['event_id'], b['event_id']])
        fact['observed_relation'] = rel
        questions.append(question(clip, 'observed_order', 'order', f"What is the observed order between {occurrence_name(a, full)} and {occurrence_name(b, full)} in this clip?", [fact]))
    else:
        excluded.append({'clip_id': clip['clip_id'], 'kind': 'observed_order', 'reason': 'no_distinct_complete_nonoverlapping_action_pair'})
    if full:
        e = max(full, key=lambda e: (e['end_frame_exclusive'] - e['start_frame'], e['event_id']))
        duration = (e['end_frame_exclusive'] - e['start_frame']) / clip['fps']
        ta, tb = clock_interval(e, clip)
        target = occurrence_name(e, full)
        fact = make_fact([clip['clip_id'], 'duration'], f"The operation lasts {duration:.1f} seconds.", e['source_ids'], numeric={'seconds': duration, 'display': f'{duration:.1f}', 'unit': 'seconds'}, event_ids=[e['event_id']])
        questions.append(question(clip, 'duration', 'duration', f"How long does {target} last?", [fact]))
        verdict = 'yes' if duration >= 60 else 'no'
        fact = make_fact([clip['clip_id'], 'threshold'], f"{verdict.title()}. It lasts {duration:.1f} seconds, so it {'reaches' if verdict == 'yes' else 'does not reach'} one minute.", e['source_ids'], verdict=verdict, numeric={'seconds': duration, 'display': f'{duration:.1f}', 'threshold_seconds': 60}, event_ids=[e['event_id']])
        questions.append(question(clip, 'duration', 'threshold', f"Does {target} last at least one minute?", [fact]))
    excluded.append({'clip_id': clip['clip_id'], 'kind': 'normative_order', 'reason': 'no_authoritative_required_order_for_this_scope'})
    for e in trial['errors']:
        if overlap(e, clip) and not (clip['start_frame'] <= e['start_frame'] and e['end_frame_exclusive'] <= clip['end_frame_exclusive']):
            excluded.append({'clip_id': clip['clip_id'], 'event_id': e['event_id'], 'kind': 'mcq_anomaly_types', 'reason': 'valid_atr_crosses_clip_boundary', 'source_ids': e['source_ids']})
    return questions, fixed_mcq(trial, clip), excluded


def normalized(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9.]+', ' ', text.lower())).strip()


def validate_generated(value, plans, arm):
    rows = value['items']
    if sorted(r['question_id'] for r in rows) != sorted(q['question_id'] for q in plans):
        raise ValueError('v26_contract:question_coverage')
    by_id = {q['question_id']: q for q in plans}
    for row in rows:
        q = by_id[row['question_id']]
        facts = q['reference_facts']
        if [u['fact_id'] for u in row['units']] != [f['fact_id'] for f in facts]:
            raise ValueError('v26_contract:fact_coverage_or_order:' + q['question_id'])
        if arm == 'A' and row['visual_support'] != 'not_applicable':
            raise ValueError('v26_contract:arm_a_visual_claim')
        if arm == 'B' and row['visual_support'] == 'not_applicable':
            raise ValueError('v26_contract:arm_b_visual_missing')
        for u, f in zip(row['units'], facts):
            text = u['text']
            clean = normalized(text)
            if re.search(r'\b(annotation|annotated|ground truth|dataset|ASR|GT)\b', text, re.I):
                raise ValueError('v26_contract:internal_prose:' + f['fact_id'])
            if any(normalized(phrase) not in clean for phrase in f['required_phrases']):
                raise ValueError('v26_contract:missing_entity_action_or_hand:' + f['fact_id'])
            if f.get('verdict') and not re.match(r'^\s*' + f['verdict'] + r'\b', text, re.I):
                raise ValueError('v26_contract:polarity:' + f['fact_id'])
            if f.get('numeric') and not re.search(r'(?<![\d.])' + re.escape(f['numeric']['display']) + r'(?![\d.])', text):
                raise ValueError('v26_contract:numeric:' + f['fact_id'])
            if q['kind'] == 'action_sequence' and re.search(r'\b\d+(?:\.\d+)?\s*(?:s|sec|seconds)\b', text, re.I):
                raise ValueError('v26_contract:action_sequence_timestamp:' + f['fact_id'])
            if q['kind'] == 'action_sequence' and re.search(r'\b(then|next|before|after|simultaneously|while)\b', text, re.I):
                raise ValueError('v26_contract:unsupported_sequence_connector:' + f['fact_id'])


def validate_plan(trial, clip, plans, mcqs):
    ids = [q['question_id'] for q in plans + mcqs]
    if len(ids) != len(set(ids)) or len(plans) > 8:
        raise ValueError('v26_plan:duplicate_or_excess_questions')
    for q in plans + mcqs:
        if not q['gt_source_ids'] or any(s not in trial['source_catalog'] for s in q['gt_source_ids']):
            raise ValueError('v26_plan:missing_source')
    seq = next((q for q in plans if q['kind'] == 'action_sequence'), None)
    expected = [e['event_id'] for e in trial['events'] if e['action'] != 'null' and overlap(e, clip)]
    observed = [f['event_ids'][0] for f in seq['reference_facts'] if f.get('event_ids')] if seq else []
    if seq and observed != expected:
        raise ValueError('v26_plan:sequence_coverage')
    for q in mcqs:
        answers = q['correct_option_ids']
        if not answers or ('A' in answers and len(answers) > 1):
            raise ValueError('v26_plan:mcq_mutual_exclusion')
