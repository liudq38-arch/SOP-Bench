import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, read_jsonl, save_json


def main():
    rows = read_jsonl(OUT / 'development_events.jsonl') + read_jsonl(OUT / 'pilot_events.jsonl')
    atr = {}
    for hand, code in [('left', 'L'), ('right', 'R')]:
        path = ANNOTATIONS / f'ATR/atr_segments_{code}/test.split4.jsonl'
        for r in read_jsonl(path):
            atr.setdefault((r['video_id'], hand), []).append(r)
    results = []
    for e in rows:
        code = 'L' if e['hand'] == 'left' else 'R'
        path = ANNOTATIONS / f'PPR/groundTruth_PPR_{code}/{e["video_id"]}.txt'
        labels = path.read_text().splitlines()
        counts = Counter(labels[e['start_frame']:e['end_frame_inclusive'] + 1])
        matches = [r for r in atr.get((e['video_id'], e['hand']), []) if r['start_frame'] <= e['start_frame'] and r['end_frame'] >= e['end_frame_inclusive']]
        results.append({'event_id': e['event_id'], 'phase': e['phase'], 'ppr_values': dict(counts), 'ppr_consistent': set(counts) == {e['phase'].upper()}, 'atr_covering_segments': matches, 'atr_vector_matches': any(r['labels'] == e['raw_anomaly_vector'] for r in matches) if e['phase'] == 'anomaly' else None, 'coarse_anomaly_values': [x['has_anomaly'] for x in e['coarse_steps']], 'coarse_fine_disagreement': e['phase'] == 'anomaly' and not any(x['has_anomaly'] for x in e['coarse_steps']), 'asr_psr_policy': 'front labels not temporally transferred without verified synchronization'})
    save_json(REPORTS / 'annotation_crosscheck.json', {'events': results, 'ppr_inconsistent': sum(not r['ppr_consistent'] for r in results), 'atr_anomaly_mismatch': sum(r['atr_vector_matches'] is False for r in results), 'coarse_fine_disagreement': sum(r['coarse_fine_disagreement'] for r in results), 'note': 'PPR/ATR are derived from TAS-B, not independent truth; coarse and fine annotations need not have identical scopes.'})
    print(json.dumps({k: v for k, v in json.loads((REPORTS / 'annotation_crosscheck.json').read_text()).items() if k != 'events'}, indent=2))


if __name__ == '__main__':
    main()
