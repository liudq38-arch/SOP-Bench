import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_jsonl, save_json, save_jsonl
from run_impact_gt_qa import export, process


async def main():
    selected = []
    for original in read_jsonl(OUT / 'gt_v11_inputs/contracts.jsonl'):
        if original['kind'] not in {'tool_identity', 'component_unassembled'}:
            continue
        c = copy.deepcopy(original)
        c['parent_contract_hash'] = original['contract_hash']
        if c['kind'] == 'tool_identity':
            c['question_proposition'] = 'Which tool did I pick up with my right hand in this clip?'
            c['canonical_answer'] = 'I picked up a screwdriver with my right hand.'
            c['choice_texts'] = ['A screwdriver.', 'A wrench.', 'A pair of pliers.']
            c['mcq_question_proposition'] = c['question_proposition']
            c['facts']['granularity_rule'] = 'The GT action names a Phillips screwdriver. This question deliberately asks only for the broader tool class, screwdriver, because the tip type is not resolved in the frames.'
            c['forbidden_claims'].append('tool tip subtype or handle color in the answer')
        else:
            c['question_proposition'] = 'Had I installed the bearing plate by the end of this clip?'
            c['facts']['granularity_rule'] = 'Ask presence of installation only. State 0 supports not installed; do not ask fine installation correctness.'
        c['contract_hash'] = fingerprint({k: v for k, v in c.items() if k not in {'contract_hash', 'input_hash', 'image_refs', 'frame_indices', 'contact_sheet'}})
        c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
        selected.append(c)
    save_jsonl(OUT / 'gt_v11_1_inputs/contracts.jsonl', selected)
    prompts = {s: (ROOT / 'prompts/impact_qa/v11' / (s + '.txt')).read_text() for s in ['generate', 'source_review', 'visual_review']}
    prompts['visual_review'] += '\nAnswer only the granularity asked. A generic tool question does not require its tip subtype. A question about whether a part was installed does not require proving torque, internal engineering tolerances, or completion of later unrelated steps. If part identity itself is unclear, keep that uncertainty. If visible action is still ongoing at the cutoff, distinguish that from not knowing what will happen later. Do not demand an eventual result to answer an explicitly earlier time.\n'
    (ROOT / 'prompts/impact_qa/v11_1').mkdir(exist_ok=True)
    (ROOT / 'prompts/impact_qa/v11_1/visual_review.txt').write_text(prompts['visual_review'])
    code_hash = fingerprint({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), ROOT / 'scripts/run_impact_gt_qa.py', ROOT / 'impact_qa/gt_qa.py']})
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    try:
        records = await asyncio.gather(*(process(pool, c, prompts, 'gt_v11_1', code_hash) for c in selected))
    finally:
        await pool.close()
    export(records, selected, 'gt_v11_1')
    save_json(REPORTS / 'gt_v11_1_refinement.json', {'items': len(selected), 'changes': ['tool subtype -> visible generic tool class, still entailed by exact GT action', 'state-0 question -> installation presence, without correctness presupposition'], 'model_sees': 'visual frames + exact source facts + GT reference answer', 'same_media_as_v11': True})
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
