import hashlib
import os
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from impact_qa.common import ANNOTATIONS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl


CONFIG_PATH = ROOT / os.environ.get('IMPACT_V26_CONFIG', 'configs/impact_qa/component_v26.json')
CONFIG = read_json(CONFIG_PATH)
FOLDER = ROOT / CONFIG['output_root']
ASSEMBLY = {'install_rotor_assembly', 'attach_adapter_plate', 'insert_bearing_plate_assembly', 'install_locking_lever_assembly', 'screw_on_anti_vibration_handle'}
DISASSEMBLY = {'unscrew_anti_vibration_handle', 'remove_locking_lever_assembly', 'extract_bearing_plate_assembly', 'detach_adapter_plate', 'remove_rotor_assembly'}
OPTIONS = [
    {'id': 'A', 'name': 'Correct', 'definition': 'The specified hand operation is explicitly normal throughout the stated scope, with no anomaly or recovery conflict. This does not certify assembly completion.'},
    {'id': 'B', 'name': 'Temporal', 'definition': 'An error concerning when an operation is executed or its temporal organization. The label alone does not identify an exact timing deviation.'},
    {'id': 'C', 'name': 'Spatial', 'definition': 'An error concerning position, orientation or spatial configuration. The label alone does not identify the particular geometry.'},
    {'id': 'D', 'name': 'Handling', 'definition': 'An error in grasping, holding, moving or manipulating an object. This does not itself mean a wrong part or tool was selected.'},
    {'id': 'E', 'name': 'Wrong part', 'definition': 'An unsuitable part is selected or used for the operation. The intended replacement requires separate evidence.'},
    {'id': 'F', 'name': 'Wrong tool', 'definition': 'An unsuitable tool is selected or used for the operation. The correct replacement requires separate evidence.'},
    {'id': 'G', 'name': 'Procedural', 'definition': 'An error concerning procedure requirements. A specific omitted, extra or misordered step requires separate evidence.'},
]


@lru_cache(maxsize=4096)
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source(path, pointer, value):
    path = Path(path)
    record = {'source_path': str(path.relative_to(ROOT)), 'sha256': digest(str(path)), 'pointer': pointer, 'value': value}
    record['source_id'] = 's_' + fingerprint([record['source_path'], pointer, record['sha256']])[:16]
    return record


def merged_intervals(intervals):
    result = []
    for a, b in sorted(intervals):
        if result and a <= result[-1][1]:
            result[-1][1] = max(result[-1][1], b)
        else:
            result.append([a, b])
    return result


def fully_covered(intervals, start, end):
    return any(a <= start and b >= end for a, b in merged_intervals(intervals))


def human(name):
    return name.replace('_', ' ')


def changes(doc):
    result = []
    if not doc or not doc['state_sequence']:
        return result
    previous = doc['state_sequence'][0]['state']
    for index, row in enumerate(doc['state_sequence'][1:], 1):
        for ci, (old, new) in enumerate(zip(previous, row['state'])):
            if old != new:
                result.append({'frame': row['frame'], 'component_index': ci, 'component': doc['components'][ci]['name'], 'previous': old, 'state': new, 'row_index': index, 'previous_row_index': index - 1})
        previous = row['state']
    return result


def component_episodes(steps, workflow):
    active = ASSEMBLY if workflow == 'assemble' else DISASSEMBLY
    result = []
    for step in sorted(steps, key=lambda s: s['start_frame']):
        label = step['label']
        if workflow == 'assemble':
            eligible = label in active or label.startswith(('install_', 'insert_', 'attach_', 'mount_'))
        else:
            eligible = label in active or label.startswith(('remove_', 'extract_', 'detach_', 'dismount_', 'unscrew_', 'uninstall_'))
        if not eligible:
            continue
        if result and result[-1]['label'] == step['label']:
            result[-1]['end_frame_exclusive'] = step['end_frame_exclusive']
            result[-1]['source_ids'].extend(step['source_ids'])
        else:
            result.append({**{k: step[k] for k in ['label', 'start_frame', 'end_frame_exclusive']}, 'source_ids': list(step['source_ids'])})
    return result


