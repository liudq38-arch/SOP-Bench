import json
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.descriptive_v21 import FOLDER


def main():
    summaries = []
    qa_rows = []
    media = {c['clip_id']: c for r in read_jsonl(FOLDER / 'cases.jsonl') for c in r['clips']}
    examples = [q['answer'].lower().split() for e in read_json(ROOT / 'prompts/impact_qa/v21/few_shots.json')['examples'] for q in e['open_qa_bundle']['items']]
    for path in sorted((FOLDER / 'runs').glob('*/result.json')):
        case = read_json(path)
        for clip in case['clips']:
            observation = clip.get('observation', {})
            events = {e['event_id']: e for e in observation.get('events', [])}
            scoped = []
            for section in clip.get('description', {}).get('sections', []):
                scoped.extend(('description:' + section['section_id'], c) for c in section['claims'])
            for qa in clip.get('qa', {}).get('items', []):
                scoped.extend(('qa:' + qa['qa_id'], c) for c in qa['claims'])
                qa_rows.append(dict(qa, case_id=case['case_id'], view=case['view'], clip_id=clip['clip_id'], status='draft_requires_review'))
            ids = Counter(c['claim_id'] for _, c in scoped)
            checks = clip.get('audit', {}).get('claim_checks', [])
            audited = {c['claim_id'] for c in checks}
            issues = []
            core = media[clip['clip_id']]['core_frames']
            low, high = core[0]['source_pts_s'], core[-1]['source_pts_s']
            for qa in clip.get('qa', {}).get('items', []):
                a, b = qa['scope_interval_s']
                if a < low - 0.001 or b > high + 0.001:
                    issues.append({'scope': qa['qa_id'], 'issue': 'qa_scope_exceeds_core_clip', 'interval': [a, b], 'core': [low, high]})
                words = qa['answer'].lower().split()
                overlap = max((SequenceMatcher(None, words, example, autojunk=False).find_longest_match().size for example in examples), default=0)
                if overlap >= 16:
                    issues.append({'scope': qa['qa_id'], 'issue': 'synthetic_example_answer_overlap_requires_review', 'consecutive_words': overlap})
            for section in clip.get('description', {}).get('sections', []):
                a, b = section['source_interval_s']
                if section['scope'] == 'target' and (a < low - 0.001 or b > high + 0.001):
                    issues.append({'scope': section['section_id'], 'issue': 'description_target_exceeds_core_clip', 'interval': [a, b], 'core': [low, high]})
            for scope, claim in scoped:
                if not claim['frame_ids'] and not claim['event_ids']:
                    issues.append({'scope': scope, 'claim_id': claim['claim_id'], 'issue': 'no_evidence'})
                invalid = set(claim['event_ids']) - events.keys()
                if invalid:
                    issues.append({'scope': scope, 'claim_id': claim['claim_id'], 'issue': 'unknown_event_ids', 'ids': sorted(invalid)})
                if claim['claim_id'] not in audited:
                    issues.append({'scope': scope, 'claim_id': claim['claim_id'], 'issue': 'not_listed_by_auditor'})
            for key, count in ids.items():
                if count > 1:
                    issues.append({'claim_id': key, 'issue': 'ambiguous_claim_id_across_outputs', 'count': count})
            summaries.append({'case_id': case['case_id'], 'view': case['view'], 'clip_id': clip['clip_id'], 'pipeline_status': clip['status'], 'pipeline_error': clip.get('error'), 'native_pilot_frames': case['native_frames'], 'valid_frame_cards': case['valid_frame_cards'], 'original_target_frames': case['original_target_frames'], 'qa_count': len(clip.get('qa', {}).get('items', [])), 'description_words': sum(len(s['text'].split()) for s in clip.get('description', {}).get('sections', [])), 'qa_answer_words': [len(q['answer'].split()) for q in clip.get('qa', {}).get('items', [])], 'audit_verdict_counts': dict(Counter(c['verdict'] for c in checks)), 'audit_omissions': clip.get('audit', {}).get('omissions', []), 'model_item_decisions': clip.get('audit', {}).get('item_decisions', []), 'postcheck_issues': issues, 'formal_release': False})
    save_json(FOLDER / 'postcheck.json', {'clips': summaries, 'claim_audit_not_accuracy': True, 'human_review_count_not_measured_here': True})
    save_jsonl(FOLDER / 'open_qa_drafts.jsonl', qa_rows)
    save_jsonl(FOLDER / 'first10_open_qa.jsonl', qa_rows[:10])
    print(json.dumps({'clips': len(summaries), 'open_qa': len(qa_rows), 'postcheck_issues': sum(len(s['postcheck_issues']) for s in summaries), 'descriptions_words': [s['description_words'] for s in summaries], 'audit_verdict_counts': dict(sum((Counter(s['audit_verdict_counts']) for s in summaries), Counter()))}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
