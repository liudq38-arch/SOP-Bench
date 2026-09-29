import argparse
import html
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, read_jsonl, save_jsonl


def main(phase):
    source = OUT / ('gt_v14_acceptance_inputs' if phase == 'acceptance' else 'gt_v14_1_tools')
    folder = OUT / ('gt_v14_frozen_' + phase) / 'blind_review'
    folder.mkdir(parents=True, exist_ok=True)
    cases = read_jsonl(source / 'contracts.jsonl')
    index = [{'review_index': i, 'contract_id': c['contract_id'], 'question': c['question'], 'video_group': c['video_id'], 'image_refs': c['image_refs']} for i, c in enumerate(cases)]
    save_jsonl(folder / 'public_index.jsonl', index)
    cards = []
    for page in range((len(cases) + 2) // 3):
        board = Image.new('RGB', (2048, 1080), 'white')
        draw = ImageDraw.Draw(board)
        for row, c in enumerate(cases[page * 3:page * 3 + 3]):
            draw.text((5, row * 360 + 2), f'{page * 3 + row} {c["contract_id"]} {c["question"]}', fill='black')
            for column, slot in enumerate([0, 4, 11, 3]):
                im = c['image_refs'][slot]
                image = ImageOps.contain(Image.open(im['path']), (512, 324))
                draw.text((column * 512 + 5, row * 360 + 17), f'{im["evidence_id"]} {im["requested_time_s"]:.3f}s', fill='black')
                board.paste(image, (column * 512 + (512 - image.width) // 2, row * 360 + 34))
        board.save(folder / f'page_{page:02d}.jpg', quality=96)
    for i, c in enumerate(cases):
        media = ''.join('<figure><img loading="lazy" src="' + html.escape(os.path.relpath(im['path'], folder)) + '"><figcaption>' + html.escape(im['evidence_id'] + ' / ' + str(im['requested_time_s'])) + '</figcaption></figure>' for im in c['image_refs'])
        cards.append('<article><h2>' + str(i) + ' ' + html.escape(c['contract_id']) + '</h2><p>' + html.escape(c['question']) + '</p><div>' + media + '</div></article>')
    (folder / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>GT隐藏的实际输入复查</title><style>body{max-width:1400px;margin:auto}article div{display:flex;flex-wrap:wrap}figure{width:45%;margin:8px}img{width:100%}</style><h1>问题与实际评测输入；无GT和模型回答</h1>' + ''.join(cards))
    print(json.dumps({'phase': phase, 'events': len(cases), 'overview_pages': (len(cases) + 2) // 3}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['development', 'acceptance'], required=True)
    main(parser.parse_args().phase)
