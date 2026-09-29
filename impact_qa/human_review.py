import hashlib
import json
import os
import sqlite3
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/impact_qa'
REVIEW = OUT / 'human_review_v18'
VIDEOS = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/front')
STATUS = {'evidence_screened_unvalidated': '通过模型筛选', 'quarantine_semantics': '语义/视觉审核隔离', 'quarantine_evidence_pair': '前后帧证据隔离', 'schema_rejected': '结构校验拒绝'}
KINDS = {'tool_identity': '工具拾取', 'observed_order': '观察到的操作顺序'}
VERDICTS = ['未审核', '通过', '问题不清楚', '答案错误', '视频证据不足', '其他问题']


def read_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


class ReviewStore:
    def __init__(self, folder=REVIEW):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.database = self.folder / 'reviews.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, contract_id TEXT NOT NULL, reviewer TEXT NOT NULL, verdict TEXT NOT NULL, corrected_answer TEXT NOT NULL, notes TEXT NOT NULL, updated_at TEXT NOT NULL, draft_hash TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS reviews_contract ON reviews(contract_id, id)')

    def connect(self):
        return sqlite3.connect(self.database, timeout=30)

    def latest(self, contract_id):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM reviews WHERE contract_id=? ORDER BY id DESC LIMIT 1', (contract_id,)).fetchone()
        return dict(row) if row else {}

    def save(self, row, reviewer, verdict, corrected_answer, notes):
        if verdict not in VERDICTS[1:]:
            raise ValueError('请先选择审核结论。')
        digest = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        record = (row['contract_id'], (reviewer or '').strip() or 'local_reviewer', verdict, corrected_answer or '', notes or '', datetime.now(timezone.utc).isoformat(), digest)
        with self.connect() as db:
            db.execute('INSERT INTO reviews(contract_id,reviewer,verdict,corrected_answer,notes,updated_at,draft_hash) VALUES (?,?,?,?,?,?,?)', record)
        return self.latest(row['contract_id'])

    def export(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            records = [dict(row) for row in db.execute('SELECT * FROM reviews ORDER BY id')]
        destination = self.folder / ('reviews_export_' + uuid.uuid4().hex + '.jsonl')
        destination.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
        return str(destination)


class ReviewData:
    def __init__(self):
        self.rows = read_rows(OUT / 'evidence_v18_batch/generated_drafts.jsonl')
        self.rows.sort(key=lambda r: (r['status'] != 'evidence_screened_unvalidated', r['kind'], r['video_id'], r['contract_id']))
        self.by_id = {r['contract_id']: r for r in self.rows}
        self.packages = {r['contract_id']: r for r in read_rows(OUT / 'evidence_v18_inputs/packages.jsonl')}
        self.clips = REVIEW / 'clips'
        self.clips.mkdir(parents=True, exist_ok=True)
        self.locks = {cid: threading.Lock() for cid in self.by_id}
        self.store = ReviewStore()

    def ids(self, scope, kind):
        return [r['contract_id'] for r in self.rows if (scope != '仅通过筛选（33）' or r['status'] == 'evidence_screened_unvalidated') and (kind == '全部题型' or KINDS.get(r['kind'], r['kind']) == kind)]

    def choices(self, ids):
        return [(f'{i + 1}. {KINDS.get(self.by_id[cid]["kind"], self.by_id[cid]["kind"])} | {self.by_id[cid]["video_id"]} | {cid[-6:]}', cid) for i, cid in enumerate(ids)]

    def timing(self, cid, context=False):
        p = self.packages[cid]
        a, b = p['answer_contract']['target_original_frame_interval_inclusive']
        fps = p['task']['fps']
        start, end = a / fps, (b + 1) / fps
        duration = p['task']['frame_count'] / fps
        return max(0, start - (3 if context else 0)), min(duration, end + (3 if context else 0)), start, end

    def clip(self, cid, context=False):
        if cid not in self.by_id:
            raise ValueError('未知题目ID。')
        row = self.by_id[cid]
        source = VIDEOS / (row['video_id'] + '.mp4')
        start, end, _, _ = self.timing(cid, context)
        stat = source.stat()
        key = hashlib.sha256(f'{source}:{stat.st_size}:{stat.st_mtime_ns}:{start}:{end}:h264-v1'.encode()).hexdigest()[:24]
        destination = self.clips / (key + '.mp4')
        with self.locks[cid]:
            if not destination.exists():
                temporary = destination.with_name(destination.stem + '.' + uuid.uuid4().hex + '.mp4')
                cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner', '-loglevel', 'error', '-ss', f'{start:.9f}', '-i', str(source), '-t', f'{end-start:.9f}', '-map', '0:v:0', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p', '-threads', '2', '-movflags', '+faststart', '-y', str(temporary)]
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=180)
                    os.replace(temporary, destination)
                except Exception as exc:
                    temporary.unlink(missing_ok=True)
                    raise RuntimeError(f'视频截取失败 [{cid}]: {exc}') from exc
        return str(destination)
