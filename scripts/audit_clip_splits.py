import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def stats(rows, minimum):
    durations = sorted(row['duration_s'] for row in rows)
    bins = Counter()
    for value in durations:
        if value < 1.5:
            label = '0-1.5'
        elif value < 3:
            label = '1.5-3'
        elif value < 5:
            label = '3-5'
        elif value < 10:
            label = '5-10'
        elif value < 20:
            label = '10-20'
        elif value < 30:
            label = '20-30'
        elif value < 60:
            label = '30-60'
        else:
            label = '>=60'
        bins[label] += 1
    return {
        'count': len(rows),
        'min_s': durations[0] if durations else None,
        'max_s': durations[-1] if durations else None,
        'mean_s': sum(durations) / len(durations) if durations else None,
        'median_s': durations[len(durations) // 2] if durations else None,
        'below_minimum': sum(value < minimum for value in durations),
        'threshold_counts': {str(threshold): sum(value < threshold for value in durations) for threshold in [1, 1.5, 2, 3, 5, 10, 15, 30, 60]},
        'bins': dict(bins),
        'workflow': dict(Counter(row['workflow'] for row in rows)),
    }


def coverage(rows, trials, field):
    by_video = defaultdict(list)
    for row in rows:
        by_video[row['video_id']].append(row)
    total = covered = partial = 0
    for video_id, trial in trials.items():
        for event in trial[field]:
            if field == 'events' and event['action'] == 'null':
                continue
            total += 1
            complete = any(row['start_frame'] <= event['start_frame'] and event['end_frame_exclusive'] <= row['end_frame_exclusive'] for row in by_video.get(video_id, []))
            if complete:
                covered += 1
            elif any(row['start_frame'] < event['end_frame_exclusive'] and event['start_frame'] < row['end_frame_exclusive'] for row in by_video.get(video_id, [])):
                partial += 1
    return {'total': total, 'fully_contained': covered, 'partial_only': partial, 'not_overlapped': total - covered - partial}


def run(config_path):
    config = json.loads(Path(config_path).read_text())
    folder = ROOT / config['output_root']
    minimum = float(config.get('clip_min_seconds', 0))
    raw = [json.loads(line) for line in (folder / 'raw_clips.jsonl').read_text().splitlines() if line.strip()]
    repaired = [json.loads(line) for line in (folder / 'clips.jsonl').read_text().splitlines() if line.strip()]
    manifest = [json.loads(line) for line in (folder / 'manifest.jsonl').read_text().splitlines() if line.strip()]
    tail_path = folder / 'tail_excluded.jsonl'
    tail_excluded = [json.loads(line) for line in tail_path.read_text().splitlines() if line.strip()] if tail_path.exists() else []
    trials = {}
    for path in (folder / 'trials').glob('*.json'):
        trials[path.stem] = json.loads(path.read_text())
    raw_manifest = [
        clip for clip in raw
        if any(
            event['action'] != 'null'
            and event['start_frame'] < clip['end_frame_exclusive']
            and event['end_frame_exclusive'] > clip['start_frame']
            for event in trials[clip['video_id']]['events']
        )
    ]
    by_video = defaultdict(list)
    for row in repaired:
        by_video[row['video_id']].append(row)
    partition_checks = []
    for video_id, rows in by_video.items():
        trial = trials[video_id]
        ordered = sorted(rows, key=lambda row: row['start_frame'])
        if trial['workflow'] == 'assemble':
            valid = bool(ordered) and ordered[0]['start_frame'] == 0 and ordered[-1]['end_frame_exclusive'] == trial['frame_count'] and all(a['end_frame_exclusive'] == b['start_frame'] for a, b in zip(ordered, ordered[1:]))
        else:
            valid = bool(ordered)
        partition_checks.append({'video_id': video_id, 'workflow': trial['workflow'], 'valid': valid, 'count': len(ordered)})
    report = {
        'version': config['version'],
        'config_path': str(Path(config_path).relative_to(ROOT)),
        'minimum_clip_seconds': minimum,
        'raw': stats(raw, minimum),
        'repaired': stats(repaired, minimum),
        'manifest': stats(manifest, minimum),
        'raw_clip_count': len(raw),
        'raw_manifest_clip_count': len(raw_manifest),
        'repaired_clip_count': len(repaired),
        'manifest_clip_count': len(manifest),
        'source_end_cleanup_tail_count': len(tail_excluded),
        'source_end_cleanup_tail_ids': [row['clip_id'] for row in tail_excluded],
        'repair_actions': dict(Counter(row.get('action', 'unknown') for row in (json.loads(line) for line in (folder / 'clip_repair_map.jsonl').read_text().splitlines() if line.strip()))),
        'partition_checks': {'videos': len(partition_checks), 'invalid': [row for row in partition_checks if not row['valid']]},
        'event_coverage_raw_manifest': coverage(raw_manifest, trials, 'events'),
        'event_coverage_repaired_manifest': coverage(manifest, trials, 'events'),
        'error_coverage_raw_manifest': coverage(raw_manifest, trials, 'raw_errors'),
        'error_coverage_repaired_manifest': coverage(manifest, trials, 'raw_errors'),
        'all_repaired_meet_minimum': all(row['duration_s'] >= minimum for row in repaired),
        'all_manifest_meet_minimum': all(row['duration_s'] >= minimum for row in manifest),
    }
    (folder / 'clip_split_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = [
        f"# Clip split audit: {config['version']}",
        '',
        f"Minimum duration: **{minimum:.1f}s**. Raw clips: **{len(raw)}**; repaired clips: **{len(repaired)}**; manifest clips: **{len(manifest)}**.",
        '',
        '| set | count | min (s) | median (s) | mean (s) | < minimum |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for name, value in [('raw', report['raw']), ('repaired', report['repaired']), ('manifest', report['manifest'])]:
        lines.append(f"| {name} | {value['count']} | {value['min_s']:.3f} | {value['median_s']:.3f} | {value['mean_s']:.3f} | {value['below_minimum']} |")
    lines.extend([
        '',
        f"All repaired clips meet minimum: **{report['all_repaired_meet_minimum']}**; all manifest clips meet minimum: **{report['all_manifest_meet_minimum']}**.",
        f"Source-end cleanup tails excluded from manifest: **{len(tail_excluded)}**.",
        f"Assembly partition checks invalid: **{len(report['partition_checks']['invalid'])}**.",
        '',
        '## Thresholds for repaired manifest',
        '',
        '```json',
        json.dumps(report['manifest']['threshold_counts'], ensure_ascii=False, indent=2),
        '```',
        '',
        '## Coverage',
        '',
        '```json',
        json.dumps({key: report[key] for key in ['event_coverage_raw_manifest', 'event_coverage_repaired_manifest', 'error_coverage_raw_manifest', 'error_coverage_repaired_manifest']}, ensure_ascii=False, indent=2),
        '```',
    ])
    (folder / 'clip_split_audit.md').write_text('\n'.join(lines) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    print(json.dumps(run(ROOT / args.config), ensure_ascii=False, indent=2))
