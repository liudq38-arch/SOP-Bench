import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, fingerprint, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import build_contracts


def main():
    contracts = build_contracts(read_jsonl(OUT / 'state_qa_inputs_v10_1/packets.jsonl'))
    folder = OUT / 'gt_v11_inputs'
    groups = defaultdict(list)
    for c in contracts:
        groups[c['video_id']].append(c)
    for video, items in groups.items():
        required = {}
        for c in items:
            indices = set(np.linspace(c['start_frame'], c['end_frame_inclusive'], 12).round().astype(int).tolist())
            for ref in c['references']:
                value = ref['value']
                if isinstance(value, dict):
                    for key in ['f_start', 'f_end', 'start_frame', 'end_frame', 'frame']:
                        n = value.get(key)
                        if isinstance(n, int) and c['start_frame'] <= n <= c['end_frame_inclusive']:
                            indices.add(n)
            c['frame_indices'] = sorted(indices)
            for n in indices:
                path = folder / 'frames' / (fingerprint({'video': video, 'frame': n})[:24] + '.jpg')
                required[n] = path
        missing = {n: p for n, p in required.items() if not p.exists()}
        if missing:
            with av.open(items[0]['source_video']) as container:
                container.streams.video[0].thread_type = 'AUTO'
                for n, frame in enumerate(container.decode(video=0)):
                    if n in missing:
                        assert abs(float(frame.pts * frame.time_base) - n / 30) < 1e-5
                        missing[n].parent.mkdir(parents=True, exist_ok=True)
                        frame.to_image().save(missing[n], quality=94)
                    if n >= max(missing):
                        break
        for c in items:
            c['image_refs'] = [{'evidence_id': f'frame_{n}', 'frame_index': n, 'path': str(required[n]), 'requested_time_s': n / 30, 'view': 'front original 1280x720', 'time_scope': 'within target clip; no future frames'} for n in c['frame_indices']]
            board = Image.new('RGB', (1800, ((len(c['frame_indices']) + 3) // 4) * 340), 'white')
            draw = ImageDraw.Draw(board)
            for j, n in enumerate(c['frame_indices']):
                im = Image.open(required[n]).crop((400, 330, 850, 640))
                x, y = (j % 4) * 450, (j // 4) * 340
                board.paste(im, (x, y + 25))
                draw.text((x + 3, y + 3), f'frame {n} | {n / 30:.3f}s', fill='black')
            c['contact_sheet'] = str(folder / (c['contract_id'] + '.jpg'))
            board.save(c['contact_sheet'], quality=94)
            c['input_hash'] = fingerprint(c)
        print(json.dumps({'video': video, 'contracts': len(items), 'distinct_frames': len(required)}), flush=True)
    save_jsonl(folder / 'contracts.jsonl', contracts)
    save_jsonl(folder / 'first10.jsonl', contracts[:10])
    summary = {'contracts': len(contracts), 'types': dict(Counter(c['kind'] for c in contracts)), 'open_polarity': dict(Counter(c['answer_polarity'] for c in contracts)), 'source_references_verified': sum(len(c['references']) for c in contracts), 'unique_fact_keys': len({fingerprint([c['video_id'], c['kind'], c['facts']]) for c in contracts}), 'frames_per_question': [len(c['frame_indices']) for c in contracts], 'frame_evidence_only': True, 'no_model_requests': True}
    save_json(REPORTS / 'gt_v11_input_validation.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
