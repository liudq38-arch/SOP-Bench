import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = ROOT / 'annotations/impact/IMPACT-v1.1/annotations'
VIDEOS = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos')
OUTPUT = ROOT / 'reports/impact_qa/object_knowledge'
FFMPEG = '/home/ldq/miniconda3/envs/ffmpeg/bin/ffmpeg'
SELECTIONS = [
    ('AL07EJ17_Reassembly_A_002', 'combination_wrench', 'pick_up'),
    ('AL07EJ17_Reassembly_A_002', 'phillips_screwdriver', 'pick_up'),
    ('AL07EJ17_Reassembly_A_002', 'torx_screwdriver', 'pick_up'),
    ('AL07EJ17_Disassembly_B_005', 'flat_head_screwdriver', 'pick_up'),
    ('AL07EJ17_Reassembly_A_002', 'adapter_plate', 'mount'),
    ('AL07EJ17_Reassembly_A_002', 'bearing_plate', 'pick_up'),
    ('MA07LF04_Reassembly_B_005', 'adapter_plate', 'pick_up'),
    ('MA07LF04_Reassembly_B_005', 'bearing_plate', 'pick_up'),
]


def extract(row):
    destination = OUTPUT / row['image']
    if not destination.exists():
        subprocess.run([
            FFMPEG, '-nostdin', '-hide_banner', '-loglevel', 'error',
            '-threads', '1', '-ss', str(row['timestamp_s']), '-i', row['video'],
            '-frames:v', '1', '-threads', '1', '-q:v', '2', str(destination)
        ], check=True, timeout=60, capture_output=True)
    row['sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
    return row


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, '-version'], check=True, capture_output=True)
    rows = []
    for trial, noun, verb in SELECTIONS:
        for view in ['front', 'top']:
            path = ANNOTATIONS / 'TAS-B' / view / f'{trial}_{view}.json'
            data = json.loads(path.read_text())
            nouns = {x['id']: x['name'] for x in data['nouns']}
            verbs = {x['id']: x['name'] for x in data['verbs']}
            index, segment = next(
                (i, s) for i, s in enumerate(data['segments'])
                if nouns.get(s['noun']) == noun and verbs.get(s['verb']) == verb
                and s['phase'] == 'normal'
            )
            fps = data['meta_data']['fps']
            for offset in [0.0, 1.0]:
                timestamp = segment['end_frame'] / fps + offset
                rows.append({
                    'trial': trial, 'view': view, 'noun': noun, 'verb': verb,
                    'annotation': str(path.relative_to(ROOT)),
                    'annotation_pointer': f'/segments/{index}',
                    'annotation_segment': segment,
                    'timestamp_s': round(timestamp, 6),
                    'relation_to_segment': 'end' if offset == 0 else '1s_after_end_context',
                    'video': str(VIDEOS / view / f'{trial}_{view}.mp4'),
                    'image': f'{trial}_{view}_{noun}_{int(offset)}.jpg'
                })
    with ThreadPoolExecutor(max_workers=4) as pool:
        for view in ['front', 'top']:
            trial = 'KE03ER16_Disassembly_A_001'
            rows.append({
                'trial': trial, 'view': view, 'noun': None, 'verb': None,
                'timestamp_s': 0.0, 'relation_to_segment': 'model_marker_audit',
                'video': str(VIDEOS / view / f'{trial}_{view}.mp4'),
                'image': f'{trial}_{view}_model_audit.jpg'
            })
        rows = list(pool.map(extract, rows))
    (OUTPUT / 'visual_evidence.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    for view in ['front', 'top']:
        selected = [r for r in rows if r['view'] == view and r['relation_to_segment'] == '1s_after_end_context']
        sheet = Image.new('RGB', (1600, 1920), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, row in enumerate(selected):
            im = Image.open(OUTPUT / row['image']).convert('RGB')
            im.thumbnail((800, 450))
            x, y = i % 2 * 800, i // 2 * 480
            sheet.paste(im, (x, y))
            draw.text((x + 8, y + 452), f"{row['trial']} | {row['noun']} | {row['timestamp_s']:.2f}s", fill='black')
        sheet.save(OUTPUT / f'evidence_{view}.jpg', quality=94)
    print(json.dumps({'frames': len(rows), 'views': ['front', 'top'], 'output': str(OUTPUT)}))


if __name__ == '__main__':
    main()