def state_operations(trial):
    """Build independent disassembly operations from ASR state transitions.

    A simultaneous transition is one operation group. The resulting clips are
    deliberately allowed to overlap because each component operation gets its
    own four-second visual context on both sides.
    """
    if not trial.get('has_asr') or trial.get('workflow') != 'disassemble':
        return []
    by_component = defaultdict(list)
    for change in trial.get('state_changes', []):
        by_component[change['component_index']].append(change)
    operations = []
    for index, rows in by_component.items():
        onset = next((r for r in rows if r['previous'] == 1 and r['state'] in (-1, 0)), None)
        if onset is None:
            continue
        completion = next((r for r in rows if r['frame'] >= onset['frame'] and r['state'] == 0), None)
        operations.append({
            'operation_id': 'op_' + fingerprint([trial['video_id'], index, onset['frame']])[:16],
            'component_indices': [index],
            'components': [onset['component']],
            'onset_frame': onset['frame'],
            'completion_frame': completion['frame'] if completion else None,
            'end_frame_exclusive': (completion['frame'] + 1) if completion else onset['frame'] + 1,
            'completion_known': completion is not None,
            'source_ids': sorted(set([onset['source_id'], onset['component_source_id']] + ([completion['source_id'], completion['component_source_id']] if completion else []))),
        })
    operations.sort(key=lambda x: (x['onset_frame'], x['end_frame_exclusive'], x['components']))
    groups = []
    tolerance = max(1, round(trial['fps'] * 0.1))
    for operation in operations:
        if groups and operation['onset_frame'] - groups[-1]['onset_frame'] <= tolerance:
            group = groups[-1]
            group['component_indices'].extend(operation['component_indices'])
            group['components'].extend(operation['components'])
            group['end_frame_exclusive'] = max(group['end_frame_exclusive'], operation['end_frame_exclusive'])
            group['completion_known'] = group['completion_known'] and operation['completion_known']
            group['source_ids'] = sorted(set(group['source_ids'] + operation['source_ids']))
            group['operation_ids'].append(operation['operation_id'])
        else:
            groups.append({
                'operation_id': operation['operation_id'],
                'operation_ids': [operation['operation_id']],
                'component_indices': list(operation['component_indices']),
                'components': list(operation['components']),
                'onset_frame': operation['onset_frame'],
                'completion_frame': operation['completion_frame'],
                'end_frame_exclusive': operation['end_frame_exclusive'],
                'completion_known': operation['completion_known'],
                'source_ids': list(operation['source_ids']),
            })
    for group in groups:
        group['components'] = sorted(set(group['components']))
        group['component_indices'] = sorted(set(group['component_indices']))
        group['operation_id'] = 'op_' + fingerprint([trial['video_id'], group['onset_frame'], group['components']])[:16]
    return groups


def clip_record(trial, start, stop, boundary, ordinal):
    fps = trial['fps']
    clip_id_version = CONFIG.get('clip_id_version', CONFIG['version'])
    return {
        'clip_id': CONFIG.get('clip_id_prefix', 'v26') + '_' + fingerprint([trial['video_id'], start, stop, clip_id_version, ordinal])[:16],
        'video_id': trial['video_id'],
        'trial_id': trial['trial_id'],
        'view': trial['view'],
        'workflow': trial['workflow'],
        'has_asr': trial['has_asr'],
        'annotation_splits': trial.get('annotation_splits', []),
        'atr_splits': trial.get('atr_splits', []),
        'asr_split': trial.get('asr_split'),
        'start_frame': start,
        'end_frame_exclusive': stop,
        'source_start_s': start / fps,
        'source_end_s': stop / fps,
        'duration_s': (stop - start) / fps,
        'fps': fps,
        'source_video': trial['source_video'],
        'boundary': boundary,
        'clock': 'nominal_fps_pending_pts_validation',
        'formal_release': False,
    }


