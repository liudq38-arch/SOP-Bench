import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio
import imageio_ffmpeg

from impact_qa.human_review import REVIEW, ROOT, VIDEOS, ReviewData, ReviewStore


def main():
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, '-version'], check=True, capture_output=True)
    data = ReviewData()
    if len(data.rows) != 161 or len(data.by_id) != 161:
        raise ValueError('review_precheck:unexpected_event_count')
    first = []
    for row in data.rows:
        cid = row['contract_id']
        start, end, _, _ = data.timing(cid)
        if not (VIDEOS / (row['video_id'] + '.mp4')).is_file() or not end > start >= 0:
            raise ValueError('review_precheck:video_or_time:' + cid)
        first.append({'contract_id': cid, 'video_id': row['video_id'], 'start_s': start, 'end_exclusive_s': end, 'question': row['open_question'], 'answer': row['generated_answer']})
    (REVIEW / 'first10.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in first[:10]))
    with tempfile.TemporaryDirectory() as directory:
        store = ReviewStore(directory)
        store.save(data.rows[0], 'isolated_preflight', '通过', '', 'test')
        store.save(data.rows[0], 'isolated_preflight', '答案错误', 'correction', 'test revision')
        if store.latest(data.rows[0]['contract_id'])['verdict'] != '答案错误' or len(Path(store.export()).read_text().splitlines()) != 2:
            raise ValueError('review_precheck:persistence_failed')
    def prepare(row):
        path = data.clip(row['contract_id'])
        subprocess.run([ffmpeg, '-v', 'error', '-i', path, '-f', 'null', '-'], check=True, capture_output=True, timeout=180)
        return {'contract_id': row['contract_id'], 'path': path, 'bytes': Path(path).stat().st_size}
    with ThreadPoolExecutor(max_workers=4) as pool:
        clips = list(pool.map(prepare, data.rows))
    report = {'events': len(first), 'clips_decoded': len(clips), 'gradio': gradio.__version__, 'python': sys.version, 'ffmpeg': ffmpeg, 'gpu_required': False, 'free_bytes': shutil.disk_usage(REVIEW).free, 'review_save_and_history_check': True, 'production_review_rows_added': 0, 'clips': clips}
    (ROOT / 'reports/impact_qa/human_review_precheck.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'clips'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
