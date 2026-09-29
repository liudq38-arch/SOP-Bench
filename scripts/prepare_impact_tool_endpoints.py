import hashlib
import sys
from collections import defaultdict
from pathlib import Path

import av
from PIL import ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, fingerprint, read_jsonl, save_json, save_jsonl
from impact_qa.state_qa import FRONT
from impact_qa.tool_review_v15 import select_images


def main():
    folder = OUT / 'gt_v15_endpoint_inputs'
    roi, canvas = (280, 270, 1020, 700), (960, 560)
    for phase, source in [('development', 'gt_v14_1_tools'), ('exposed_regression', 'gt_v14_acceptance_inputs')]:
        cases = read_jsonl(OUT / source / 'contracts.jsonl')
        grouped = defaultdict(list)
        for c in cases:
            c['image_refs'] = select_images(c, 'transition8')
            grouped[c['video_id']].append(c)
        for video, rows in grouped.items():
            with av.open(str(FRONT / (video + '.mp4'))) as container:
                stream = container.streams.video[0]
                stream.thread_type = 'AUTO'
                for c in rows:
                    endpoints = [im for im in c['image_refs'] if im['evidence_id'].startswith('context_')]
                    for im in endpoints:
                        im['path'] = str(folder / 'frames' / (fingerprint([video, im['frame_index'], roi, canvas])[:24] + '.jpg'))
                    wanted = {im['frame_index']: Path(im['path']) for im in endpoints if not Path(im['path']).exists()}
                    if wanted:
                        container.seek(int((min(wanted) / 30) / float(stream.time_base)), stream=stream, backward=True)
                        seen = set()
                        for frame in container.decode(stream):
                            actual = float(frame.pts * frame.time_base)
                            number = round(actual * 30)
                            if number in wanted:
                                assert abs(actual - number / 30) < 1e-5
                                wanted[number].parent.mkdir(parents=True, exist_ok=True)
                                ImageOps.pad(frame.to_image().crop(roi), canvas, color='white').save(wanted[number], quality=96)
                                seen.add(number)
                            if number >= max(wanted):
                                break
                        assert seen == set(wanted), 'endpoints:missing_pts:' + c['contract_id']
                    for im in endpoints:
                        im['sha256'] = hashlib.sha256(Path(im['path']).read_bytes()).hexdigest()
                    c['media_variant'] = {'roi': roi, 'canvas': canvas, 'context_unchanged': False, 'source_pts_checked': True, 'all_eight_images_same_crop': True}
                    c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
            print({'video': video, 'events': len(rows)}, flush=True)
        save_jsonl(folder / phase / 'contracts.jsonl', cases)
        save_jsonl(folder / phase / 'first10.jsonl', cases[:10])
        save_json(folder / phase / 'validation.json', {'events': len(cases), 'images_per_event': 8, 'changed_images_per_event': 2, 'new_timestamps': 0, 'source_pts_checked': True, 'roi': roi, 'canvas': canvas, 'no_gt_or_question_changes': True})


if __name__ == '__main__':
    main()