def boundaries(trial):
    fps, n = trial['fps'], trial['frame_count']
    episodes = trial['episodes']
    candidates = []
    if trial['workflow'] == 'assemble':
        events = [x for x in trial['state_changes'] if x['state'] == 1]
        if trial['has_asr']:
            grouped = []
            tolerance = max(1, round(fps * 0.1))
            for event in events:
                if grouped and event['frame'] - grouped[-1][0] <= tolerance:
                    grouped[-1][1].append(event)
                else:
                    grouped.append([event['frame'], [event]])
            raw = [(frame, 'asr_completion_plus_2s', sorted({s for e in group for s in [e['source_id']] + ([e['component_source_id']] if 'component_source_id' in e else [])}), sorted({e['component'] for e in group})) for frame, group in grouped]
        else:
            raw = [(e['end_frame_exclusive'], 'action_boundary_plus_2s', e['source_ids'], [e['label']]) for e in episodes]
        for anchor, reason, refs, components in raw:
            stop = min(n, anchor + round(CONFIG['assembly_tail_seconds'] * fps))
            expanded = []
            while True:
                hit = [e for e in episodes if e['start_frame'] < stop < e['end_frame_exclusive']]
                if not hit:
                    break
                expanded.extend(s for e in hit for s in e['source_ids'])
                stop = min(n, max(e['end_frame_exclusive'] for e in hit) + round(CONFIG['assembly_tail_seconds'] * fps))
            candidates.append({'frame': stop, 'reason': reason, 'anchor_frame': anchor, 'components': components, 'source_ids': sorted(set(refs + expanded)), 'merged_active_process': bool(expanded)})
    elif trial['workflow'] == 'disassemble':
        operations = trial.get('component_operations') or [
            {
                'operation_id': 'step_' + fingerprint([trial['video_id'], e['start_frame'], e['end_frame_exclusive']])[:16],
                'components': [e['label']],
                'component_indices': [],
                'onset_frame': e['start_frame'],
                'completion_frame': e['end_frame_exclusive'] - 1,
                'end_frame_exclusive': e['end_frame_exclusive'],
                'completion_known': False,
                'source_ids': e['source_ids'],
            }
            for e in episodes
        ]
        # Unlike assembly, these are independent windows, so overlapping
        # component clips are retained instead of being partitioned.
        result = []
        for ordinal, operation in enumerate(operations):
            start = max(0, operation['onset_frame'] - round(CONFIG['disassembly_preroll_seconds'] * fps))
            stop = min(n, operation['end_frame_exclusive'] + round(CONFIG['disassembly_preroll_seconds'] * fps))
            if stop <= start:
                continue
            boundary = {
                'reason': 'component_disassembly_onset_minus4s_completion_plus4s',
                'rule': 'independent_component_window',
                'operation_id': operation['operation_id'],
                'operation_ids': operation.get('operation_ids', [operation['operation_id']]),
                'components': sorted(set(operation.get('components', []))),
                'component_indices': operation.get('component_indices', []),
                'onset_frame': operation['onset_frame'],
                'completion_frame': operation.get('completion_frame'),
                'completion_known': operation.get('completion_known', False),
                'source_ids': operation.get('source_ids', []),
                'preroll_s': (operation['onset_frame'] - start) / fps,
                'tail_s': (stop - operation['end_frame_exclusive']) / fps,
            }
            result.append(clip_record(trial, start, stop, boundary, ordinal))
        for i, clip in enumerate(result):
            clip['boundary']['overlaps_clip_ids'] = [other['clip_id'] for j, other in enumerate(result) if i != j and other['start_frame'] < clip['end_frame_exclusive'] and clip['start_frame'] < other['end_frame_exclusive']]
        return result
    unique = {}
    for item in candidates:
        frame = item['frame']
        if 0 < frame < n:
            if frame in unique:
                unique[frame]['source_ids'] = sorted(set(unique[frame]['source_ids'] + item['source_ids']))
                unique[frame]['components'] = sorted(set(unique[frame]['components'] + item['components']))
            else:
                unique[frame] = item
    unique[n] = {'frame': n, 'reason': 'source_video_end', 'source_ids': [], 'components': []}
    result, start = [], 0
    for stop in sorted(unique):
        result.append(clip_record(trial, start, stop, unique[stop], len(result)))
        start = stop
    return result


