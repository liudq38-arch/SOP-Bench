import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_ids import normalize_evidence
from impact_qa.reliable_pool import ReliablePool


async def main(phase):
    frozen = read_json(REPORTS / 'gt_v14_tool_pipeline_frozen.json')
    for p, digest in frozen['files'].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest, 'frozen:changed:' + p
    if phase == 'development':
        base_folder, input_folder = OUT / 'gt_v14_tool_inputs', OUT / 'gt_v14_1_tools'
    else:
        base_folder, input_folder = OUT / 'gt_v14_acceptance_base', OUT / 'gt_v14_acceptance_inputs'
    folder = OUT / ('gt_v14_frozen_' + phase)
    base = {c['contract_id']: c for c in read_jsonl(base_folder / 'contracts.jsonl')}
    cases = read_jsonl(input_folder / 'contracts.jsonl')
    prompts = {name: (ROOT / ('prompts/impact_qa/v14/tool_' + name + '.txt')).read_text() for name in ['generate', 'track']}
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), folder / 'request_audit')
    assert pool.model_revision == frozen['model_revision']
    gate = asyncio.Semaphore(12)

    async def process(c):
        async with gate:
            path = folder / 'runs' / (c['contract_id'] + '.json')
            key = fingerprint([frozen['pipeline_hash'], base[c['contract_id']]['input_hash'], c['input_hash']])
            if path.exists():
                previous = read_json(path)
                assert previous['run_key'] == key
                if previous['status'] == 'ok':
                    return previous
            record = {'contract_id': c['contract_id'], 'run_key': key, 'status': 'running', 'pipeline_hash': frozen['pipeline_hash']}
            try:
                b = base[c['contract_id']]
                private = {k: b[k] for k in ['question', 'canonical_answer', 'source_label', 'hand', 'target_interval_exclusive']}
                gen = await pool.call('gt_v14_tool_generate', prompts['generate'], private, b['image_refs'], max_tokens=180)
                assert gen['result'] == {'question': c['question'], 'answer': c['canonical_answer']}, 'frozen:source_answer_mismatch'
                public = {'question': c['question'], 'clip_start_original_s': c['start_frame'] / 30, 'clip_end_original_s_exclusive': (c['end_frame_inclusive'] + 1) / 30}
                visual = await pool.call('gt_v14_1_tool_track', prompts['track'], public, c['image_refs'], max_tokens=350)
                v, changes = normalize_evidence(visual['result'], c['image_refs'])
                assert v['tool'] in ['screwdriver', 'wrench', 'pliers', 'unknown']
                assert v['answerability'] in ['answerable', 'uncertain']
                assert isinstance(v['pickup_visible'], bool)
                assert len(v['visible_evidence'].split()) <= 40
                if v['answerability'] == 'answerable':
                    assert v['pickup_visible'] and v['tool'] != 'unknown'
                    refs = {im['evidence_id']: im for im in c['image_refs']}
                    assert refs[v['before_image_id']]['frame_index'] < refs[v['after_image_id']]['frame_index']
                verdict = 'abstain' if v['answerability'] != 'answerable' else ('short_answer_match' if v['tool'] == c['tool'] else 'short_answer_conflict')
                record.update(status='ok', generation=gen['result'], visual_review=v, raw_visual_review=visual['result'], normalizations=changes, cache_keys=[gen['cache_key'], visual['cache_key']], comparison=verdict, proposed_retain=verdict == 'short_answer_match')
            except Exception as exc:
                record.update(status='error', error=f'frozen:{type(exc).__name__}:{exc}', proposed_retain=False)
            save_json(path, record)
            print(json.dumps({k: record.get(k) for k in ['contract_id', 'status', 'comparison', 'error']}), flush=True)
            return record

    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(folder / 'results.jsonl', records)
    output, evaluation = [], []
    for c, r in zip(cases, records):
        if not r.get('proposed_retain'):
            continue
        output.append({'contract_id': c['contract_id'], 'video_id': c['video_id'], 'question': c['question'], 'answer': c['canonical_answer'], 'options': c['options'], 'correct_option': c['correct_option'], 'references': c['references'], 'status': 'pending_direct_evidence_review', 'pipeline_hash': frozen['pipeline_hash']})
        for form in ['open', 'mcq']:
            evaluation.append({'qa_id': fingerprint([c['contract_id'], form])[:24], 'format': form, 'question': c['question'], 'image_paths': [im['path'] for im in c['image_refs']], 'original_times_s': [im['requested_time_s'] for im in c['image_refs']], 'annotation_assisted_sampling': True, **({'options': c['options']} if form == 'mcq' else {})})
    save_jsonl(folder / 'proposed_candidates.jsonl', output)
    save_jsonl(folder / 'evaluation_inputs.jsonl', evaluation)
    save_json(REPORTS / ('gt_v14_frozen_' + phase + '_summary.json'), {'phase': phase, 'events': len(cases), 'counts': dict(Counter(r.get('comparison', 'error') for r in records)), 'proposed_retained': len(output), 'pipeline_hash': frozen['pipeline_hash'], 'quality_acceptance': False})
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['development', 'acceptance'], required=True)
    asyncio.run(main(parser.parse_args().phase))
