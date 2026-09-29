import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.history_v23 import history_input


FOLDER = ROOT / 'outputs/impact_qa/history_v23'


def main():
    results = read_json(FOLDER / 'results.json')
    records = {r['case']['case_id']: r for r in read_jsonl(ROOT / 'outputs/impact_qa/descriptive_v21/cases.jsonl')}
    stats, outputs = [], []
    for result in results:
        cid = result['case_id']
        ledger = result['ledger']
        for i, row in enumerate(ledger):
            if row['history_before_hash'] != fingerprint(history_input(ledger[:i])):
                raise ValueError('history_review:history_mismatch')
            call = read_json(FOLDER / 'api_cache' / (row['cache_key'] + '.json'))
            payload = json.loads(call['request']['messages'][1]['content'][0]['text'])
            if 'atr_ground_truth' in payload or 'wrong_tool' in json.dumps(payload):
                raise ValueError('history_review:gt_answer_in_local_observation')
            previous = {e['event_id'] for old in ledger[max(0, i - 2):i] for e in old['events']}
            if any(e['continues_event_id'] != 'none' and e['continues_event_id'] not in previous for e in row['events']):
                raise ValueError('history_review:future_or_missing_continuation')
        ids = {e['event_id'] for row in ledger for e in row['events']}
        covered = {e for section in result['integration']['sections'] for e in section['event_ids']}
        if ids != covered:
            raise ValueError('history_review:missing_integration_events')
        revised = read_json(FOLDER / 'qa_visual_revision' / (cid + '.json'))
        valid, held = [], []
        for q in revised['qa']['items']:
            if not set(q['event_ids']).issubset(ids):
                raise ValueError('history_review:qa_unknown_events')
            reasons = []
            if q['kind'] == 'event_occurrence' and re.match(r'^\s*No\b', q['answer'], re.I):
                reasons.append('negative_occurrence_requires_independent_absence_verification')
            if re.search(r'\b(uninterrupted|without pause|without interruption|clockwise)\b', q['answer'], re.I):
                warnings = ['Review direction or absolute continuity wording against the video; a valid citation does not certify this detail.']
            else:
                warnings = []
            item = dict(q, case_id=cid, status='held' if reasons else 'pending_human', reasons=reasons, warnings=warnings, formal_release=False)
            (held if reasons else valid).append(item)
            outputs.append(item)
        save_json(FOLDER / 'review_ready' / (cid + '.json'), {'case_id': cid, 'qa': {'items': valid}, 'held_items': held, 'formal_release': False})
        stats.append({'case_id': cid, 'clips': len(ledger), 'native_interval_frames': len(records[cid]['frames']), 'unique_clip_descriptions': len({r['description'] for r in ledger}), 'events': len(ids), 'integration_event_id_coverage': 1.0, 'continuation_links': sum(e['continues_event_id'] != 'none' for r in ledger for e in r['events']), 'pending_qa': len(valid), 'held_qa': len(held), 'history_and_gt_separation_checks': True})
    mcq = read_jsonl(FOLDER / 'fixed_mcq.jsonl')
    old = {r['qa_id']: r for r in read_jsonl(ROOT / 'outputs/impact_qa/descriptive_v21/fixed_mcq.jsonl')}
    if any(r != old[r['qa_id']] for r in mcq):
        raise ValueError('history_review:fixed_mcq_changed')
    calls = [read_json(f) for folder in [FOLDER / 'api_cache', FOLDER / 'qa_visual_revision/api_cache'] for f in folder.glob('*.json')]
    summary = {'cases': stats, 'requests': len(calls), 'input_tokens': sum(r['usage']['prompt_tokens'] for r in calls), 'output_tokens': sum(r['usage']['completion_tokens'] for r in calls), 'max_prompt_tokens': max(r['usage']['prompt_tokens'] for r in calls), 'final_open_qa_drafts': len(outputs), 'pending_human_qa': sum(r['status'] == 'pending_human' for r in outputs), 'held_negative_occurrence': sum(r['status'] == 'held' for r in outputs), 'fixed_mcq': len(mcq), 'full_source_video_processed': False, 'formal_release': False, 'human_validated_v23': 0}
    save_json(FOLDER / 'final_summary.json', summary)
    save_jsonl(FOLDER / 'first10_outputs.jsonl', outputs[:10])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