def load_index():
    parts = defaultdict(set)
    for task, dirs in [('TAS-B', ['splits_TAS-BL', 'splits_TAS-BR']), ('TAS-S', ['splits'])]:
        for directory in dirs:
            for part in ['train', 'val', 'test']:
                p = ANNOTATIONS / task / directory / f'{part}.split1.bundle'
                if p.exists():
                    for name in p.read_text().split():
                        parts[name.removesuffix('.txt')].add(part)
    asr_parts = {}
    for part in ['train', 'val', 'test']:
        for name in (ANNOTATIONS / 'ASR/splits' / f'{part}.split1.bundle').read_text().split():
            asr_parts[name.removesuffix('.txt')] = part
    atr = defaultdict(list)
    for hand in ['L', 'R']:
        for part in ['train', 'val', 'test']:
            p = ANNOTATIONS / f'ATR/atr_segments_{hand}/{part}.split1.jsonl'
            for i, row in enumerate(read_jsonl(p)):
                if row['view'] == CONFIG['view']:
                    atr[row['video_id']].append((row, source(p, f'/jsonl/{i}', row)))
    trials, excluded = [], []
    for p in sorted((ANNOTATIONS / 'TAS-B' / CONFIG['view']).glob('*.json')):
        d = read_json(p)
        vid = d['video_id']
        fps = d['meta_data']['fps']
        n = d['meta_data']['num_frames']
        catalog = {}
        def add(ref):
            catalog[ref['source_id']] = ref
            return ref['source_id']
        actions = {v['id']: v['name'] for v in d['action_labels']}
        verbs = {v['id']: v['name'] for v in d['verbs']}
        nouns = {v['id']: v['name'] for v in d['nouns']}
        events = []
        for i, row in enumerate(d['segments']):
            ref = add(source(p, f'/segments/{i}', row))
            events.append({'event_id': 'e_' + fingerprint([vid, i])[:16], 'video_id': vid, 'start_frame': row['start_frame'], 'end_frame_exclusive': row['end_frame'] + 1, 'hand': row['entity'], 'action': actions[row['action_label']], 'verb': verbs.get(row['verb'], 'null'), 'noun': nouns.get(row['noun'], 'null'), 'phase': row['phase'], 'labels': row['anomaly_type'], 'source_ids': [ref]})
        valid_partition = all(fully_covered([(e['start_frame'], e['end_frame_exclusive']) for e in events if e['hand'] == hand], 0, n) for hand in ['left', 'right'])
        step_path = ANNOTATIONS / 'TAS-S' / CONFIG['view'] / (vid + '.json')
        steps = []
        if step_path.exists():
            for i, row in enumerate(read_json(step_path)['segments']):
                steps.append({'label': row['label'], 'start_frame': row['f_start'], 'end_frame_exclusive': row['f_end'] + 1, 'source_ids': [add(source(step_path, f'/segments/{i}', row))]})
        asr_path = ANNOTATIONS / 'ASR/annotations' / (vid + '_asr.json')
        asr = read_json(asr_path) if asr_path.exists() else None
        if asr and (asr['fps'] != fps or asr['frame_count'] != n):
            raise ValueError(f'v26_data:asr_clock:{vid}')
        state_changes = changes(asr)
        state_rows = []
        component_sources = {}
        if asr:
            component_sources = {str(i): add(source(asr_path, f'/components/{i}', c)) for i, c in enumerate(asr['components'])}
            for i, row in enumerate(asr['state_sequence']):
                ref = add(source(asr_path, f'/state_sequence/{i}', row))
                state_rows.append(dict(row, source_id=ref))
            for change in state_changes:
                change['source_id'] = state_rows[change['row_index']]['source_id']
                change['previous_source_id'] = state_rows[change['previous_row_index']]['source_id']
                change['component_source_id'] = component_sources[str(change['component_index'])]
        errors, raw_errors = [], []
        for row, ref in atr[vid]:
            sid = add(ref)
            action_names = sorted({actions.get(i, 'null') for i in row.get('source_action_labels', []) if actions.get(i, 'null') != 'null'})
            error = {'event_id': 'a_' + fingerprint([vid, row['entity'], row['start_frame'], row['end_frame']])[:16], 'video_id': vid, 'hand': row['entity'], 'start_frame': row['start_frame'], 'end_frame_exclusive': row['end_frame'] + 1, 'duration_s': row['num_frames'] / fps, 'labels': row['labels'], 'action_names': action_names, 'source_ids': [sid], 'part': row['part'], 'source_segment_count': row['source_segment_count']}
            if error['end_frame_exclusive'] - error['start_frame'] != row['num_frames']:
                raise ValueError(f'v26_data:atr_endpoints:{vid}')
            raw_errors.append(error)
            if row['num_frames'] + 1e-9 < CONFIG['minimum_error_seconds'] * fps:
                excluded.append(dict(error, reason='atr_duration_below_1_5s', raw_gt_retained=True))
            else:
                errors.append(error)
        intervals = merged_intervals([(x['start_frame'], x['end_frame_exclusive']) for x in errors])
        source_video = Path(CONFIG['source_root']) / CONFIG['view'] / (vid + '.mp4')
        train = parts.get(vid) == {'train'} and all(r['part'] == 'train' for r in raw_errors) and (not asr or asr_parts.get(vid) == 'train')
        workflow = 'assemble' if '_Reassembly_' in vid else 'disassemble'
        trial = {'video_id': vid, 'trial_id': vid.rsplit('_', 1)[0], 'participant': vid.split('_')[0], 'view': CONFIG['view'], 'workflow': workflow, 'fps': fps, 'frame_count': n, 'source_video': str(source_video), 'has_asr': bool(asr), 'annotation_splits': sorted(parts.get(vid, set())), 'atr_splits': sorted({row['part'] for row, _ in atr[vid]}), 'asr_split': asr_parts.get(vid) if asr else None, 'components': asr['components'] if asr else [], 'state_rows': state_rows, 'state_changes': state_changes, 'events': sorted(events, key=lambda e: (e['start_frame'], e['end_frame_exclusive'], e['hand'])), 'steps': steps, 'errors': errors, 'raw_errors': raw_errors, 'source_catalog': catalog, 'split_eligible': train, 'partition_complete': valid_partition, 'media_available': source_video.exists(), 'valid_error_episodes': len(intervals), 'valid_error_seconds': sum(b - a for a, b in intervals) / fps, 'raw_error_count': len(raw_errors)}
        trial['episodes'] = component_episodes(steps, workflow)
        trial['component_source_ids'] = component_sources
        if not trial['episodes']:
            prefixes = ('insert', 'seat', 'attach', 'tighten', 'hand_tighten', 'screw_on') if workflow == 'assemble' else ('remove', 'detach', 'extract', 'unscrew')
            active = [e for e in events if e['verb'].startswith(prefixes)]
            groups = merged_intervals([(e['start_frame'], e['end_frame_exclusive']) for e in active])
            trial['episodes'] = [{'label': 'tasb_component_operation', 'start_frame': a, 'end_frame_exclusive': b, 'source_ids': sorted({s for e in active if e['start_frame'] < b and e['end_frame_exclusive'] > a for s in e['source_ids']})} for a, b in groups]
        if workflow == 'disassemble':
            trial['component_operations'] = state_operations(trial) if asr else [
                {
                    'operation_id': 'step_' + fingerprint([vid, e['start_frame'], e['end_frame_exclusive'], e['label']])[:16],
                    'operation_ids': ['step_' + fingerprint([vid, e['start_frame'], e['end_frame_exclusive'], e['label']])[:16]],
                    'component_indices': [],
                    'components': [e['label']],
                    'onset_frame': e['start_frame'],
                    'completion_frame': e['end_frame_exclusive'] - 1,
                    'end_frame_exclusive': e['end_frame_exclusive'],
                    'completion_known': False,
                    'source_ids': e['source_ids'],
                }
                for e in trial['episodes']
            ]
        else:
            trial['component_operations'] = []
        trials.append(trial)
    return trials, excluded


