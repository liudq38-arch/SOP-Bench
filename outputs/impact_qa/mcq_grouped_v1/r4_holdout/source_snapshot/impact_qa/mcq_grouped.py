from collections import Counter, defaultdict

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl


def option_ids(events):
    return [chr(66 + i) for i in range(6) if any(e['labels'][i] for e in events)]


def cluster_events(events, fps, gap_seconds=0.5):
    groups = []
    for event in sorted(events, key=lambda e: (e['start_frame'], e['end_frame_exclusive'], e['event_id'])):
        if groups and event['start_frame'] <= groups[-1]['end_frame_exclusive'] + round(gap_seconds * fps):
            groups[-1]['events'].append(event)
            groups[-1]['end_frame_exclusive'] = max(groups[-1]['end_frame_exclusive'], event['end_frame_exclusive'])
        else:
            groups.append({'start_frame': event['start_frame'], 'end_frame_exclusive': event['end_frame_exclusive'], 'events': [event]})
    for group in groups:
        group['episode_id'] = 'ep_' + fingerprint(sorted(e['event_id'] for e in group['events']))[:16]
        group['option_ids'] = option_ids(group['events'])
    return groups


def overlap(a, b):
    return a['start_frame'] < b['end_frame_exclusive'] and b['start_frame'] < a['end_frame_exclusive']


def add_type_intervals(event, trial):
    result = dict(event)
    result['type_intervals'] = {}
    for i, flag in enumerate(event['labels']):
        if not flag:
            continue
        rows = []
        for action in trial['events']:
            if action['hand'] != event['hand'] or not action['labels'][i] or not overlap(action, event):
                continue
            rows.append({'interval_frames': [max(action['start_frame'],event['start_frame']), min(action['end_frame_exclusive'],event['end_frame_exclusive'])], 'source_ids': action['source_ids'], 'action': action['action']})
        if not rows:
            raise ValueError('mcq_grouped:no_type_source_interval:' + event['event_id'])
        result['type_intervals'][chr(66+i)] = rows
    return result


def build_units(parent, config):
    clips = read_jsonl(parent / 'manifest.jsonl')
    trials = {vid: read_json(parent / 'trials' / (vid + '.json')) for vid in sorted({c['video_id'] for c in clips})}
    owners, eligible = defaultdict(list), {}
    for clip in clips:
        rows = [add_type_intervals(e, trials[clip['video_id']]) for e in trials[clip['video_id']]['errors'] if e['duration_s'] + 1e-9 >= config['minimum_anomaly_seconds'] and clip['start_frame'] <= e['start_frame'] < e['end_frame_exclusive'] <= clip['end_frame_exclusive']]
        eligible[clip['clip_id']] = rows
        for event in rows:
            owners[event['event_id']].append(clip)
    canonical = {eid: min(rows, key=lambda c: (c['duration_s'], c['clip_id']))['clip_id'] for eid, rows in owners.items()}
    units, parents = [], []
    for clip in clips:
        cid = clip['clip_id']
        events = [e for e in eligible[cid] if canonical[e['event_id']] == cid]
        if not events:
            continue
        episodes = cluster_events(events, clip['fps'], config['episode_gap_seconds'])
        owned_ids = {e['event_id'] for e in events}
        other = [e for e in trials[clip['video_id']]['raw_errors'] if overlap(e, clip) and e['event_id'] not in owned_ids]
        parents.append({'clip_id': cid, 'episode_count': len(episodes), 'owned_event_ids': sorted(owned_ids), 'context_only_event_ids': [e['event_id'] for e in other]})
        packages = [episodes] if len(episodes) <= config['parent_max_episodes'] else [[ep] for ep in episodes]
        for package in packages:
            scope = 'whole_clip' if len(packages) == 1 and not other else 'specified_hand_intervals'
            rows = [e for ep in package for e in ep['events']]
            unit_id = 'mq_' + fingerprint([cid, sorted(e['event_id'] for e in rows)])[:16]
            units.append({'unit_id': unit_id, 'parent_clip_id': cid, 'clip': clip, 'scope': scope, 'packaging': 'parent' if len(packages) == 1 else 'episode', 'parent_episode_count': len(episodes), 'episodes': package, 'context_only_events': other, 'correct_option_ids': option_ids(rows), 'formal_release': False, 'human_review': 'unreviewed'})
    report = audit_units(units, owners)
    report.update(manifest_clips=len(clips), candidate_clips=sum(bool(v) for v in eligible.values()), canonical_parents=len(parents), packaging=dict(Counter(u['packaging'] for u in units)), scopes=dict(Counter(u['scope'] for u in units)), parent_episode_distribution=dict(Counter(p['episode_count'] for p in parents)))
    return units, parents, trials, report


