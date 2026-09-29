import math
from copy import deepcopy


def _duration(start, stop, fps):
    return (stop - start) / fps


def _merge_boundary(end_group, raw_ids, direction, minimum_seconds, fps):
    boundary = deepcopy(end_group['boundary'])
    raw_boundaries = [clip['boundary'] for clip in end_group['raw_clips']]
    boundary['components'] = sorted({component for item in raw_boundaries for component in item.get('components', [])})
    boundary['source_ids'] = sorted({source for item in raw_boundaries for source in item.get('source_ids', [])})
    boundary['raw_boundary_reasons'] = sorted({item.get('reason') for item in raw_boundaries if item.get('reason')})
    boundary['raw_anchor_frames'] = sorted({item['anchor_frame'] for item in raw_boundaries if 'anchor_frame' in item})
    boundary['repair_action'] = 'merge_adjacent_short_clip'
    boundary['repair_direction'] = direction
    boundary['minimum_clip_seconds'] = minimum_seconds
    boundary['raw_clip_ids'] = list(raw_ids)
    boundary['repaired_duration_s'] = _duration(end_group['start'], end_group['stop'], fps)
    return boundary


def _assembly_repair(trial, raw_clips, minimum_seconds):
    if not raw_clips:
        return [], []
    fps = raw_clips[0]['fps']
    groups = [
        {
            'start': clip['start_frame'],
            'stop': clip['end_frame_exclusive'],
            'boundary': deepcopy(clip['boundary']),
            'raw_clips': [clip],
        }
        for clip in sorted(raw_clips, key=lambda item: item['start_frame'])
    ]
    repairs = []
    while True:
        index = next(
            (i for i, group in enumerate(groups) if _duration(group['start'], group['stop'], fps) < minimum_seconds),
            None,
        )
        if index is None:
            break
        if len(groups) == 1:
            group = groups.pop(index)
            repairs.append({
                'video_id': trial['video_id'],
                'workflow': trial['workflow'],
                'action': 'drop_unrepairable_short_clip',
                'raw_clip_ids': [clip['clip_id'] for clip in group['raw_clips']],
                'raw_intervals': [[clip['start_frame'], clip['end_frame_exclusive']] for clip in group['raw_clips']],
                'raw_duration_s': _duration(group['start'], group['stop'], fps),
                'minimum_clip_seconds': minimum_seconds,
            })
            continue
        if index == 0:
            neighbor = 1
            direction = 'into_next'
        elif index == len(groups) - 1:
            neighbor = index - 1
            direction = 'into_previous'
        else:
            previous_duration = groups[index - 1]['stop'] - groups[index - 1]['start']
            next_duration = groups[index + 1]['stop'] - groups[index + 1]['start']
            neighbor = index - 1 if previous_duration >= next_duration else index + 1
            direction = 'into_previous' if neighbor == index - 1 else 'into_next'
        left, right = sorted((index, neighbor))
        merged_raw = groups[left]['raw_clips'] + groups[right]['raw_clips']
        merged = {
            'start': groups[left]['start'],
            'stop': groups[right]['stop'],
            'boundary': groups[right]['boundary'],
            'raw_clips': merged_raw,
        }
        raw_ids = [clip['clip_id'] for clip in merged_raw]
        repairs.append({
            'video_id': trial['video_id'],
            'workflow': trial['workflow'],
            'action': 'merge_adjacent_short_clip',
            'direction': direction,
            'raw_clip_ids': raw_ids,
            'raw_intervals': [[clip['start_frame'], clip['end_frame_exclusive']] for clip in merged_raw],
            'raw_duration_s': sum(clip['duration_s'] for clip in merged_raw),
            'repaired_interval': [merged['start'], merged['stop']],
            'repaired_duration_s': _duration(merged['start'], merged['stop'], fps),
            'minimum_clip_seconds': minimum_seconds,
        })
        groups[left:right + 1] = [merged]

    repaired = []
    for ordinal, group in enumerate(groups):
        raw_ids = [clip['clip_id'] for clip in group['raw_clips']]
        changed = len(raw_ids) > 1 or group['start'] != group['raw_clips'][0]['start_frame'] or group['stop'] != group['raw_clips'][-1]['end_frame_exclusive']
        boundary = deepcopy(group['boundary'])
        if changed:
            boundary = _merge_boundary(group, raw_ids, 'merged', minimum_seconds, fps)
        clip = _rebuild_clip(trial, group['start'], group['stop'], boundary, ordinal)
        repaired.append(clip)
        if changed:
            repairs.append({
                'video_id': trial['video_id'],
                'workflow': trial['workflow'],
                'action': 'repaired_clip',
                'repaired_clip_id': clip['clip_id'],
                'raw_clip_ids': raw_ids,
                'repaired_interval': [group['start'], group['stop']],
                'repaired_duration_s': clip['duration_s'],
                'minimum_clip_seconds': minimum_seconds,
            })
    return repaired, repairs


