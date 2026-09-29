import hashlib
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, fingerprint, read_json, read_jsonl, save_json, save_jsonl


def main():
    batch = OUT / 'evidence_v18_batch'
    folder = OUT / 'evidence_v18_review'
    records = [read_json(p) for p in (batch / 'runs').glob('*.json')]
    records = [r for r in records if r['status'] != 'running']
    packages = {p['contract_id']: p for p in read_jsonl(OUT / 'evidence_v18_inputs/packages.jsonl')}
    cases = {c['contract_id']: c for name in ['quality_v16_inputs', 'quality_v16_training_inputs'] for c in read_jsonl(OUT / name / 'contracts.jsonl')}
    selected = [r for r in records if r['status'] == 'evidence_screened_unvalidated']
    selected.sort(key=lambda r: (cases[r['contract_id']].get('hand') != 'left', cases[r['contract_id']].get('tool') != 'wrench', fingerprint(r['contract_id'])))
    selected = selected[:50]
    folder.mkdir(exist_ok=True)
    save_jsonl(folder / 'sample_manifest.jsonl', [{'contract_id': r['contract_id'], 'selection': 'all screened if <=50; otherwise left hand then wrench then fixed hash', 'status': 'selected_not_yet_directly_reviewed'} for r in selected])
    cards = []
    escape = lambda value: html.escape(str(value), quote=True)
    for r in sorted(records, key=lambda r: (r['status'] != 'evidence_screened_unvalidated', r['kind'], r['contract_id'])):
        p, c = packages[r['contract_id']], cases[r['contract_id']]
        g = r['stages'].get('generate', {})
        picture_refs = p['target_visual']['images'] + p['public_reference']['action_examples']
        pictures = ''.join(f'<figure><figcaption>{escape(im["evidence_id"])} | {im["requested_time_s"]:.3f}s</figcaption><img loading="lazy" src="{escape(Path(im["path"]).relative_to(OUT))}"></figure>' for im in picture_refs)
        details = {'GT_answer': c['canonical_answer'], 'generated_answer': g.get('answer'), 'options': c['options'], 'correct_option': c['correct_option'], 'audit': r}
        cards.append(f'<article id="{escape(r["contract_id"])}"><h2>{escape(r["contract_id"])} · {escape(r["kind"])}</h2><p>{escape(g.get("open_question", c["question"]))}</p><div class="frames">{pictures}</div><details><summary>展开GT和模型审核（建议先看画面）</summary><pre>{escape(json.dumps(details,ensure_ascii=False,indent=2))}</pre></details></article>')
    page = '<!doctype html><meta charset="utf-8"><base href="../"><title>IMPACT v18 evidence review</title><style>body{font-family:sans-serif;margin:24px}article{border-bottom:2px solid #888;margin-bottom:30px}.frames{display:flex;overflow-x:auto;gap:8px}figure{margin:0;min-width:480px}img{width:480px}pre{white-space:pre-wrap}summary{cursor:pointer}</style><h1>v18候选复查</h1><p>抽帧及训练动作参考；模型筛选结果，非真人金标准。状态暂隐藏于展开记录。</p>' + ''.join(cards)
    (folder / 'review.html').write_text(page)
    for r in selected:
        destination = folder / 'boards' / (r['contract_id'] + '.jpg')
        if destination.exists():
            continue
        destination.parent.mkdir(exist_ok=True)
        p = packages[r['contract_id']]
        by_id = {im['evidence_id']: im for im in p['target_visual']['images']}
        pair = r['stages']['pair']['review']
        chosen = [by_id[pair['before_image_id']], by_id[pair['after_image_id']]]
        board = Image.new('RGB', (1920, 610), 'white')
        draw = ImageDraw.Draw(board)
        for j, im in enumerate(chosen):
            picture = ImageOps.contain(Image.open(im['path']), (960, 560))
            board.paste(picture, (j * 960, 50))
            draw.text((j * 960 + 8, 8), r['contract_id'], fill='black')
            draw.text((j * 960 + 8, 28), f'{im["evidence_id"]} | {im["requested_time_s"]:.3f}s', fill='black')
        board.save(destination, quality=96)
    reasons = Counter(reason for r in records for reason in r.get('decision', {}).get('reasons', []))
    needs = Counter(need for r in records for need in r['stages'].get('qualify', {}).get('needs', []) if need != 'none')
    keys = {key for r in records for key in r['cache_keys'].values()}
    usages = [read_json(OUT / 'api_cache' / (key + '.json')) for key in keys]
    stats = {'completed_events': len(records), 'input_events': len(packages), 'complete': len(records) == len(packages), 'counts': dict(Counter(r['status'] for r in records)), 'evidence_needs': dict(needs), 'semantic_rejection_reasons': dict(reasons), 'schema_errors': dict(Counter(r.get('error') for r in records if r['status'] == 'schema_rejected')), 'unique_response_cache_keys': len(keys), 'prompt_tokens_including_reused_responses': sum(u.get('usage', {}).get('prompt_tokens', 0) for u in usages), 'completion_tokens_including_reused_responses': sum(u.get('usage', {}).get('completion_tokens', 0) for u in usages), 'selected_for_direct_review': len(selected), 'selection_is_not_review_completion': True, 'formal_release': False}
    save_json(REPORTS / 'evidence_v18_analysis.json', stats)
    print(stats)


if __name__ == '__main__':
    main()