def audit_units(units, owners=None):
    errors, seen, ids = [], [], []
    for unit in units:
        ids.append(unit['unit_id'])
        clip = unit['clip']
        events = [e for ep in unit['episodes'] for e in ep['events']]
        seen.extend(e['event_id'] for e in events)
        if unit['correct_option_ids'] != option_ids(events) or not unit['correct_option_ids']:
            errors.append([unit['unit_id'], 'label_union'])
        if unit['scope'] == 'whole_clip' and unit['context_only_events']:
            errors.append([unit['unit_id'], 'incomplete_whole_clip_scope'])
        for e in events:
            if not clip['start_frame'] <= e['start_frame'] < e['end_frame_exclusive'] <= clip['end_frame_exclusive']:
                errors.append([unit['unit_id'], 'event_boundary'])
            if abs(e['duration_s'] - (e['end_frame_exclusive'] - e['start_frame']) / clip['fps']) > 1e-6:
                errors.append([e['event_id'], 'event_clock'])
    if len(ids) != len(set(ids)) or len(seen) != len(set(seen)):
        errors.append(['global', 'duplicate_unit_or_event'])
    if owners is not None and set(seen) != set(owners):
        errors.append(['global', 'lost_event'])
    return {'unit_count': len(units), 'unique_event_count': len(set(seen)), 'hard_errors': errors}


def make_windows(unit, config):
    clip = unit['clip']
    fps = clip['fps']
    windows = []
    context = round(config['context_seconds'] * fps)
    size = round(config['window_seconds'] * fps)
    stride = size - 2 * context
    if stride <= 0:
        raise ValueError('mcq_grouped:window_must_exceed_twice_context')
    for episode in unit['episodes']:
        start = max(clip['start_frame'], episode['start_frame'] - context)
        end = min(clip['end_frame_exclusive'], episode['end_frame_exclusive'] + context)
        pos = start
        while pos < end:
            stop = min(end, pos + size)
            events = [e for e in episode['events'] if e['start_frame'] < stop and e['end_frame_exclusive'] > pos]
            windows.append({'window_id': 'win_' + fingerprint([clip['video_id'], pos, stop])[:16], 'start_frame': pos, 'end_frame_exclusive': stop, 'events': events, 'episode_id': episode['episode_id']})
            if stop == end:
                break
            pos += stride
    return windows


def select_pilot(units, count=12, excluded=None):
    excluded = set(excluded or [])
    pool = [u for u in units if u['unit_id'] not in excluded]
    selected = []
    predicates = [
        lambda u, label=label: label in u['correct_option_ids'] for label in 'BCDEFG'
    ] + [
        lambda u: any(len(ep['events']) > 1 for ep in u['episodes']),
        lambda u: 2 <= len(u['episodes']) <= 4,
        lambda u: u['packaging'] == 'episode',
        lambda u: u['scope'] == 'whole_clip',
        lambda u: u['context_only_events'] and u['clip']['workflow'] == 'disassemble',
        lambda u: any(e['duration_s'] >= 30 for ep in u['episodes'] for e in ep['events']),
    ]
    used_videos = Counter()
    for predicate in predicates:
        available = [u for u in pool if predicate(u) and u not in selected]
        if available and len(selected) < count:
            chosen = min(available, key=lambda u: (used_videos[u['clip']['video_id']], sum(e['duration_s'] for ep in u['episodes'] for e in ep['events']), u['unit_id']))
            selected.append(chosen)
            used_videos[chosen['clip']['video_id']] += 1
    for u in sorted(pool, key=lambda u: u['unit_id']):
        if len(selected) >= count:
            break
        if u not in selected:
            selected.append(u)
    return selected


