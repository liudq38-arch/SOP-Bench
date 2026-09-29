import copy
import hashlib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, fingerprint, read_jsonl, save_json, save_jsonl
from impact_qa.quality_v16 import check_integrity


def normalize(c, images=None):
    c = copy.deepcopy(c)
    c['question'] = c.get('question', c.get('question_proposition'))
    c['mcq_question'] = c.get('mcq_question_proposition', c['question'])
    original = c.get('options', c.get('choice_texts'))
    answer = original[c.get('correct_option', c.get('correct_choice_index', 0))]
    c['options'] = sorted(original, key=lambda x: fingerprint([c['contract_id'], 'v16', x]))
    c['correct_option'] = c['options'].index(answer)
    if c['kind'] == 'tool_identity':
        c['facts'] = {'tool': c['tool'], 'hand': c['hand'], 'action': 'pick_up', 'target_interval_exclusive': c['target_interval_exclusive'], 'scope': 'generic tool identity only, no tip subtype or appropriateness'}
    c['image_refs'] = sorted(copy.deepcopy(images or c['image_refs']), key=lambda im: (im['frame_index'], im['evidence_id']))
    for im in c['image_refs']:
        im['sha256'] = hashlib.sha256(Path(im['path']).read_bytes()).hexdigest()
    c['source_split'] = 'official_train_previously_exposed'
    c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
    check_integrity(c)
    return c


def main():
    dense = {r['contract_id']: r['image_refs'] for r in read_jsonl(OUT / 'gt_v13_inputs/cases.jsonl') if r['condition'] == 'dense_crop'}
    rows = []
    for name in ['gt_v14_1_tools', 'gt_v14_acceptance_inputs']:
        rows.extend(normalize(r) for r in read_jsonl(OUT / name / 'contracts.jsonl'))
    for c in read_jsonl(OUT / 'gt_v12_2_inputs/contracts.jsonl'):
        if c['kind'] != 'tool_identity':
            rows.append(normalize(c, dense.get(c['contract_id'], c['audit_frame_refs'])))
    require_ids = {r['contract_id'] for r in rows}
    if len(require_ids) != len(rows):
        raise ValueError('prepare_v16:duplicate_event')
    smoke = []
    for kind in sorted({c['kind'] for c in rows}):
        candidates = sorted([c for c in rows if c['kind'] == kind], key=lambda c: fingerprint(c['contract_id']))
        smoke.extend(candidates[:2])
    for identifier in ['tool_39cf6e0e97ab91a2e9dd', 'tool_de3175ea544adfb611e7', 'tool_451b9facfc0f67fda7e0']:
        c = next(r for r in rows if r['contract_id'] == identifier)
        if c not in smoke:
            smoke.append(c)
    folder = OUT / 'quality_v16_inputs'
    save_jsonl(folder / 'contracts.jsonl', rows)
    save_jsonl(folder / 'smoke.jsonl', smoke)
    save_jsonl(folder / 'first10.jsonl', rows[:10])
    report = {'events': len(rows), 'smoke': len(smoke), 'kinds': dict(Counter(c['kind'] for c in rows)), 'image_counts': dict(Counter(len(c['image_refs']) for c in rows)), 'references_verified': sum(len(c['references']) for c in rows), 'independent_acceptance': False, 'official_val_test_used': False}
    save_json(folder / 'precheck.json', report)
    print(report)
    for c in rows[:10]:
        print(c['contract_id'], c['kind'], len(c['image_refs']), c['question'])


if __name__ == '__main__':
    main()
