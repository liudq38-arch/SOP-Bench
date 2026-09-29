import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/impact_qa'
REPORTS = ROOT / 'reports/impact_qa'
ANNOTATIONS = ROOT / 'annotations/impact/IMPACT-v1.1/annotations'
MEDIA = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/ego')
FFMPEG = '/home/ldq/miniconda3/envs/ffmpeg/bin/ffmpeg'
FFPROBE = '/home/ldq/miniconda3/envs/ffmpeg/bin/ffprobe'
TYPES = ['temporal', 'spatial', 'handling', 'wrong_part', 'wrong_tool', 'procedural']


def read_json(path):
    return json.loads(Path(path).read_text())


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temporary.replace(path)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def save_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