def normal_controls(trials, count=4):
    result = []
    participants = set()
    for trial in sorted(trials.values(), key=lambda t: t['video_id']):
        participant=trial['video_id'].split('_')[0]
        if participant in participants:
            continue
        fps = trial['fps']
        for event in trial['events']:
            if event['action'] == 'null' or event['phase'] != 'normal' or any(event['labels']):
                continue
            if event['end_frame_exclusive'] - event['start_frame'] < 8 * fps:
                continue
            a, b = event['start_frame'], min(event['end_frame_exclusive'], event['start_frame'] + round(15 * fps))
            scope = {'start_frame': a, 'end_frame_exclusive': b}
            if any(overlap(e, scope) for e in trial['raw_errors']):
                continue
            if any(overlap(e, scope) and (any(e['labels']) or e['phase'] not in ['normal', 'null']) for e in trial['events']):
                continue
            cid = 'control_' + fingerprint([trial['video_id'], a, b])[:16]
            clip = dict(scope, fps=fps, video_id=trial['video_id'], source_video=trial['source_video'], clip_id=cid, duration_s=(b-a)/fps, workflow=trial['workflow'])
            e = dict(event, start_frame=a, end_frame_exclusive=b, duration_s=(b-a)/fps)
            result.append({'unit_id': cid, 'parent_clip_id': cid, 'clip': clip, 'scope': 'control', 'packaging': 'control', 'parent_episode_count': 1, 'episodes': cluster_events([e], fps), 'context_only_events': [], 'correct_option_ids': ['A'], 'formal_release': False, 'human_review': 'unreviewed'})
            participants.add(participant)
            break
        if len(result) >= count:
            break
    return result


def question_record(unit, event_reviews, options, requirement='accepted'):
    rows = [e for ep in unit['episodes'] for e in ep['events']]
    missing = [e['event_id'] for e in rows if not event_reviews.get(e['event_id'], {}).get(requirement)]
    if missing:
        return None, {'unit_id': unit['unit_id'], 'reason': 'not_all_target_events_and_types_supported', 'missing_event_ids': missing}
    clip = unit['clip']
    scopes, segments = [], []
    for e in rows:
        interval = [round((e[k] - clip['start_frame']) / clip['fps'], 3) for k in ['start_frame', 'end_frame_exclusive']]
        scopes.append(f"{e['hand']} hand, {interval[0]:.2f}–{interval[1]:.2f} s")
        segments.append({'event_id': e['event_id'], 'hand': e['hand'], 'clip_interval_s': interval, 'source_interval_frames': [e['start_frame'], e['end_frame_exclusive']], 'option_ids': option_ids([e]), 'gt_source_ids': e['source_ids'], 'type_intervals': e.get('type_intervals',{}), 'visual_review': event_reviews[e['event_id']]})
    question = 'Does this clip contain an abnormal operation? Select all applicable anomaly types and identify the abnormal time segments.' if unit['scope'] == 'whole_clip' else 'Considering only these hand operations (' + '; '.join(scopes) + '), is there an abnormal operation? Select all applicable anomaly types.'
    return {'question_id': unit['unit_id'], 'parent_clip_id': unit['parent_clip_id'], 'kind': 'mcq_anomaly_grouped', 'question': question, 'scope': unit['scope'], 'options': options, 'correct_option_ids': unit['correct_option_ids'], 'abnormal_segments': segments, 'episodes': [{'episode_id': ep['episode_id'], 'event_ids': [e['event_id'] for e in ep['events']]} for ep in unit['episodes']], 'interval_basis': 'ATR GT; visual evidence supports the event, not frame-exact boundary accuracy', 'formal_release': False, 'human_review': 'unreviewed'}, None


def save_preparation(folder, units, parents, report):
    if report['hard_errors']:
        raise ValueError('mcq_grouped:precheck:' + str(report['hard_errors']))
    save_jsonl(folder / 'candidate_units.jsonl', units)
    save_jsonl(folder / 'parent_manifest.jsonl', parents)
    save_json(folder / 'offline_audit.json', report)
    save_jsonl(folder / 'first10_candidates.jsonl', units[:10])
