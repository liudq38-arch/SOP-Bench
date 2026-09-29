from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageOps

from impact_qa.anomaly_multiview import FOLDER
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json
from impact_qa.source_frames import extract_source_frames


def main():
    case_id = 'mv_6a0bcfa0824d_ego'
    case = next(c for c in read_jsonl(FOLDER / 'cases.jsonl') if c['case_id'] == case_id)
    folder = FOLDER / 'dense' / case_id
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / 'manifest.json'
    version = fingerprint([case, Path(__file__).read_text(), (ROOT / 'impact_qa/source_frames.py').read_text()])
    if manifest.exists():
        cached = read_json(manifest)
        if cached['version'] != version:
            raise ValueError('multiview_dense:changed_renderer_requires_new_directory')
        if all(Path(f['path']).exists() for f in cached['frames']) and all(Path(p).exists() for p in cached['sheets']):
            print({'cached': True, 'frames': len(cached['frames'])})
            return
    a, b = case['target_interval_frames']
    result = extract_source_frames(case['source_video'], range(a, b), folder, case['fps'])
    sheets = []
    crop_normalized = (.30, .20, 1., .90)
    for start in range(0, len(result['frames']), 6):
        sheet = Image.new('RGB', (1600, 1360), 'white')
        draw = ImageDraw.Draw(sheet)
        draw.text((8, 8), f'{case_id} | ALL target frames | page {start // 6 + 1}', fill='black')
        for j, frame in enumerate(result['frames'][start:start + 6]):
            frame['scope'] = 'TARGET'
            with Image.open(frame['path']) as im:
                box = tuple(round(v * (im.width if i % 2 == 0 else im.height)) for i, v in enumerate(crop_normalized))
                crop = ImageOps.contain(im.crop(box), (800, 407))
                x, y = j % 2 * 800, 40 + j // 2 * 440
                sheet.paste(crop, (x, y))
            draw.text((x + 8, y + 410), f"{frame['frame_id']} | PTS {frame['pts_s']:.3f}s", fill='black')
        path = folder / f'p{start // 6 + 1}.jpg'
        sheet.save(path, quality=96)
        sheets.append(str(path))
    result.update({'case_id': case_id, 'version': version, 'source_video': case['source_video'], 'sheets': sheets, 'crop_normalized': crop_normalized, 'sampling': 'every_source_frame_in_native_target'})
    save_json(manifest, result)
    print({'frames': len(result['frames']), 'sheets': len(sheets)})


if __name__ == '__main__':
    main()
