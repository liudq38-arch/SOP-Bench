import concurrent.futures
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import av
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, read_json, read_jsonl, save_json


DEST = REPORTS / 'state_v10_2_independent_audit'


def sheet(paths, output, columns, cell=(460, 340)):
    board = Image.new('RGB', (columns * cell[0], ((len(paths) + columns - 1) // columns) * cell[1]), 'white')
    draw = ImageDraw.Draw(board)
    for i, (index, path) in enumerate(paths):
        im = Image.open(path).convert('RGB')
        im.thumbnail((cell[0], cell[1] - 25))
        x, y = i % columns * cell[0], i // columns * cell[1]
        board.paste(im, (x, y + 25))
        draw.text((x + 4, y + 4), f'frame {index} | original {index / 30:.3f} s', fill='black')
    board.save(output, quality=94)


def extract(video, packets):
    source = Path(packets[0]['media_profile']['path'])
    folder = DEST / video
    folder.mkdir(parents=True, exist_ok=True)
    total = packets[0]['media_profile']['decoded_frames']
    overview = sorted(set(list(range(0, total, 150)) + [total - 1]))
    ends = {p['event_id']: sorted(set(max(p['target']['start_frame'], p['target']['end_frame_inclusive'] - offset) for offset in [180, 150, 120, 90, 60, 30, 15, 0])) for p in packets}
    frames = sorted(set(overview).union(*(set(x) for x in ends.values())))
    required = {i for i in frames if not (folder / f'{i:06d}.jpg').exists()}
    if required:
        with av.open(str(source)) as container:
            container.streams.video[0].thread_type = 'AUTO'
            for index, frame in enumerate(container.decode(video=0)):
                if index in required:
                    assert abs(float(frame.pts * frame.time_base) - index / 30) < 1e-5
                    frame.to_image().crop((400, 330, 850, 640)).save(folder / f'{index:06d}.jpg', quality=95)
                if index >= max(required):
                    break
    boards = []
    for start in range(0, len(overview), 12):
        path = folder / f'overview_{start // 12:02d}.jpg'
        sheet([(i, folder / f'{i:06d}.jpg') for i in overview[start:start + 12]], path, 3)
        boards.append({'path': str(path), 'kind': 'whole_recording_5s_overview', 'frames': overview[start:start + 12]})
    for event, indices in ends.items():
        path = folder / (event.rsplit('__', 1)[-1] + '_last6s.jpg')
        sheet([(i, folder / f'{i:06d}.jpg') for i in indices], path, 4)
        boards.append({'path': str(path), 'event_id': event, 'kind': 'target_last6s', 'frames': indices})
    result = {'video_id': video, 'source_video': str(source), 'crop_xyxy': [400, 330, 850, 640], 'selected_distinct_frames': len(frames), 'boards': boards, 'inspection_note': 'These are timestamped still frames, not continuous video playback.'}
    print(json.dumps({'video': video, 'frames': len(frames), 'boards': len(boards)}), flush=True)
    return result


def main():
    packets = read_jsonl(OUT / 'state_qa_inputs_v10_1/packets.jsonl')
    groups = defaultdict(list)
    for p in packets:
        groups[p['target']['video_id']].append(p)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        manifests = list(pool.map(lambda item: extract(*item), groups.items()))
    save_json(DEST / 'frame_manifest.json', manifests)
    questions = read_jsonl(OUT / 'state_v10_2/agent_reviewed_candidates.jsonl')
    mcq = read_jsonl(OUT / 'state_v10_2/state_mcq_candidates.jsonl')
    source_checks = []
    for q in questions:
        for fact in q['state_assertions']:
            video = q['event_id'].split('__')[0]
            a = read_json(ANNOTATIONS / 'ASR/annotations' / (video + '_asr.json'))
            si = max(i for i, row in enumerate(a['state_sequence']) if row['frame'] <= fact['at_frame'])
            ci = next(i for i, c in enumerate(a['components']) if c['name'] == fact['component_id'])
            actual = a['state_sequence'][si]['state'][ci]
            assert actual == fact['state']
            source_checks.append({'qa_id': q['qa_id'], 'component': fact['component_id'], 'frame': fact['at_frame'], 'state': actual})
    boundary = []
    for packet in packets:
        video, target = packet['target']['video_id'], packet['target']
        a = read_json(ANNOTATIONS / 'TAS-S/front' / (video + '.json'))
        b = read_json(ANNOTATIONS / 'TAS-B/front' / (video + '.json'))
        end = target['end_frame_inclusive']
        labels = {r['id']: r['name'] for r in b['action_labels']}
        active_coarse = [s for s in a['segments'] if s['f_start'] <= end <= s['f_end']]
        active_hands = [dict(s, action_name=labels[s['action_label']]) for s in b['segments'] if s['start_frame'] <= end <= s['end_frame']]
        boundary.append({'event_id': packet['event_id'], 'end_frame': end, 'asr_state': target['state_at_end'], 'coarse_at_end': active_coarse, 'hands_at_end': active_hands})
    duplicates = defaultdict(list)
    for q in questions:
        key = (q['event_id'].split('__')[0], q['type'], json.dumps(q['state_assertions'], sort_keys=True))
        duplicates[key].append(q['qa_id'])
    result = {'open_count': len(questions), 'open_unique_questions': len({q['question'] for q in questions}), 'open_types': dict(Counter(q['type'] for q in questions)), 'open_polarity': dict(Counter(q['answer_polarity'] for q in questions)), 'always_yes_binary_polarity_baseline': sum(q['answer_polarity'] == 'yes' for q in questions) / len(questions), 'reference_order_yes': sum(q['type'] == 'reference_order' and q['answer_polarity'] == 'yes' for q in questions), 'reference_order_total': sum(q['type'] == 'reference_order' for q in questions), 'mcq_count': len(mcq), 'mcq_states': dict(Counter(q['source_state'] for q in mcq)), 'always_select_correctly_installed_mcq_baseline': sum(q['source_state'] == 1 for q in mcq) / len(mcq), 'same_trial_type_and_state_assertion_duplicates': [ids for ids in duplicates.values() if len(ids) > 1], 'source_state_checks': source_checks, 'endpoint_source_labels': boundary, 'baseline_note': 'Deterministic label-distribution baselines, not an evaluated VLM accuracy; binary polarity does not score open-answer explanations.'}
    save_json(DEST / 'objective_checks.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['source_state_checks', 'endpoint_source_labels']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
