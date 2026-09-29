from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageOps

from impact_qa.anomaly_multiview import FOLDER
from impact_qa.common import fingerprint, read_json, save_json


REGIONS = {
    'ac_caf796a863e97b95_ego': (.23, .42, .83, .95),
    'mv_4b8ab0029243_ego': (.30, .25, 1., .95),
    'mv_6a0bcfa0824d_ego': (.30, .20, 1., .90),
    'mv_8ddc3ed4e499_ego': (.10, .40, .80, 1.),
    'mv_cfe39ed51190_ego': (.15, .40, .85, 1.),
}


def main():
    folder = FOLDER / 'details'
    folder.mkdir(exist_ok=True)
    records = []
    for case_id, region in REGIONS.items():
        source = read_json(FOLDER / 'frames' / case_id / 'manifest.json')
        frames = [f for f in source['frames'] if f['scope'] == 'TARGET']
        for start in range(0, len(frames), 6):
            selected = frames[start:start + 6]
            sheet = Image.new('RGB', (1600, 40 + 440 * 3), 'white')
            draw = ImageDraw.Draw(sheet)
            draw.text((8, 8), f'{case_id} | original-frame crop | page {start // 6 + 1}', fill='black')
            for j, frame in enumerate(selected):
                with Image.open(frame['path']) as im:
                    box = tuple(round(v * (im.width if i % 2 == 0 else im.height)) for i, v in enumerate(region))
                    crop = ImageOps.contain(im.crop(box), (800, 407))
                    x, y = j % 2 * 800, 40 + j // 2 * 440
                    sheet.paste(crop, (x, y))
                draw.text((x + 8, y + 410), f"{frame['frame_id']} | PTS {frame['pts_s']:.3f}s | TARGET", fill='black')
            path = folder / f'{case_id}_p{start // 6 + 1}.jpg'
            sheet.save(path, quality=96)
            records.append({'case_id': case_id, 'sheet': str(path), 'crop_normalized': region, 'frames': selected, 'source_version': source['version'], 'renderer_sha': fingerprint(Path(__file__).read_text()), 'new_source_frames': 0})
    save_json(folder / 'manifest.json', records)
    print({'detail_sheets': len(records), 'reused_frame_entries': sum(len(r['frames']) for r in records)})


if __name__ == '__main__':
    main()
