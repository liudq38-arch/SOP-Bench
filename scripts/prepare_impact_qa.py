import concurrent.futures
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, FFPROBE, FFMPEG, MEDIA, OUT, REPORTS, TYPES, fingerprint, read_json, save_json, save_jsonl


def probe(path):
    cached = REPORTS / 'media' / (path.stem + '.json')
    if cached.exists():
        return read_json(cached)
    result = subprocess.run([FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-show_streams', '-show_format', '-show_entries', 'packet=pts_time', '-show_packets', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    stream = data['streams'][0]
    pts = sorted(float(p['pts_time']) for p in data['packets'] if 'pts_time' in p)
    ann = read_json(ANNOTATIONS / 'TAS-B/ego' / (path.stem + '.json'))
    for position in [0, max(0, float(data['format']['duration']) - 1)]:
        subprocess.run([FFMPEG, '-v', 'error', '-threads', '1', '-ss', str(position), '-i', str(path), '-frames:v', '1', '-f', 'null', '-'], capture_output=True, check=True)
    row = {'video_id': path.stem, 'path': str(path), 'bytes': path.stat().st_size, 'duration_s': float(data['format']['duration']), 'width': stream['width'], 'height': stream['height'], 'codec': stream['codec_name'], 'avg_frame_rate': stream['avg_frame_rate'], 'reported_frames': int(stream.get('nb_frames', 0)), 'annotation_frames': ann['meta_data']['num_frames'], 'packet_pts_s': pts, 'pts_basis': 'sorted presentation timestamps of video packets; one-packet-per-frame checked against stream nb_frames', 'first_last_decode': 'ok'}
    row['count_matches'] = len(pts) == row['reported_frames'] == row['annotation_frames']
    save_json(cached, row)
    return row


def events_for_video(video):
    vid = video['video_id']
    data = read_json(ANNOTATIONS / 'TAS-B/ego' / (vid + '.json'))
    coarse = read_json(ANNOTATIONS / 'TAS-S/ego' / (vid + '.json'))
    actions = {v['id']: v['name'] for v in data['action_labels']}
    verbs = {v['id']: v['name'] for v in data['verbs']}
    nouns = {v['id']: v['name'] for v in data['nouns']}
    pts = video['packet_pts_s']
    rows, excluded = [], []
    for index, s in enumerate(data['segments']):
        event_id = f'{vid}__{s["entity"]}__{index:04d}'
        reason = None
        if s['action_label'] == 0:
            reason = 'null_action'
        elif not video['count_matches']:
            reason = 'frame_count_mismatch'
        elif not 0 <= s['start_frame'] <= s['end_frame'] < len(pts):
            reason = 'invalid_boundary'
        elif s['phase'] == 'anomaly' and not any(s['anomaly_type']):
            reason = 'anomaly_missing_type'
        if reason:
            excluded.append({'event_id': event_id, 'reason': reason})
            continue
        start = pts[s['start_frame']]
        end = pts[s['end_frame'] + 1] if s['end_frame'] + 1 < len(pts) else video['duration_s']
        if not .5 <= end - start <= 35:
            excluded.append({'event_id': event_id, 'reason': 'pilot_duration_outside_0.5_35s'})
            continue
        overlaps = [c for c in coarse['segments'] if min(c['f_end'], s['end_frame']) >= max(c['f_start'], s['start_frame'])]
        same_hand = [(i, x) for i, x in enumerate(data['segments']) if x['entity'] == s['entity'] and x['action_label'] != 0]
        ordered = sorted(same_hand, key=lambda pair: (pair[1]['start_frame'], pair[0]))
        position = next(j for j, pair in enumerate(ordered) if pair[0] == index)
        neighbors = [dict(x, action_name=actions[x['action_label']]) for _, x in ordered[max(0, position - 2):position + 3]]
        row = {'event_id': event_id, 'video_id': vid, 'execution_id': vid.removesuffix('_ego'), 'hand': s['entity'], 'action': actions[s['action_label']], 'verb': verbs.get(s['verb']), 'object': nouns.get(s['noun']), 'phase': s['phase'], 'anomaly_types': [name for name, bit in zip(TYPES, s['anomaly_type']) if bit], 'raw_anomaly_vector': s['anomaly_type'], 'start_frame': s['start_frame'], 'end_frame_inclusive': s['end_frame'], 'start_s': start, 'end_s_exclusive': end, 'annotation_duration_s': end - start, 'context_start_s': max(pts[0], start - 3), 'context_end_s': min(video['duration_s'], end + 3), 'coarse_steps': overlaps, 'neighbor_actions': neighbors, 'annotation_ref': f'{ANNOTATIONS}/TAS-B/ego/{vid}.json#/segments/{index}', 'video_path': video['path'], 'video_size': video['bytes'], 'time_basis': 'packet PTS; inclusive annotation endpoints mapped to next frame PTS', 'review_status': 'pending_human_review'}
        rows.append(row)
    return rows, excluded


def select(rows, counts, rng, used_videos):
    selected = []
    pool = rows.copy()
    rng.shuffle(pool)
    type_counts = Counter()
    for phase, count in counts.items():
        candidates = [x for x in pool if x['phase'] == phase and x['video_id'] not in used_videos]
        for _ in range(count):
            if not candidates:
                raise RuntimeError(f'selection: insufficient unique videos for {phase}')
            if phase == 'anomaly':
                candidates.sort(key=lambda x: (sum(1 / (1 + type_counts[t]) for t in x['anomaly_types']), -sum(s['hand'] == x['hand'] for s in selected)), reverse=True)
            item = candidates.pop(0)
            selected.append(item)
            used_videos.add(item['video_id'])
            type_counts.update(item['anomaly_types'])
            candidates = [x for x in candidates if x['video_id'] != item['video_id']]
    return selected


def main():
    files = sorted(MEDIA.glob('*.mp4'))
    if len(files) != 112:
        raise RuntimeError(f'media_preflight: expected 112 ego videos, got {len(files)}')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        videos = list(pool.map(probe, files))
    candidates, excluded = [], []
    for video in videos:
        a, b = events_for_video(video)
        candidates.extend(a)
        excluded.extend(b)
    rng = random.Random(20260918)
    used = set()
    dev = select(candidates, {'recovery': 5, 'anomaly': 10, 'normal': 5}, rng, used)
    pilot = select(candidates, {'recovery': 15, 'anomaly': 30, 'normal': 15}, rng, used)
    for name, rows in [('development', dev), ('pilot', pilot)]:
        for row in rows:
            row['split'] = name
            row['record_hash'] = fingerprint(row)
        save_jsonl(OUT / f'{name}_events.jsonl', rows)
    save_jsonl(OUT / 'candidate_events.jsonl', candidates)
    save_jsonl(OUT / 'excluded_events.jsonl', excluded)
    save_json(REPORTS / 'events_first10.json', dev[:10])
    summary = {'videos': len(videos), 'frame_count_mismatches': [v['video_id'] for v in videos if not v['count_matches']], 'candidate_events': len(candidates), 'excluded_reasons': dict(Counter(r['reason'] for r in excluded)), 'seed': 20260918, 'development': {'events': len(dev), 'phases': dict(Counter(r['phase'] for r in dev)), 'types': dict(Counter(t for r in dev for t in r['anomaly_types']))}, 'pilot': {'events': len(pilot), 'phases': dict(Counter(r['phase'] for r in pilot)), 'types': dict(Counter(t for r in pilot for t in r['anomaly_types']))}, 'execution_overlap': sorted(set(x['execution_id'] for x in dev) & set(x['execution_id'] for x in pilot)), 'unique_selected_videos': len(used)}
    save_json(REPORTS / 'precheck.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
