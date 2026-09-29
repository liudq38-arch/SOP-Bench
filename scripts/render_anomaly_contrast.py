import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import av
import numpy as np
from PIL import Image, ImageDraw

from impact_qa.anomaly_contrast import FOLDER
from impact_qa.common import read_jsonl, save_json


def render(case):
    folder = FOLDER / case['split'] / 'direct_frames' / case['case_id']
    folder.mkdir(parents=True, exist_ok=True)
    a, b = case['start_frame'], case['end_frame_exclusive']
    fps = case['clip']['fps']
    before = np.rint(np.linspace(max(0, a - round(4 * fps)), a - 1, 4)).astype(int).tolist() if a else []
    target = np.rint(np.linspace(a, b - 1, min(12, b - a))).astype(int).tolist()
    after = np.rint(np.linspace(b, min(case['clip']['frame_count'] - 1, b + round(6 * fps)), 4)).astype(int).tolist() if b < case['clip']['frame_count'] else []
    indices = sorted(set(before + target + after))
    wanted = set(indices)
    sheet = Image.new('RGB', (1600, 40 + 270 * int(np.ceil(len(indices) / 4))), 'white')
    draw = ImageDraw.Draw(sheet)
    draw.text((6, 10), f"{case['case_id']} | target {case['target_hand']} | {case['trial_id']} | {a/fps:.3f}-{b/fps:.3f}s", fill='black')
    records = []
    with av.open(case['clip']['source_video']) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        container.seek(max(0, int(indices[0] / fps / stream.time_base)), stream=stream, backward=True)
        for frame in container.decode(stream):
            t = float(frame.pts * frame.time_base)
            index = round(t * fps)
            if index > indices[-1]:
                break
            if index not in wanted:
                continue
            original = frame.to_image()
            path = folder / f'f{index:07d}.jpg'
            original.save(path, quality=94)
            crop = original.crop((round(original.width * .04), round(original.height * .2), round(original.width * .96), original.height))
            crop.thumbnail((400, 244))
            n = len(records)
            x, y = (n % 4) * 400, 40 + (n // 4) * 270
            sheet.paste(crop, (x, y))
            scope = 'TARGET' if a <= index < b else 'BEFORE' if index < a else 'AFTER'
            draw.text((x + 4, y + 247), f'{scope} f{index:07d} {t:.3f}s', fill='red' if scope == 'TARGET' else 'black')
            records.append({'frame_id': f'f{index:07d}', 'source_frame_index': index, 'source_time_s': t, 'scope': scope, 'path': str(path)})
    assert [r['source_frame_index'] for r in records] == indices, 'contrast_sheet:missing_frame:' + case['case_id']
    path = folder / 'sheet.jpg'
    sheet.save(path, quality=94)
    result = {'case_id': case['case_id'], 'sheet': str(path), 'frames': records, 'reviewer_status': 'unreviewed'}
    save_json(folder / 'manifest.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['discovery', 'validation'], default='discovery')
    args = parser.parse_args()
    if args.split == 'validation' and not (FOLDER / 'rulebook_frozen_v1.json').exists():
        raise ValueError('contrast_sheet:freeze_rules_before_validation')
    cases = [r for r in read_jsonl(FOLDER / 'cases.jsonl') if r['split'] == args.split]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(render, cases))
    save_json(FOLDER / args.split / 'direct_frames_manifest.json', results)
    print({'cases': len(results), 'frames': sum(len(r['frames']) for r in results)})


if __name__ == '__main__':
    main()
