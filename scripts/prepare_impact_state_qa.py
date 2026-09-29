import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, FFMPEG, REPORTS, fingerprint, read_json, save_json, save_jsonl
from impact_qa.state_qa import STATE_OUT, make_packets, make_procedure, prepare_frames, profile_video


def clip(packet):
    target = packet['target']
    path = STATE_OUT / 'media' / packet['event_id'] / 'clip.mp4'
    config = {'source': packet['media_profile'], 'start_frame': target['start_frame'], 'end_frame': target['end_frame_inclusive'], 'width': 1024, 'codec': 'h264', 'crf': 20}
    manifest = path.parent / 'clip_config.json'
    if not path.exists() or not manifest.exists() or read_json(manifest) != config:
        subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-threads', '1', '-ss', str(target['start_s']), '-i', packet['media_profile']['path'], '-frames:v', str(target['end_frame_inclusive'] - target['start_frame'] + 1), '-vf', 'scale=1024:-2', '-an', '-c:v', 'libx264', '-threads', '1', '-preset', 'fast', '-crf', '20', '-movflags', '+faststart', '-y', str(path)], check=True, capture_output=True)
        save_json(manifest, config)
    packet['image_refs'].insert(0, {'evidence_id': 'video:' + packet['event_id'], 'media_type': 'video', 'path': str(path), 'source_start_s': target['start_s'], 'source_end_s': target['end_s_exclusive'], 'decoder_num_frames': 16, 'view': 'front'})
    packet['input_hash'] = fingerprint(packet)
    save_json(STATE_OUT / 'packets' / (packet['event_id'] + '.json'), packet)
    return packet


def main():
    procedure = make_procedure()
    save_json(STATE_OUT / 'procedure.json', procedure)
    paths = sorted((ANNOTATIONS / 'ASR/annotations').glob('*Reassembly_A*'))[:3]
    packets = []
    for path in paths:
        annotation = read_json(path)
        profile = profile_video(annotation['video_id'], annotation)
        packets.extend(make_packets(annotation['video_id'], procedure, profile))
        print(json.dumps({'profile': profile}), flush=True)
    prepare_frames(packets)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        packets = list(pool.map(clip, packets))
    for packet in packets:
        target = packet['target']
        assert target['start_frame'] < target['end_frame_inclusive'] < packet['media_profile']['decoded_frames']
        known = {r['id'] for r in packet['evidence_catalog']}
        assert target['end_state_source_id'] in known
        for comparison in packet['computed_comparisons']:
            assert all(s in known for s in comparison['source_ids']), (packet['event_id'], comparison)
    save_jsonl(STATE_OUT / 'packets.jsonl', packets)
    save_json(REPORTS / 'v10_input_first10.json', packets[:10])
    summaries = [{'event_id': p['event_id'], 'component': p['target']['component_id'], 'state_at_end': p['target']['state_at_end'], 'duration_s': p['target']['end_s_exclusive'] - p['target']['start_s'], 'anchor_count': len(p['image_refs']) - 1, 'end_frame': p['target']['end_frame_inclusive']} for p in packets]
    save_json(REPORTS / 'v10_input_summary.json', summaries)
    print(json.dumps(summaries, indent=2), flush=True)


if __name__ == '__main__':
    main()
