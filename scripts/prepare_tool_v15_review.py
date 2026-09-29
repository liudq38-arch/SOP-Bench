import argparse
import html
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, read_jsonl, save_jsonl


def main(condition, phase, label):
    folder = OUT / 'gt_v15_tools' / condition / phase
    rows = read_jsonl(folder / (label + '_results.jsonl'))
    destination = folder / (label + '_review')
    destination.mkdir(parents=True, exist_ok=True)
    cards, index = [], []
    for i, r in enumerate(rows):
        images = r['image_refs']
        board = Image.new('RGB', (1920, 320 * ((len(images) + 3) // 4)), 'white')
        draw = ImageDraw.Draw(board)
        figures = []
        for j, ref in enumerate(images):
            x, y = j % 4 * 480, j // 4 * 320
            draw.text((x + 3, y + 3), ref['evidence_id'] + ' ' + str(ref['requested_time_s']), fill='black')
            picture = ImageOps.contain(Image.open(ref['path']), (480, 290))
            board.paste(picture, (x + (480 - picture.width) // 2, y + 25))
            figures.append('<figure><img loading="lazy" src="' + html.escape(os.path.relpath(ref['path'], destination)) + '"><figcaption>' + html.escape(ref['evidence_id'] + ' ' + str(ref['requested_time_s'])) + '</figcaption></figure>')
        path = destination / (r['contract_id'] + '.jpg')
        board.save(path, quality=96)
        index.append({'index': i, 'contract_id': r['contract_id'], 'image_board': str(path), 'question': r['generation']['question']})
        cards.append('<article><h2>' + html.escape(str(i) + ' ' + r['contract_id']) + '</h2><p>' + html.escape(r['generation']['question']) + '</p><div>' + ''.join(figures) + '</div></article>')
    save_jsonl(destination / 'public_index.jsonl', index)
    (destination / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>v15 evidence review</title><style>body{max-width:1500px;margin:auto}article div{display:flex;flex-wrap:wrap}figure{width:45%;margin:8px}img{width:100%}</style><h1>Question and actual input images; GT and model answers hidden</h1>' + ''.join(cards))
    print({'events': len(rows), 'folder': str(destination)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--condition', required=True, choices=['chronological20', 'transition8', 'endpoint8', 'inventory8'])
    parser.add_argument('--phase', required=True, choices=['development', 'exposed_regression'])
    parser.add_argument('--label', default='full', choices=['smoke', 'full'])
    args = parser.parse_args()
    main(args.condition, args.phase, args.label)
