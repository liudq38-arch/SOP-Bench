import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import FFMPEG, ROOT, read_jsonl, save_json
from impact_qa.descriptive_v21 import digest


FOLDER = ROOT / 'outputs/impact_qa/history_v23'


def prepare(record):
    case = record['case']
    destination = FOLDER / 'review_media' / (case['case_id'] + '.mp4')
    destination.parent.mkdir(parents=True, exist_ok=True)
    start, end = case['source_interval_inclusive']
    if not destination.exists():
        tmp = destination.with_suffix('.tmp.mp4')
        subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', case['source_video'], '-vf', f'select=between(n\\,{start}\\,{end}),setpts=PTS-STARTPTS,scale=960:-2', '-frames:v', str(end - start + 1), '-an', '-fps_mode', 'vfr', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(tmp)], check=True, capture_output=True, timeout=240)
        tmp.replace(destination)
    with av.open(destination) as video:
        pts = [float(f.pts * f.time_base) for f in video.decode(video=0)]
    expected = record['frames']
    if len(pts) != len(expected):
        raise ValueError('history_review:frame_count')
    error = max(abs(t - (f['source_pts_s'] - expected[0]['source_pts_s'])) for t, f in zip(pts, expected))
    if error > .002:
        raise ValueError('history_review:pts_mapping')
    return {'case_id': case['case_id'], 'path': str(destination), 'source_start_pts_s': expected[0]['source_pts_s'], 'frames': len(pts), 'max_pts_error_s': error, 'sha256': digest(destination)}


def main():
    records = [r for r in read_jsonl(ROOT / 'outputs/impact_qa/descriptive_v21/cases.jsonl') if r['case']['pair_id'] == 'atr_403f880f747b22eb']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(prepare, records))
    save_json(FOLDER / 'review_media.json', results)
    print(json.dumps(results), flush=True)


if __name__ == '__main__':
    main()
