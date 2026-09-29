import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_validation import validate_stage
from impact_qa.quality_v16 import decide


def main():
    cases = {c['contract_id']: c for name in ['quality_v16_inputs', 'quality_v16_training_inputs'] for c in read_jsonl(OUT / name / 'contracts.jsonl')}
    results = []
    for name in ['quality_v16_batch001', 'quality_v16_batch002']:
        for r in read_jsonl(OUT / name / 'results.jsonl'):
            if r['disposition'] != 'schema_or_runtime_error':
                continue
            stages, warnings = {}, []
            row = {'contract_id': r['contract_id'], 'old_error': r['error'], 'original_batch': name, 'not_automatically_accepted': True}
            try:
                for stage in ['generate', 'blind', 'source_audit', 'visual_audit']:
                    key = r['cache_keys'].get(stage)
                    if not key:
                        raise ValueError('missing_original_stage:' + stage)
                    raw = read_json(OUT / 'api_cache' / (key + '.json'))['result']
                    stages[stage], notes = validate_stage(stage, raw, cases[r['contract_id']], stages.get('generate'))
                    warnings.extend({'stage': stage, **note} for note in notes)
                row.update(status='format_only_recovered', decision=decide(cases[r['contract_id']], stages))
            except Exception as exc:
                row.update(status='still_rejected', error=f'{type(exc).__name__}:{exc}')
            row['warnings'] = warnings
            results.append(row)
    save_jsonl(OUT / 'evidence_v18_validation_replay/results.jsonl', results)
    summary = {'events': len(results), 'counts': dict(Counter(r['status'] for r in results)), 'recovered_decisions': dict(Counter(r['decision']['disposition'] for r in results if r['status'] == 'format_only_recovered')), 'new_api_requests': 0, 'old_outputs_overwritten': False, 'formal_release': False}
    save_json(REPORTS / 'evidence_v18_validation_replay.json', summary)
    print(summary)


if __name__ == '__main__':
    main()