def normal_scope(trial, clip):
    start, end = clip['start_frame'], clip['end_frame_exclusive']
    for event in sorted(trial['events'], key=lambda e: (-(e['end_frame_exclusive'] - e['start_frame']), e['event_id'])):
        a, b = event['start_frame'], event['end_frame_exclusive']
        if event['action'] == 'null' or not start <= a < b <= end or event['phase'] != 'normal' or any(event['labels']):
            continue
        conflict = any(other['hand'] == event['hand'] and other['start_frame'] < b and other['end_frame_exclusive'] > a and (other['phase'] != 'normal' or any(other['labels'])) for other in trial['events'])
        conflict |= any(other['hand'] == event['hand'] and other['start_frame'] < b and other['end_frame_exclusive'] > a for other in trial['raw_errors'])
        if not conflict:
            return event
    return None


def clip_errors(trial, clip):
    return [e for e in trial['errors'] if clip['start_frame'] <= e['start_frame'] < e['end_frame_exclusive'] <= clip['end_frame_exclusive']]


def selection_rank(trial):
    if CONFIG.get('selection_mode') == 'long_anomaly_first':
        longest = max((e['duration_s'] for e in trial['errors']), default=0.0)
        return (-longest, -trial['valid_error_seconds'], -trial['raw_error_count'], trial['video_id'])
    return (trial['valid_error_episodes'], trial['valid_error_seconds'], trial['raw_error_count'], trial['video_id'])


