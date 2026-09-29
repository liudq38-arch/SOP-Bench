from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from impact_qa.common import fingerprint, read_json, save_json
from impact_qa.source_frames import extract_source_frames


def render_case(case, output):
    folder = Path(output) / 'frames' / case['case_id']
    manifest = folder / 'manifest.json'
    media = Path(case['source_video']).stat()
    version = fingerprint([case, media.st_size, media.st_mtime_ns, Path(__file__).read_text(), Path(__file__).with_name('source_frames.py').read_text()])
    if manifest.exists():
        result = read_json(manifest)
        if result['version'] != version:
            raise ValueError('review_frames:changed_input_requires_new_directory:' + case['case_id'])
        if Path(result['sheet']).is_file() and all(Path(r['path']).is_file() for r in result['frames']):
            return result
    a, b = case['target_interval_frames']
    ca, cb = case['context_interval_frames']
    before, target, after = case.get('sample_counts', [4, 10, 4])
    indices = np.rint(np.concatenate([np.linspace(ca, a-1, before) if ca < a else [], np.linspace(a, b-1, target), np.linspace(b, cb-1, after) if b < cb else []])).astype(int).tolist()
    result = extract_source_frames(case['source_video'], indices, folder, case['fps'])
    sheet = Image.new('RGB', (1800, 40 + 360 * int(np.ceil(len(result['frames']) / 3))), 'white')
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 8), f"{case['case_id']} {case['trial_id']} {case['target_hand']} {a/case['fps']:.3f}-{b/case['fps']:.3f}s; sampling, not sync", fill='black')
    for k, row in enumerate(result['frames']):
        idx = row['source_frame_index']
        row['scope'] = 'TARGET' if a <= idx < b else 'BEFORE' if idx < a else 'AFTER'
        im = Image.open(row['path'])
        im.thumbnail((600, 334))
        x, y = k % 3 * 600, 40 + k // 3 * 360
        sheet.paste(im, (x, y))
        draw.text((x + 3, y + 337), f"{row['scope']} {row['frame_id']} {row['pts_s']:.3f}s", fill='red' if row['scope'] == 'TARGET' else 'black')
    path = folder / 'sheet.jpg'
    sheet.save(path, quality=96)
    result.update(case_id=case['case_id'], version=version, sheet=str(path))
    save_json(manifest, result)
    return result
