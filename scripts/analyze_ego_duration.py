import json
import math
from pathlib import Path


def quantile(values, fraction):
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def main():
    root = Path(__file__).resolve().parents[1]
    results = {}
    for path in sorted((root / 'annotations/egoerrorvqa').glob('*.json')):
        rows = json.loads(path.read_text())
        if not isinstance(rows, list):
            continue
        valid = [r for r in rows if isinstance(r.get('start_time'), (int, float)) and isinstance(r.get('end_time'), (int, float)) and math.isfinite(r['start_time']) and math.isfinite(r['end_time']) and r['start_time'] >= 0 and r['end_time'] > r['start_time']]
        durations = sorted(r['end_time'] - r['start_time'] for r in valid)
        fields = sorted(set().union(*(r.keys() for r in rows)))
        results[path.name] = {'rows': len(rows), 'valid_intervals': len(valid), 'invalid_intervals': len(rows) - len(valid), 'duration_seconds': {str(q): round(quantile(durations, q), 3) for q in [0, .25, .5, .75, .9, .95, .99, 1]}, 'non_null_fields': {f: sum(r.get(f) is not None for r in rows) for f in fields}, 'first10_intervals': [{'video_id': r.get('video_id'), 'start': r['start_time'], 'end': r['end_time']} for r in valid[:10]]}
    target = root / 'reports/design/ego_duration_stats.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    for name, value in results.items():
        print(name, json.dumps({k: v for k, v in value.items() if k not in ['non_null_fields', 'first10_intervals']}))


if __name__ == '__main__':
    main()
