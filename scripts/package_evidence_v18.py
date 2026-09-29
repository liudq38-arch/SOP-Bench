import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl, save_json, save_jsonl


def main():
    folder = OUT / 'evidence_v18_batch'
    rows = read_jsonl(folder / 'results.jsonl')
    cases = {c['contract_id']: c for name in ['quality_v16_inputs', 'quality_v16_training_inputs'] for c in read_jsonl(OUT / name / 'contracts.jsonl')}
    drafts = []
    for r in rows:
        if 'generate' not in r['stages']:
            continue
        c, g = cases[r['contract_id']], r['stages']['generate']
        drafts.append({'contract_id': r['contract_id'], 'video_id': c['video_id'], 'kind': r['kind'], 'status': r['status'], 'open_question': g['open_question'], 'generated_answer': g['answer'], 'GT_answer': c['canonical_answer'], 'mcq_question': g['mcq_question'], 'options': c['options'], 'GT_correct_option': c['correct_option'], 'not_validated_dataset': True, 'formal_release': False, 'rejection_reasons': r.get('decision', {}).get('reasons', []), 'schema_error': r.get('error'), 'review_path': str(folder / 'runs' / (r['contract_id'] + '.json'))})
    save_jsonl(folder / 'generated_drafts.jsonl', drafts)
    selected = read_jsonl(folder / 'screened_candidates.jsonl')
    new_ids = {r['contract_id'] for r in selected}
    old_ids = {r['contract_id'] for r in read_jsonl(OUT / 'quality_v16_final/screened_candidates.jsonl')}
    summary = read_json(folder / 'initial_completed_summary.json')
    summary.update(generated_draft_events=len(drafts), generated_draft_kinds=dict(Counter(r['kind'] for r in drafts)), screened_tool_counts=dict(Counter(cases[r['contract_id']]['tool'] for r in selected)), screened_hand_counts=dict(Counter(cases[r['contract_id']]['hand'] for r in selected)), screened_trials=len({r['video_id'] for r in selected}), screened_participants=len({r['video_id'].split('_')[0] for r in selected}), option_position_counts=dict(Counter(r['correct_option'] for r in selected)), overlap_with_v16=len(new_ids & old_ids), newly_screened_vs_v16=len(new_ids - old_ids), v16_not_screened_by_v18=len(old_ids - new_ids), comparison_is_not_independent_accuracy=True)
    save_json(REPORTS / 'evidence_v18_final_summary.json', summary)
    save_json(folder / 'drafts_manifest.json', {'drafts': len(drafts), 'open_qa_drafts': len(drafts), 'mcq_qa_drafts': len(drafts), 'not_final_training_or_evaluation_data': True, 'formal_release': False})
    print(summary)


if __name__ == '__main__':
    main()
