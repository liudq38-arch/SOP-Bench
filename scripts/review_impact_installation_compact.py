import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, ROOT, read_jsonl, save_json, save_jsonl


async def main(strict=False):
    kinds = ['component_installed', 'component_unassembled'] if strict else ['component_installed']
    cases = [c for c in read_jsonl(OUT / 'gt_v13_inputs/cases.jsonl') if c['kind'] in kinds and c['condition'] == 'dense_crop']
    references = read_jsonl(OUT / 'gt_v13_action_reference/references.jsonl')
    prompt = (ROOT / 'prompts/impact_qa/v13/install_compact.txt').read_text()
    variant = 'install_state_strict' if strict else 'install_compact'
    if strict:
        prompt += (ROOT / 'prompts/impact_qa/v13/install_state_boundary.txt').read_text()
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    async def process(c):
        payload = {'question': c['question'], 'target_cutoff_original_s': c['end_frame_inclusive'] / 30, 'media_protocol': 'First 4 full-frame context images and next 16 crop images show this execution; timestamps are original recording seconds. Last 5 named action-example cards are a different training execution, in alphabetical order, not target events. Reference placeholder time zero is not a target timestamp.'}
        result = await pool.call('gt_v13_' + variant + '_visual', prompt, payload, c['image_refs'] + references, max_tokens=450)
        v = result['result']
        assert v['answer'] in ['Yes', 'No', 'cannot determine']
        assert v['answerability'] in ['answerable', 'uncertain', 'unanswerable']
        assert len(v['visible_evidence'].split()) <= 60
        assert (v['answerability'] == 'answerable') == (v['answer'] in ['Yes', 'No'])
        record = {'contract_id': c['contract_id'], 'condition': 'dense_crop_' + ('install_state_strict' if strict else 'install_reference_compact'), 'visual_review': v, 'cache_key': result['cache_key'], 'prompt_changed': True}
        save_json(OUT / ('gt_v13/' + variant + '_runs') / (c['contract_id'] + '.json'), record)
        print(json.dumps(record), flush=True)
        return record
    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(OUT / ('gt_v13/' + variant + '_results.jsonl'), records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict-state-boundary', action='store_true')
    asyncio.run(main(parser.parse_args().strict_state_boundary))
