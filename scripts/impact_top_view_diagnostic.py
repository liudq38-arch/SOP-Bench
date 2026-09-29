import argparse
import asyncio
import hashlib
import json
import sys
import zipfile
import zlib
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl


def prepare():
    video = 'KI03AR28_Reassembly_A_003'
    front = read_json(ANNOTATIONS / 'TAS-B/front' / (video + '_front.json'))
    top = read_json(ANNOTATIONS / 'TAS-B/top' / (video + '_top.json'))
    assert front['meta_data'] == top['meta_data']
    cases = [c for c in read_jsonl(OUT / 'gt_v13_inputs/cases.jsonl') if c['video_id'] == video + '_front' and c['kind'] == 'tool_identity' and c['condition'] == 'dense_crop']
    for c in cases:
        interval = c['facts']['target_interval']
        segment = next(s for s in front['segments'] if [s['start_frame'], s['end_frame']] == interval and s['entity'] == c['facts']['hand'])
        assert segment in top['segments']
    archive = Path('/data_1/ldq/dataset/impact/downloads/v1.1/videos/IMPACT-v1.1-videos-top.zip')
    target = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/top') / (video + '_top.mp4')
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        info = z.getinfo('IMPACT-v1.1/videos/top/' + target.name)
        if not target.exists():
            temp = target.with_suffix('.partial.mp4')
            with z.open(info) as src, temp.open('wb') as dst:
                while data := src.read(8 * 1024 * 1024):
                    dst.write(data)
            temp.replace(target)
        crc = 0
        with target.open('rb') as stream:
            while data := stream.read(8 * 1024 * 1024):
                crc = zlib.crc32(data, crc)
        assert crc == info.CRC
    folder = OUT / 'gt_v13_top_inputs'
    folder.mkdir(exist_ok=True)
    wanted = {im['frame_index'] for c in cases for im in c['image_refs'][4:20:2]}
    count, max_error = 0, 0.0
    with av.open(str(target)) as container:
        container.streams.video[0].thread_type = 'AUTO'
        for n, frame in enumerate(container.decode(video=0)):
            count += 1
            max_error = max(max_error, abs(float(frame.pts * frame.time_base) - n / 30))
            if n in wanted:
                ImageOps.pad(frame.to_image(), (640, 448), color='white').save(folder / f'{n}.jpg', quality=95)
    assert count == top['meta_data']['num_frames'] and max_error < 1e-5
    for c in cases:
        c['condition'] = 'dense_crop_plus_top8'
        added = []
        board = Image.new('RGB', (1600, 500), 'white')
        draw = ImageDraw.Draw(board)
        for i, old in enumerate(c['image_refs'][4:20:2]):
            n = old['frame_index']
            path = folder / f'{n}.jpg'
            added.append({'evidence_id': f'top_{i}', 'path': str(path), 'frame_index': n, 'requested_time_s': n / 30, 'view': 'top', 'time_scope': 'Same execution, synchronized top-camera event frame. Original recording time, not a manual reference.', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            board.paste(ImageOps.contain(Image.open(path), (400, 220)), (i % 4 * 400, i // 4 * 250 + 24))
            draw.text((i % 4 * 400 + 3, i // 4 * 250 + 3), f'top_{i} | {n / 30:.3f}s', fill='black')
        c['image_refs'] += added
        c['top_contact_sheet'] = str(folder / (c['contract_id'] + '.jpg'))
        board.save(c['top_contact_sheet'], quality=95)
        c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
    save_jsonl(folder / 'cases.jsonl', cases)
    save_json(REPORTS / 'gt_v13_top_sync_validation.json', {'video': video, 'matched_tool_action_intervals': [c['facts']['target_interval'] for c in cases], 'all_segment_lists_equal': front['segments'] == top['segments'], 'fps': 30, 'frames': count, 'max_pts_error': max_error, 'crc32': hex(crc), 'sync_basis': 'Official synchronized-view release, equal timing metadata and exact target segment equality; paired frames require direct inspection.', 'bytes_extracted': target.stat().st_size})


async def run():
    cases = read_jsonl(OUT / 'gt_v13_top_inputs/cases.jsonl')
    prompt = (ROOT / 'prompts/impact_qa/v13/visual_review.txt').read_text() + '\nAfter the 20 front-camera event images, eight synchronized TOP-camera event frames are attached. These eight are the same execution, with original timestamps. They are not manual references. Use them to disambiguate visual identity without assuming cross-view appearance is identical.\n'
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    records = []
    try:
        for c in cases:
            payload = {'question': c['question'], 'public_procedure': c['public_procedure'], 'original_start_s': c['start_frame'] / 30, 'original_end_s_exclusive': (c['end_frame_inclusive'] + 1) / 30, 'event_images': [{'id': im['evidence_id'], 'time_s': im['requested_time_s'], 'view': im['view']} for im in c['image_refs']]}
            result = await pool.call('gt_v13_top_visual', prompt, payload, c['image_refs'], max_tokens=850)
            records.append({'contract_id': c['contract_id'], 'condition': c['condition'], 'visual_review': result['result'], 'cache_key': result['cache_key'], 'input_hash': c['input_hash']})
            save_jsonl(OUT / 'gt_v13/top_results.jsonl', records)
            print(json.dumps(records[-1]), flush=True)
    finally:
        await pool.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        asyncio.run(run())