def clips_with_actions(trial, clips=None):
    clips = boundaries(trial) if clips is None else clips
    return [
        clip for clip in clips
        if any(
            event['action'] != 'null'
            and event['start_frame'] < clip['end_frame_exclusive']
            and event['end_frame_exclusive'] > clip['start_frame']
            for event in trial['events']
        )
    ]


TAIL_CORE_VERBS = {
    'adjust', 'align', 'attach', 'detach', 'dismount', 'extract', 'flip',
    'hand_loosen', 'hand_spin', 'hand_tighten', 'insert', 'loosen', 'mount',
    'remove', 'seat', 'screw_on', 'thread', 'tighten', 'unscrew',
}


def source_end_cleanup_tail_reason(trial, clip):
    if not CONFIG.get('drop_source_end_cleanup_tails'):
        return None
    if clip.get('boundary', {}).get('reason') != 'source_video_end':
        return None
    start, end = clip['start_frame'], clip['end_frame_exclusive']
    if any(error['start_frame'] < end and error['end_frame_exclusive'] > start for error in trial.get('errors', [])):
        return None
    if any(episode['start_frame'] < end and episode['end_frame_exclusive'] > start for episode in trial.get('episodes', [])):
        return None
    meaningful = any(
        event['action'] != 'null'
        and event['phase'] != 'recovery'
        and event['verb'] in TAIL_CORE_VERBS
        and event['start_frame'] < end
        and event['end_frame_exclusive'] > start
        for event in trial.get('events', [])
    )
    if meaningful:
        return None
    return 'source_end_cleanup_tail_without_component_operation_or_valid_error'


