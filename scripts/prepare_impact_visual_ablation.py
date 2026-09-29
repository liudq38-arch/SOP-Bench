import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.visual_ablation import CONDITIONS, FOLDER, ROI, evidence, frame_path, indices, manual_refs, render, select


def main():
    contracts = select()
    FOLDER.mkdir(exist_ok=True)
    manifest = {'contract_ids': [c['contract_id'] for c in contracts], 'kinds': dict(Counter(c['kind'] for c in contracts)), 'roi_xyxy': ROI, 'target_canvas': [640, 448], 'context_canvas': [512, 288], 'conditions': CONDITIONS, 'question_and_gt_fixed': True, 'reserve_used': False}
    if (FOLDER / 'selection.json').exists():
        assert read_json(FOLDER / 'selection.json') == {**manifest, 'roi_xyxy': list(ROI)}
    save_json(FOLDER / 'selection.json', manifest)
    by_video = defaultdict(list)
    for c in contracts:
        by_video[c['video_id']].append(c)
    for video, cases in by_video.items():
        wanted = set()
        for c in cases:
            wanted.update(indices(c))
            wanted.update(indices(c, True))
            wanted.update(np.linspace(c['start_frame'], c['end_frame_inclusive'], 4).round().astype(int).tolist())
        missing = {n for n in wanted if not all(frame_path(video, n, variant).exists() for variant in ['full', 'crop', 'context'])}
        if missing:
            with av.open(cases[0]['source_video']) as container:
                stream = container.streams.video[0]
                stream.thread_type = 'AUTO'
                for n, frame in enumerate(container.decode(video=0)):
                    if n in missing:
                        assert abs(float(frame.pts * frame.time_base) - n / 30) < 1e-5
                        im = frame.to_image()
                        for variant in ['full', 'crop', 'context']:
                            path = frame_path(video, n, variant)
                            path.parent.mkdir(parents=True, exist_ok=True)
                            result = ImageOps.pad(im, (512, 288), color='white') if variant == 'context' else render(im, variant == 'crop')
                            result.save(path, quality=95)
                    if n >= max(missing):
                        break
        print({'prepared_video': video, 'source_frames': len(wanted)}, flush=True)
    references = manual_refs()
    questions = {r['contract_id']: r for r in read_jsonl(OUT / 'gt_v12_final/open_candidates.jsonl')}
    rows, hashes = [], {}
    for c in contracts:
        sheets = {}
        for condition in CONDITIONS:
            refs = evidence(c, condition, references)
            for im in refs:
                if im.get('view') == 'front':
                    assert c['start_frame'] <= im['frame_index'] <= c['end_frame_inclusive']
                if im['path'] not in hashes:
                    hashes[im['path']] = hashlib.sha256(Path(im['path']).read_bytes()).hexdigest()
                im['sha256'] = hashes[im['path']]
            sheet_path = FOLDER / 'sheets' / (c['contract_id'] + '_' + condition + '.jpg')
            sheet_path.parent.mkdir(exist_ok=True)
            board = Image.new('RGB', (1600, 1220), 'white')
            draw = ImageDraw.Draw(board)
            for i, imref in enumerate(refs[:20]):
                im = ImageOps.contain(Image.open(imref['path']), (400, 220))
                x, y = i % 4 * 400, i // 4 * 244
                draw.text((x + 3, y + 3), f'{imref["evidence_id"]} | {imref["requested_time_s"]:.3f}s', fill='black')
                board.paste(im, (x + (400 - im.width) // 2, y + 22))
            board.save(sheet_path, quality=93)
            sheets[condition] = str(sheet_path)
            row = {'contract_id': c['contract_id'], 'condition': condition, 'video_id': c['video_id'], 'kind': c['kind'], 'selection_reason': c['selection_reason'], 'question': questions[c['contract_id']]['question'], 'gt_answer': questions[c['contract_id']]['answer'], 'answer_polarity': c['answer_polarity'], 'public_procedure': c['public_procedure'], 'start_frame': c['start_frame'], 'end_frame_inclusive': c['end_frame_inclusive'], 'image_refs': refs, 'contact_sheet': str(sheet_path), 'facts': c['facts']}
            row['input_hash'] = fingerprint(row)
            rows.append(row)
    save_jsonl(FOLDER / 'cases.jsonl', rows)
    save_jsonl(FOLDER / 'first10.jsonl', rows[:10])
    save_json(FOLDER / 'media_hashes.json', hashes)
    save_json(REPORTS / 'gt_v13_input_validation.json', {'contracts': len(contracts), 'conditions': len(CONDITIONS), 'cases': len(rows), 'media_assets': len(hashes), 'source_frame_times_verified': True, 'no_future_frames': True, 'target_images': 16, 'context_images': 4, 'manual_reference_images': 2, 'kinds': manifest['kinds']})
    print({'contracts': len(contracts), 'cases': len(rows), 'media_assets': len(hashes)}, flush=True)


if __name__ == '__main__':
    main()
