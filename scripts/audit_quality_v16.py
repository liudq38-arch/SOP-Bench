import argparse
import hashlib
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, fingerprint, read_json, read_jsonl, save_json, save_jsonl


def main(args):
    cases = {c['contract_id']: c for path in [OUT / 'quality_v16_inputs/contracts.jsonl', OUT / 'quality_v16_training_inputs/contracts.jsonl'] for c in read_jsonl(path)}
    folder = OUT / 'quality_v16_audit'
    folder.mkdir(exist_ok=True)
    records = []
    for name in args.batches:
        batch = OUT / name
        if (batch / 'results.jsonl').exists():
            records.extend({**r, 'batch': name} for r in read_jsonl(batch / 'results.jsonl'))
    if len({r['contract_id'] for r in records}) != len(records):
        raise ValueError('audit_v16:duplicate_events')
    passed = [r for r in records if r['disposition'] == 'model_passed_unvalidated']
    selected = sorted(passed, key=lambda r: (r['kind'] == 'tool_identity', fingerprint(r['contract_id'])))
    if len(selected) > 50:
        selected = selected[:50]
    save_jsonl(folder / 'sample_manifest.jsonl', [{'contract_id': r['contract_id'], 'batch': r['batch'], 'kind': r['kind'], 'selection': 'all if <=50, otherwise non-tool first then fixed hash'} for r in selected])
    cards = []
    for r in records:
        c = cases[r['contract_id']]
        g = r['stages'].get('generate', {})
        escape = lambda value: html.escape(str(value), quote=True)
        pictures = ''.join(f'<figure><figcaption>{escape(im["evidence_id"])} | {im["requested_time_s"]:.3f}s</figcaption><img loading="lazy" src="{escape(Path(im["path"]).relative_to(OUT))}"></figure>' for im in c['image_refs'])
        evidence = {'disposition': r['disposition'], 'GT_answer': c['canonical_answer'], 'generated_answer': g.get('answer'), 'options': c['options'], 'correct_option': c['correct_option'], 'stages': r['stages'], 'decision': r.get('decision'), 'error': r.get('error')}
        cards.append(f'<article id="{escape(c["contract_id"])}"><h2>{escape(c["contract_id"])} · {escape(c["kind"])}</h2><p>{escape(g.get("open_question", c["question"]))}</p><div class="frames">{pictures}</div><details><summary>展开参考答案与审核记录（先看图作答）</summary><pre>{escape(json.dumps(evidence,ensure_ascii=False,indent=2))}</pre></details></article>')
    page = '<!doctype html><meta charset="utf-8"><base href="../"><title>IMPACT v16 candidate audit</title><style>body{font-family:sans-serif;margin:24px}article{border-bottom:2px solid #888;margin-bottom:30px}.frames{display:flex;overflow-x:auto;gap:8px}figure{margin:0;min-width:480px}img{width:480px}pre{white-space:pre-wrap}summary{cursor:pointer}</style><h1>v16候选复查：先看图，后展开GT</h1><p>模型通过不代表人工金标准。按完整原时钟顺序显示输入帧，抽帧不能替代连续视频。</p>' + ''.join(cards)
    (folder / 'review.html').write_text(page)
    for r in selected:
        c = cases[r['contract_id']]
        ids = set()
        for ch in r['stages']['visual_audit']['claim_checks']:
            ids.update(ch['image_ids'])
        v = r['stages']['visual_audit']
        ids.update(i for i in [v['before_id'], v['after_id']] if i)
        images = [im for im in c['image_refs'] if im['evidence_id'] in ids]
        if len(images) > 8:
            indices = [round(i * (len(images) - 1) / 7) for i in range(8)]
            images = [images[i] for i in indices]
        width, height = 720, 450
        board = Image.new('RGB', (width * 2, height * ((len(images) + 1) // 2)), 'white')
        draw = ImageDraw.Draw(board)
        for j, im in enumerate(images):
            picture = ImageOps.contain(Image.open(im['path']), (width, height - 35))
            x, y = (j % 2) * width, (j // 2) * height
            board.paste(picture, (x, y + 35))
            draw.text((x + 8, y + 8), f'{c["contract_id"]} | {im["evidence_id"]} | {im["requested_time_s"]:.3f}s', fill='black')
        path = folder / 'boards' / (c['contract_id'] + '.jpg')
        path.parent.mkdir(exist_ok=True)
        board.save(path, quality=95)
    keys = {key for r in records for key in r['cache_keys'].values()}
    usages = [read_json(OUT / 'api_cache' / (key + '.json')) for key in keys]
    stages = defaultdict(list)
    for u in usages:
        stages[u['stage']].append(u)
    stats = {'processed_events': len(records), 'counts': dict(Counter(r['disposition'] for r in records)), 'selected_for_direct_review': len(selected), 'unique_successful_response_cache_keys': len(keys), 'not_http_attempt_count': True, 'prompt_tokens': sum(u.get('usage', {}).get('prompt_tokens', 0) for u in usages), 'completion_tokens': sum(u.get('usage', {}).get('completion_tokens', 0) for u in usages), 'stage_counts': {k: len(v) for k, v in stages.items()}, 'formal_release': False}
    save_json(REPORTS / 'quality_v16_production_stats.json', stats)
    print(stats)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--batches', nargs='+', default=['quality_v16_batch001', 'quality_v16_batch002'])
    main(parser.parse_args())
