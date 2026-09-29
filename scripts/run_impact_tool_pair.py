import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.reliable_pool import ReliablePool
from impact_qa.tool_batch import parents
from impact_qa.tool_review_v15 import validate


async def main(phase):
    cases = read_jsonl(OUT / 'gt_v15_endpoint_inputs' / phase / 'contracts.jsonl')
    folder = OUT / 'gt_v15_tools/pairboard' / phase
    prompt = (ROOT / 'prompts/impact_qa/v15/tool_pair.txt').read_text()
    old = parents(phase)
    code = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    gate = asyncio.Semaphore(12)
    prepared = []
    for c in cases:
        refs = [im for im in c['image_refs'] if im['evidence_id'] in ['context_0', 'context_3']]
        assert len(refs) == 2 and refs[0]['frame_index'] < refs[1]['frame_index']
        path = folder / 'frames' / (fingerprint(refs)[:24] + '.jpg')
        if not path.exists():
            board = Image.new('RGB', (1920, 600), 'white')
            draw = ImageDraw.Draw(board)
            for i, im in enumerate(refs):
                draw.text((i * 960 + 8, 8), ('BEFORE ' if i == 0 else 'AFTER ') + im['evidence_id'] + f' | {im["requested_time_s"]:.3f}s', fill='black')
                board.paste(Image.open(im['path']), (i * 960, 40))
            path.parent.mkdir(parents=True, exist_ok=True)
            board.save(path, quality=96)
        image = {'evidence_id': 'pair_board', 'frame_index': refs[0]['frame_index'], 'requested_time_s': refs[0]['requested_time_s'], 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'view': 'front_composite_before_after', 'time_scope': 'Composite, not a single frame. LEFT context_0 before; RIGHT context_3 after. See panel_map for original times.'}
        prepared.append((c, refs, image))
    save_jsonl(folder / 'first10.jsonl', [{'contract_id': c['contract_id'], 'evidence_refs': refs, 'image_refs': [im]} for c, refs, im in prepared[:10]])

    async def process(c, refs, image):
        async with gate:
            payload = {'question': c['question'], 'panel_map': [{'panel': 'left' if i == 0 else 'right', 'evidence_id': im['evidence_id'], 'original_time_s': im['requested_time_s']} for i, im in enumerate(refs)]}
            key = fingerprint([code, prompt, payload, image, pool.model_revision])
            path = folder / 'runs' / (c['contract_id'] + '.json')
            if path.exists():
                previous = read_json(path)
                assert previous['run_key'] == key, 'pair:changed_version'
                if previous['status'] == 'ok':
                    return previous
            r = {'contract_id': c['contract_id'], 'run_key': key, 'status': 'running', 'phase': phase, 'condition': 'pairboard', 'previous_comparison': old[c['contract_id']]['comparison'], 'generation': old[c['contract_id']]['generation'], 'image_refs': [image], 'evidence_refs': refs}
            try:
                response = await pool.call('gt_v15_tool_pair', prompt, payload, [image], max_tokens=350)
                value, changes, answerable = validate(response['result'], refs, 'transition8')
                comparison = 'abstain' if not answerable else ('short_answer_match' if value['tool'] == c['tool'] else 'short_answer_conflict')
                r.update(status='ok', raw_visual_review=response['result'], visual_review=value, normalizations=changes, answerable=answerable, comparison=comparison, proposed_retain=comparison == 'short_answer_match', cache_key=response['cache_key'])
            except Exception as exc:
                r.update(status='error', proposed_retain=False, error=f'pair:{type(exc).__name__}:{exc}')
            save_json(path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'status', 'comparison', 'error']}), flush=True)
            return r

    try:
        records = await asyncio.gather(*(process(*row) for row in prepared))
    finally:
        await pool.close()
    save_jsonl(folder / 'full_results.jsonl', records)
    summary = {'condition': 'pairboard', 'phase': phase, 'events': len(cases), 'counts': dict(Counter(r.get('comparison', 'error') for r in records)), 'gains': [r['contract_id'] for r in records if r['proposed_retain'] and r['previous_comparison'] != 'short_answer_match'], 'regressions': [r['contract_id'] for r in records if not r['proposed_retain'] and r['previous_comparison'] == 'short_answer_match'], 'independent_acceptance': False, 'code_hash': code, 'prompt_hash': hashlib.sha256(prompt.encode()).hexdigest()}
    save_json(folder / 'full_summary.json', summary)
    print(json.dumps(summary), flush=True)
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True, choices=['development', 'exposed_regression'])
    asyncio.run(main(parser.parse_args().phase))
