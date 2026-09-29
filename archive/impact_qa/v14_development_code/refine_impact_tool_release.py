import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import av
from PIL import ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.reliable_pool import ReliablePool
from impact_qa.evidence_ids import normalize_evidence
from impact_qa.state_qa import FRONT


FOLDER = OUT / 'gt_v14_1_tools'
ROI = (280, 270, 1020, 700)


def prepare():
    rows = read_jsonl(OUT / 'gt_v14_tool_inputs/contracts.jsonl')
    by_video = defaultdict(list)
    for c in rows:
        by_video[c['video_id']].append(c)
    for video, cases in by_video.items():
        with av.open(str(FRONT / (video + '.mp4'))) as container:
            stream = container.streams.video[0]
            stream.thread_type = 'AUTO'
            for c in cases:
                for ref in c['image_refs'][4:]:
                    ref['path'] = str(FOLDER / 'frames' / (fingerprint([video, ref['frame_index'], ROI, [960, 560]])[:24] + '.jpg'))
                wanted = {r['frame_index']: r['path'] for r in c['image_refs'][4:] if not Path(r['path']).exists()}
                if wanted:
                    container.seek(int((min(wanted) / 30) / float(stream.time_base)), stream=stream, backward=True)
                    seen = set()
                    for frame in container.decode(stream):
                        actual = float(frame.pts * frame.time_base)
                        number = round(actual * 30)
                        if number in wanted:
                            assert abs(actual - number / 30) < 1e-5
                            p = Path(wanted[number])
                            p.parent.mkdir(parents=True, exist_ok=True)
                            ImageOps.pad(frame.to_image().crop(ROI), (960, 560), color='white').save(p, quality=96)
                            seen.add(number)
                        if number >= max(wanted):
                            break
                    assert seen == set(wanted), 'tool_refine:missing_pts:' + c['contract_id']
                for ref in c['image_refs']:
                    ref['sha256'] = hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()
                c['media_variant'] = {'roi': ROI, 'canvas': [960, 560], 'source_pts_checked': True, 'context_unchanged': True}
                c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
        print({'prepared': video, 'events': len(cases)}, flush=True)
    save_jsonl(FOLDER / 'contracts.jsonl', rows)
    save_jsonl(FOLDER / 'first10.jsonl', rows[:10])


async def run(smoke=False):
    cases = read_jsonl(FOLDER / 'contracts.jsonl')
    old = {r['contract_id']: r for r in read_jsonl(OUT / 'gt_v14_tools/results.jsonl')}
    if smoke:
        failures = [c for c in cases if old[c['contract_id']]['short_answer_comparison'] != 'short_answer_match']
        controls = sorted([c for c in cases if c not in failures], key=lambda c: fingerprint(c['contract_id']))[:4]
        cases = failures + controls
    pool = ReliablePool(Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4), FOLDER / 'request_audit')
    prompt = (ROOT / 'prompts/impact_qa/v14/tool_track.txt').read_text()
    code = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    gate = asyncio.Semaphore(12)

    async def process(c):
        async with gate:
            key = fingerprint([c['input_hash'], prompt, code, pool.model_revision])
            path = FOLDER / 'normalized_runs' / (c['contract_id'] + '.json')
            if path.exists():
                previous = read_json(path)
                assert previous['run_key'] == key, 'tool_refine:changed_version'
                if previous['status'] == 'ok':
                    return previous
            r = {'contract_id': c['contract_id'], 'run_key': key, 'status': 'running', 'generation_parent': 'gt_v14_tools', 'generation': old[c['contract_id']]['generation']}
            try:
                payload = {'question': c['question'], 'clip_start_original_s': c['start_frame'] / 30, 'clip_end_original_s_exclusive': (c['end_frame_inclusive'] + 1) / 30}
                response = await pool.call('gt_v14_1_tool_track', prompt, payload, c['image_refs'], max_tokens=350)
                v, normalizations = normalize_evidence(response['result'], c['image_refs'])
                assert v['tool'] in ['screwdriver', 'wrench', 'pliers', 'unknown']
                assert v['answerability'] in ['answerable', 'uncertain']
                assert isinstance(v['pickup_visible'], bool)
                refs = {im['evidence_id']: im for im in c['image_refs']}
                assert set(v['evidence_image_ids']) <= set(refs)
                if v['answerability'] == 'answerable':
                    assert v['pickup_visible'] and v['tool'] != 'unknown'
                    a, b = v['before_image_id'], v['after_image_id']
                    assert a in v['evidence_image_ids'] and b in v['evidence_image_ids']
                    assert refs[a]['frame_index'] < refs[b]['frame_index'], 'tool_track:nonchronological_evidence'
                assert len(v['visible_evidence'].split()) <= 40
                verdict = 'abstain' if v['answerability'] != 'answerable' else ('short_answer_match' if v['tool'] == c['tool'] else 'short_answer_conflict')
                r.update(status='ok', visual_review=v, raw_visual_review=response['result'], evidence_id_normalizations=normalizations, cache_key=response['cache_key'], short_answer_comparison=verdict)
            except Exception as exc:
                r.update(status='error', error=f'tool_refine:{type(exc).__name__}:{exc}')
            save_json(path, r)
            print(json.dumps({k: r.get(k) for k in ['contract_id', 'status', 'short_answer_comparison', 'error']}), flush=True)
            return r

    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    label = 'normalized_smoke' if smoke else 'normalized_full'
    save_jsonl(FOLDER / (label + '_results.jsonl'), records)
    save_json(REPORTS / ('gt_v14_1_tool_' + label + '_summary.json'), {'events': len(records), 'counts': dict(Counter(r.get('short_answer_comparison', 'error') for r in records)), 'prompt_and_media_changed': True, 'reserve_used': False})
    if any(r['status'] != 'ok' for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        asyncio.run(run(args.smoke))
