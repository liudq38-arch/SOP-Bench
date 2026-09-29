import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl, save_json, save_jsonl


def main():
    folder = OUT / 'quality_v16_final'
    evidence = {r['contract_id']: r for r in read_jsonl(OUT / 'quality_v16_evidence/results.jsonl')}
    candidates = [r for batch in ['quality_v16_batch001', 'quality_v16_batch002'] for r in read_jsonl(OUT / batch / 'model_passed_candidates.jsonl')]
    screened = [{**r, 'additional_evidence_review': evidence[r['contract_id']], 'status': 'evidence_screened_unvalidated'} for r in candidates if evidence[r['contract_id']]['status'] == 'evidence_screened_unvalidated']
    retained = {r['contract_id'] for r in screened}
    public = [r for batch in ['quality_v16_batch001', 'quality_v16_batch002'] for r in read_jsonl(OUT / batch / 'evaluation_inputs.jsonl') if r['id'].split(':')[0] in retained]
    for row in public:
        allowed = {'id', 'video_id', 'kind', 'format', 'question', 'images', 'options'}
        if set(row) - allowed:
            raise ValueError('package_v16:public_metadata_leak')
    save_jsonl(folder / 'screened_candidates.jsonl', screened)
    save_jsonl(folder / 'evaluation_inputs.jsonl', public)
    save_jsonl(folder / 'pending_or_rejected_evidence.jsonl', [r for r in evidence.values() if r['status'] != 'evidence_screened_unvalidated'])
    summary = {'generation_events': 230, 'primary_model_passed': len(candidates), 'additional_evidence_counts': dict(Counter(r['status'] for r in evidence.values())), 'screened_events': len(screened), 'open_qa': len(screened), 'mcq_qa': len(screened), 'formal_release': False, 'independent_acceptance': False, 'tool_only': True, 'warning': 'Model-screened candidates, not human gold. Additional pair check was designed after inspecting batch001. v17 richer-input results remain a separate experiment.'}
    save_json(folder / 'summary.json', summary)
    save_json(REPORTS / 'quality_v16_final_summary.json', summary)
    print(summary)


if __name__ == '__main__':
    main()
