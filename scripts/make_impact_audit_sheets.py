import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['development', 'pilot'], required=True)
    parser.add_argument('--selection')
    args = parser.parse_args()
    events = read_jsonl(OUT / f'{args.split}_events.jsonl')
    selected = set(read_json(args.selection)['event_ids']) if args.selection else {e['event_id'] for e in events}
    folder = REPORTS / 'visual_audit'
    folder.mkdir(exist_ok=True)
    written = []
    for i, event in enumerate(events):
        if event['event_id'] not in selected:
            continue
        manifest = OUT / 'evidence' / event['event_id'] / 'focus/manifest.json'
        if not manifest.exists():
            continue
        frames = read_json(manifest)['images']
        full = [f for f in frames if 'full' in f['evidence_id']]
        crops = [f for f in frames if 'crop' in f['evidence_id']]
        canvas = Image.new('RGB', (1152, 4 * 240 + 2 * 290), 'white')
        draw = ImageDraw.Draw(canvas)
        for j, frame in enumerate(full):
            pic = Image.open(frame['path'])
            pic.thumbnail((384, 216))
            x, y = j % 3 * 384, j // 3 * 240
            canvas.paste(pic, (x, y))
            draw.text((x + 3, y + 218), f"{frame['evidence_id']} {frame['requested_time_s']:.3f}s", fill='black')
        for j, frame in enumerate(crops):
            pic = Image.open(frame['path'])
            pic.thumbnail((576, 266))
            x, y = j % 2 * 576, 960 + j // 2 * 290
            canvas.paste(pic, (x, y))
            draw.text((x + 3, y + 268), f"{frame['evidence_id']} {frame['requested_time_s']:.3f}s", fill='black')
        output = folder / f'{args.split}_{i:02d}_focus.jpg'
        canvas.save(output)
        written.append({'index': i, 'event_id': event['event_id'], 'sheet': str(output)})
    print(json.dumps(written, indent=2))


if __name__ == '__main__':
    main()
