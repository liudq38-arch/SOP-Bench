import concurrent.futures
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_jsonl, save_json
from impact_qa.media import create_review_clip, prepare_evidence


def process(event):
    evidence = prepare_evidence(event)
    clip = create_review_clip(event)
    print(event['event_id'], len(evidence['images']), flush=True)
    return {'event_id': event['event_id'], 'frames': len(evidence['images']), 'clip': str(clip)}


def main():
    rows = read_jsonl(OUT / 'development_events.jsonl') + read_jsonl(OUT / 'pilot_events.jsonl')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(process, rows))
    save_json(REPORTS / 'evidence_precheck.json', {'events': len(results), 'total_frames': sum(r['frames'] for r in results), 'first10': results[:10]})


if __name__ == '__main__':
    main()