def _expand_to_minimum(trial, clip, minimum_seconds):
    minimum_frames = max(1, math.ceil(minimum_seconds * clip['fps']))
    start, stop, count = clip['start_frame'], clip['end_frame_exclusive'], clip['end_frame_exclusive'] - clip['start_frame']
    if count >= minimum_frames:
        return clip, None
    target = min(trial['frame_count'], max(minimum_frames, count))
    left_room, right_room = start, trial['frame_count'] - stop
    needed = target - count
    take_left = min(left_room, (needed + 1) // 2)
    start -= take_left
    needed -= take_left
    take_right = min(right_room, needed)
    stop += take_right
    needed -= take_right
    if needed:
        take_left = min(start, needed)
        start -= take_left
        needed -= take_left
    if needed:
        return None, {
            'video_id': trial['video_id'],
            'workflow': trial['workflow'],
            'action': 'drop_unrepairable_short_clip',
            'raw_clip_ids': [clip['clip_id']],
            'raw_intervals': [[clip['start_frame'], clip['end_frame_exclusive']]],
            'raw_duration_s': clip['duration_s'],
            'minimum_clip_seconds': minimum_seconds,
        }
    boundary = deepcopy(clip['boundary'])
    boundary['repair_action'] = 'extend_short_window'
    boundary['minimum_clip_seconds'] = minimum_seconds
    boundary['raw_clip_ids'] = [clip['clip_id']]
    boundary['repaired_interval'] = [start, stop]
    repaired = _rebuild_clip(trial, start, stop, boundary, 0)
    return repaired, {
        'video_id': trial['video_id'],
        'workflow': trial['workflow'],
        'action': 'extend_short_window',
        'raw_clip_ids': [clip['clip_id']],
        'raw_intervals': [[clip['start_frame'], clip['end_frame_exclusive']]],
        'raw_duration_s': clip['duration_s'],
        'repaired_interval': [start, stop],
        'repaired_duration_s': repaired['duration_s'],
        'minimum_clip_seconds': minimum_seconds,
    }


def _rebuild_clip(trial, start, stop, boundary, ordinal):
    from impact_qa.v26_data import clip_record

    return clip_record(trial, start, stop, boundary, ordinal)


def repair_clips(trial, raw_clips, minimum_seconds):
    if not minimum_seconds or minimum_seconds <= 0:
        return raw_clips, []
    if trial['workflow'] == 'assemble':
        return _assembly_repair(trial, raw_clips, minimum_seconds)
    repaired, repairs = [], []
    for ordinal, clip in enumerate(raw_clips):
        value, repair = _expand_to_minimum(trial, clip, minimum_seconds)
        if value is not None:
            value['boundary']['repair_ordinal'] = ordinal
            repaired.append(value)
        if repair is not None:
            repairs.append(repair)
    for ordinal, clip in enumerate(repaired):
        clip['boundary']['repair_ordinal'] = ordinal
    return repaired, repairs