def prepare_index():
    trials, excluded = load_index()
    pool = [t for t in trials if t['split_eligible'] and t['partition_complete'] and t['media_available'] and t['episodes']]
    dataset_pool = [t for t in trials if t['partition_complete'] and t['media_available'] and t['episodes']]
    if CONFIG.get('selection_mode') in ['all_train_clips', 'all_component_clips']:
        selected_pool = pool if CONFIG.get('selection_mode') == 'all_train_clips' else dataset_pool
        selected = sorted(selected_pool, key=lambda trial: (trial['workflow'], trial['video_id']))
        from impact_qa.clip_repair import repair_clips

        all_clips, raw_all_clips, repair_map, manifest, tail_excluded = [], [], [], [], []
        for trial in selected:
            raw_clips = boundaries(trial)
            clips, repairs = repair_clips(trial, raw_clips, CONFIG.get('clip_min_seconds'))
            raw_all_clips.extend(raw_clips)
            repair_map.extend(repairs)
            all_clips.extend(clips)
            for clip in clips_with_actions(trial, clips):
                tail_reason = source_end_cleanup_tail_reason(trial, clip)
                if tail_reason:
                    tail_excluded.append(dict(clip, exclusion_reason=tail_reason))
                    continue
                clip['selection_reason'] = 'all_eligible_train_component_clips'
                clip['raw_error_overlap_count'] = sum(
                    error['start_frame'] < clip['end_frame_exclusive']
                    and error['end_frame_exclusive'] > clip['start_frame']
                    for error in trial['raw_errors']
                )
                manifest.append(clip)
            save_json(FOLDER / 'trials' / (trial['video_id'] + '.json'), trial)
        manifest.sort(key=lambda clip: (clip['workflow'], clip['video_id'], clip['start_frame'], clip['clip_id']))
        if not manifest:
            raise ValueError('v26_selection:empty_all_train_manifest')
        summary = {
            'version': CONFIG['version'],
            'indexed_videos': len(trials),
            'has_asr': sum(trial['has_asr'] for trial in trials),
            'eligible_train_videos': len(pool),
            'eligible_dataset_videos': len(dataset_pool),
            'selected_videos': len(selected),
            'selected_without_asr': sum(not trial['has_asr'] for trial in selected),
            'split_policy': 'all_available_splits_included' if CONFIG.get('selection_mode') == 'all_component_clips' else 'train_only',
            'annotation_split_video_counts': {split: sum(split in trial['annotation_splits'] for trial in selected) for split in ['train', 'val', 'test']},
            'atr_split_video_counts': {split: sum(split in trial['atr_splits'] for trial in selected) for split in ['train', 'val', 'test']},
            'asr_split_video_counts': {split: sum(trial['asr_split'] == split for trial in selected) for split in ['train', 'val', 'test']},
            'participants': sorted({trial['participant'] for trial in selected}),
            'selected_clips': len(manifest),
            'all_clips': len(all_clips),
            'raw_all_clips': len(raw_all_clips),
            'clip_min_seconds': CONFIG.get('clip_min_seconds'),
            'short_raw_clips': sum(clip['duration_s'] < CONFIG.get('clip_min_seconds', 0) for clip in raw_all_clips) if CONFIG.get('clip_min_seconds') else 0,
            'clip_repairs': len(repair_map),
            'merge_operations': sum(row.get('action') == 'merge_adjacent_short_clip' for row in repair_map),
            'repaired_clip_count': sum(row.get('action') == 'repaired_clip' for row in repair_map),
            'extended_clip_count': sum(row.get('action') == 'extend_short_window' for row in repair_map),
            'dropped_short_clip_count': sum(row.get('action') == 'drop_unrepairable_short_clip' for row in repair_map),
            'source_end_cleanup_tail_count': len(tail_excluded),
            'source_end_cleanup_tail_ids': [row['clip_id'] for row in tail_excluded],
            'clip_repair_policy': CONFIG.get('clip_repair_policy'),
            'short_errors_excluded': len(excluded),
            'selected_trials': [{key: trial[key] for key in ['video_id', 'workflow', 'has_asr', 'valid_error_episodes', 'valid_error_seconds', 'raw_error_count']} for trial in selected],
        }
        save_json(FOLDER / 'selection_summary.json', summary)
        save_json(FOLDER / 'mcq_options.json', OPTIONS)
        save_jsonl(FOLDER / 'clips.jsonl', all_clips)
        save_jsonl(FOLDER / 'raw_clips.jsonl', raw_all_clips)
        save_jsonl(FOLDER / 'clip_repair_map.jsonl', repair_map)
        save_jsonl(FOLDER / 'manifest.jsonl', manifest)
        save_jsonl(FOLDER / 'tail_excluded.jsonl', tail_excluded)
        save_jsonl(FOLDER / 'excluded.jsonl', excluded)
        save_jsonl(FOLDER / 'events.jsonl', [event for trial in selected for event in trial['events']])
        save_jsonl(FOLDER / 'first10_clips.jsonl', manifest[:10])
        save_jsonl(FOLDER / 'video_index.jsonl', [{key: value for key, value in trial.items() if key not in ['source_catalog', 'events', 'steps', 'state_rows', 'state_changes', 'components', 'errors', 'raw_errors', 'episodes']} for trial in trials])
        return manifest, summary
    selected = []
    for workflow in ['assemble', 'disassemble']:
        group = sorted([t for t in pool if t['workflow'] == workflow], key=selection_rank)
        missing = [t for t in group if not t['has_asr']][:CONFIG['without_asr_per_workflow']]
        if len(missing) < CONFIG['without_asr_per_workflow']:
            raise ValueError('v26_selection:insufficient_without_asr:' + workflow)
        chosen = list(missing)
        chosen.extend(t for t in group if t['video_id'] not in {s['video_id'] for s in missing})
        selected.extend(chosen[:CONFIG['videos_per_workflow']])
    if len(selected) != CONFIG['pilot_videos'] or len({t['participant'] for t in selected}) < 3:
        raise ValueError('v26_selection:pilot_quota')
    from impact_qa.clip_repair import repair_clips

    all_clips, raw_all_clips, repair_map, manifest = [], [], [], []
    for t in sorted(selected, key=selection_rank):
        raw_clips = boundaries(t)
        clips, repairs = repair_clips(t, raw_clips, CONFIG.get('clip_min_seconds'))
        raw_all_clips.extend(raw_clips)
        repair_map.extend(repairs)
        all_clips.extend(clips)
        qualified = [c for c in clips if any(e['action'] != 'null' and e['start_frame'] < c['end_frame_exclusive'] and e['end_frame_exclusive'] > c['start_frame'] for e in t['events'])]
        if CONFIG.get('selection_mode') == 'long_anomaly_first':
            with_error = sorted([c for c in qualified if clip_errors(t, c)], key=lambda c: (-max((e['duration_s'] for e in clip_errors(t, c)), default=0.0), -c['duration_s'], c['clip_id']))
        else:
            with_error = sorted([c for c in qualified if clip_errors(t, c)], key=lambda c: (len(clip_errors(t, c)), c['duration_s'], c['clip_id']))
        picked = with_error[:1]
        controls = sorted([c for c in qualified if c not in picked and normal_scope(t, c)], key=lambda c: (sum(e['start_frame'] < c['end_frame_exclusive'] and e['end_frame_exclusive'] > c['start_frame'] for e in t['raw_errors']), c['duration_s'], c['clip_id']))
        if controls:
            picked.extend(controls[:1])
        elif not picked and qualified:
            picked.append(min(qualified, key=lambda c: (c['duration_s'], c['clip_id'])))
        for c in picked[:CONFIG['clips_per_video']]:
            c['selection_reason'] = 'low_anomaly_target' if c in with_error[:1] else 'explicit_normal_operation_available'
            c['raw_error_overlap_count'] = sum(e['start_frame'] < c['end_frame_exclusive'] and e['end_frame_exclusive'] > c['start_frame'] for e in t['raw_errors'])
            manifest.append(c)
        save_json(FOLDER / 'trials' / (t['video_id'] + '.json'), t)
    order = []
    for workflow, has in [('assemble', True), ('assemble', False), ('disassemble', True), ('disassemble', False)]:
        c = next((c for c in manifest if c['workflow'] == workflow and c['has_asr'] == has), None)
        if c is None:
            raise ValueError('v26_selection:smoke_coverage')
        order.append(c)
    manifest = order + [c for c in manifest if c not in order]
    summary = {'version': CONFIG['version'], 'indexed_videos': len(trials), 'has_asr': sum(t['has_asr'] for t in trials), 'eligible_train_videos': len(pool), 'selected_videos': len(selected), 'selected_without_asr': sum(not t['has_asr'] for t in selected), 'participants': sorted({t['participant'] for t in selected}), 'selected_clips': len(manifest), 'all_clips': len(all_clips), 'raw_all_clips': len(raw_all_clips), 'clip_min_seconds': CONFIG.get('clip_min_seconds'), 'short_raw_clips': sum(clip['duration_s'] < CONFIG.get('clip_min_seconds', 0) for clip in raw_all_clips) if CONFIG.get('clip_min_seconds') else 0, 'clip_repairs': len(repair_map), 'merge_operations': sum(row.get('action') == 'merge_adjacent_short_clip' for row in repair_map), 'repaired_clip_count': sum(row.get('action') == 'repaired_clip' for row in repair_map), 'extended_clip_count': sum(row.get('action') == 'extend_short_window' for row in repair_map), 'dropped_short_clip_count': sum(row.get('action') == 'drop_unrepairable_short_clip' for row in repair_map), 'clip_repair_policy': CONFIG.get('clip_repair_policy'), 'short_errors_excluded': len(excluded), 'selected_trials': [{k: t[k] for k in ['video_id', 'workflow', 'has_asr', 'valid_error_episodes', 'valid_error_seconds', 'raw_error_count']} for t in selected]}
    save_json(FOLDER / 'selection_summary.json', summary)
    save_json(FOLDER / 'mcq_options.json', OPTIONS)
    save_jsonl(FOLDER / 'clips.jsonl', all_clips)
    save_jsonl(FOLDER / 'raw_clips.jsonl', raw_all_clips)
    save_jsonl(FOLDER / 'clip_repair_map.jsonl', repair_map)
    save_jsonl(FOLDER / 'manifest.jsonl', manifest)
    save_jsonl(FOLDER / 'excluded.jsonl', excluded)
    save_jsonl(FOLDER / 'events.jsonl', [e for t in selected for e in t['events']])
    save_jsonl(FOLDER / 'first10_clips.jsonl', manifest[:10])
    save_jsonl(FOLDER / 'video_index.jsonl', [{k: v for k, v in t.items() if k not in ['source_catalog', 'events', 'steps', 'state_rows', 'state_changes', 'components', 'errors', 'raw_errors', 'episodes']} for t in trials])
    return manifest, summary
