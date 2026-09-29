import hashlib
import sys
from collections import Counter
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, fingerprint, read_json, save_json, save_jsonl
from impact_qa.gt_qa import reference, verify_reference
from impact_qa.state_qa import FRONT
from impact_qa.visual_ablation import ROI, render


FOLDER = OUT / 'gt_v14_tool_inputs'


def main(videos=None, folder=None, report_path=None):
    folder = folder or FOLDER
    split = read_json(OUT / 'gt_v12_split_manifest.json')
    rows, excluded, hashes = [], [], {}
    for video in videos if videos is not None else split['development']:
        path = ANNOTATIONS / 'TAS-B/front' / (video + '.json')
        data = read_json(path)
        names = {r['id']: (i, r['name']) for i, r in enumerate(data['action_labels'])}
        total = read_json(ANNOTATIONS / 'ASR/annotations' / (video + '_asr.json'))['frame_count']
        local = []
        for i, seg in enumerate(data['segments']):
            li, label = names[seg['action_label']]
            if not label.startswith('pick_up_') or not any(w in label for w in ['wrench', 'screwdriver']):
                continue
            if seg['phase'] != 'normal' or seg['end_frame'] - seg['start_frame'] < 15:
                excluded.append({'video_id': video, 'source_segment_index': i, 'reason': 'not_normal_or_under_15_frames'})
                continue
            tool = 'wrench' if 'wrench' in label else 'screwdriver'
            start, end = max(0, seg['start_frame'] - 15), min(total - 1, seg['end_frame'] + 14)
            identifier = 'tool_' + fingerprint([video, i, seg])[:20]
            refs = [reference(path, f'/segments/{i}'), reference(path, f'/action_labels/{li}')]
            for ref in refs:
                verify_reference(ref)
            choices = ['A screwdriver.', 'A wrench.', 'A pair of pliers.']
            choices.sort(key=lambda x: fingerprint([identifier, x]))
            target = np.linspace(seg['start_frame'], seg['end_frame'] - 1, 16).round().astype(int).tolist()
            context = np.linspace(start, end, 4).round().astype(int).tolist()
            c = {'contract_id': identifier, 'video_id': video, 'participant': video.split('_')[0], 'kind': 'tool_identity', 'source_segment_index': i, 'source_label': label, 'tool': tool, 'hand': seg['entity'], 'start_frame': start, 'end_frame_inclusive': end, 'target_interval_exclusive': [seg['start_frame'], seg['end_frame']], 'question': f'Which tool did I pick up with my {seg["entity"]} hand in this clip?', 'canonical_answer': f'I picked up a {tool} with my {seg["entity"]} hand.', 'references': refs, 'options': choices, 'correct_option': choices.index(f'A {tool}.')}
            c['image_refs'] = [{'evidence_id': f'{variant}_{j}', 'frame_index': n, 'requested_time_s': n / 30, 'view': 'front', 'time_scope': 'Original recording seconds. Same target execution, no action labels.', 'path': str(folder / 'frames' / (fingerprint([video, n, variant, ROI])[:24] + '.jpg'))} for variant, nums in [('context', context), ('target', target)] for j, n in enumerate(nums)]
            local.append(c)
        wanted = {}
        for c in local:
            for im in c['image_refs']:
                wanted.setdefault(im['frame_index'], {})[im['path']] = im['evidence_id'].startswith('context')
        missing = {n: paths for n, paths in wanted.items() if any(not Path(p).exists() for p in paths)}
        if missing:
            seen = set()
            with av.open(str(FRONT / (video + '.mp4'))) as container:
                container.streams.video[0].thread_type = 'AUTO'
                for n, frame in enumerate(container.decode(video=0)):
                    if n in missing:
                        assert abs(float(frame.pts * frame.time_base) - n / 30) < 1e-5
                        image = frame.to_image()
                        for p, context in missing[n].items():
                            destination = Path(p)
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            (ImageOps.pad(image, (512, 288), color='white') if context else render(image, True)).save(destination, quality=95)
                        seen.add(n)
                    if n >= max(missing):
                        break
            assert seen == set(missing), 'tool_prepare:missing_frames:' + video
        for c in local:
            board = Image.new('RGB', (1600, 1220), 'white')
            draw = ImageDraw.Draw(board)
            for j, im in enumerate(c['image_refs']):
                assert c['start_frame'] <= im['frame_index'] <= c['end_frame_inclusive']
                digest = hashes.setdefault(im['path'], hashlib.sha256(Path(im['path']).read_bytes()).hexdigest())
                im['sha256'] = digest
                image = ImageOps.contain(Image.open(im['path']), (400, 220))
                x, y = j % 4 * 400, j // 4 * 244
                draw.text((x + 3, y + 3), f'{im["evidence_id"]} | {im["requested_time_s"]:.3f}s', fill='black')
                board.paste(image, (x + (400 - image.width) // 2, y + 22))
            c['contact_sheet'] = str(folder / 'sheets' / (c['contract_id'] + '.jpg'))
            Path(c['contact_sheet']).parent.mkdir(exist_ok=True)
            board.save(c['contact_sheet'], quality=93)
            c['input_hash'] = fingerprint(c)
        rows += local
        print({'video': video, 'events': len(local), 'frames': len(wanted)}, flush=True)
    assert len({r['contract_id'] for r in rows}) == len(rows)
    save_jsonl(folder / 'contracts.jsonl', rows)
    save_jsonl(folder / 'first10.jsonl', rows[:10])
    save_jsonl(folder / 'excluded.jsonl', excluded)
    save_json(folder / 'media_hashes.json', hashes)
    save_json(report_path or REPORTS / 'gt_v14_tool_input_validation.json', {'events': len(rows), 'trials': len({r['video_id'] for r in rows}), 'participants': len({r['participant'] for r in rows}), 'tool_counts': dict(Counter(r['tool'] for r in rows)), 'hand_counts': dict(Counter(r['hand'] for r in rows)), 'excluded': len(excluded), 'media_hashes': len(hashes), 'source_references_checked': 2 * len(rows), 'reserve_used': bool({r['video_id'] for r in rows} & set(split['unexposed_reserve'])), 'all_eligible_requested_pickups': True, 'roi_xyxy': ROI, 'sampling': '4 context +16 target, target end exclusive', 'source_frame_times_verified': True})
    return rows


if __name__ == '__main__':
    main()
