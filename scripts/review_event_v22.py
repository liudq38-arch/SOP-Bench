import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import ROOT, read_json, save_json, save_jsonl
from impact_qa.descriptive_v21 import digest


FOLDER = ROOT / 'outputs/impact_qa/event_v22'


def main():
    calls = [read_json(p) for p in (FOLDER / 'api_cache').glob('*.json')]
    by_key = {r['cache_key']: r for r in calls}
    pilot = read_json(FOLDER / 'pilot_results.json')
    assisted = read_json(FOLDER / 'assisted_summary.json')['results']
    reviews = read_json(FOLDER / 'agent_review.json')
    defects = []
    actual_verifications = 0
    for call in calls:
        if call['stage'] != 'verify' or call['status'] != 'ok':
            continue
        payload = json.loads(call['request']['messages'][1]['content'][0]['text'])
        visible = set(call['actual_frame_ids'])
        for claim in payload['claims']:
            actual_verifications += 1
            if not set(claim['evidence_frame_ids']).issubset(visible):
                defects.append({'call': call['cache_key'], 'claim': claim['event_id'], 'issue': 'unsupplied_evidence'})
    outputs = []
    for branch, records in [('B', pilot), ('assisted', assisted)]:
        for result in records:
            qa = result.get('qa')
            errors = []
            if qa:
                expected = ' '.join(e['text'].strip() for e in qa['claims'])
                if qa['answer'] != expected:
                    errors.append('answer_not_verbatim')
                supported = {v['claim_id'] for v in result['verification']['verdicts'] if v['verdict'] == 'supported'}
                if not {e['event_id'] for e in qa['claims']}.issubset(supported):
                    errors.append('unsupported_selected_event')
                if 'options' in qa:
                    errors.append('open_qa_contains_options')
            status = 'held_visual_review' if branch == 'B' else 'assisted_pending_human'
            if not qa:
                status = 'held_no_qa'
            if errors:
                status = 'held_contract_error'
            outputs.append({'case_id': result['case_id'], 'clip_id': result['clip_id'], 'branch': branch, 'qa': qa, 'disposition': status, 'errors': errors, 'agent_review': reviews.get(result['case_id']) if branch == 'B' else None, 'human_gold': False, 'autonomous_generation': branch == 'B', 'formal_release': False})
    single = read_json(FOLDER / 'single_frame_results.json')
    summary = {'pilot_cases': len(pilot), 'pilot_qa_drafts': sum(bool(r.get('qa')) for r in pilot), 'pilot_agent_material_holds': sum(r.get('qa') is not None and reviews[r['case_id']]['disposition'].startswith('hold_') for r in pilot), 'assisted_qa_drafts': sum(bool(r.get('qa')) for r in assisted), 'assisted_reference_events_selected': sum(len((r.get('qa') or {}).get('claims', [])) for r in assisted), 'verification_claim_instances': actual_verifications, 'unsupplied_evidence_errors': defects, 'output_contract_errors': [r for r in outputs if r['errors']], 'api_requests': len(calls) + len(single), 'pipeline_requests': len(calls), 'pipeline_errors': sum(r['status'] != 'ok' for r in calls), 'single_frame_requests': len(single), 'input_tokens': sum((r.get('usage') or {}).get('prompt_tokens', 0) for r in calls + single), 'output_tokens': sum((r.get('usage') or {}).get('completion_tokens', 0) for r in calls + single), 'max_prompt_tokens': max((r.get('usage') or {}).get('prompt_tokens', 0) for r in calls + single), 'stage_counts': dict(collections.Counter(r['stage'] + ':' + r['status'] for r in calls)), 'formal_release': False, 'human_validated': 0, 'long_generation_started': False, 'reason_long_not_started': 'Local visual truth and verifier specificity failed the prerequisite; extending unreliable ledgers into history is not justified.'}
    save_json(FOLDER / 'final_summary.json', summary)
    save_jsonl(FOLDER / 'review_candidates.jsonl', outputs)
    save_jsonl(FOLDER / 'first10_outputs.jsonl', outputs[:10])
    sources = [ROOT / 'impact_qa/event_v22.py', *sorted((ROOT / 'scripts').glob('*event_v22*.py')), ROOT / 'configs/impact_qa/event_v22.json', *sorted((ROOT / 'prompts/impact_qa/v22').glob('*.txt')), ROOT / 'prompts/impact_qa/diagnostics/v22_single_frame_probe.txt', FOLDER / 'agent_event_reference.json', FOLDER / 'challenge_reference.json']
    save_json(FOLDER / 'final_artifact_hashes.json', {str(p.relative_to(ROOT)): digest(p) for p in sources})
    if defects or summary['output_contract_errors']:
        raise RuntimeError('review_v22:contract_or_media_coverage_failed')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
