import hashlib
import sys
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, read_json, save_json
from impact_qa.state_qa import FRONT
from prepare_impact_tool_release import main as prepare_base
from refine_impact_tool_release import prepare as prepare_detail


def main():
    frozen = read_json(REPORTS / 'gt_v14_tool_pipeline_frozen.json')
    for path, digest in frozen['files'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    videos = frozen['acceptance_trials']
    assert not set(videos) & set(frozen['development_trials'])
    extracted = []
    with zipfile.ZipFile('/data_1/ldq/dataset/impact/downloads/v1.1/videos/IMPACT-v1.1-videos-front.zip') as archive:
        for video in videos:
            info = archive.getinfo('IMPACT-v1.1/videos/front/' + video + '.mp4')
            target = FRONT / (video + '.mp4')
            if not target.exists() or target.stat().st_size != info.file_size:
                temp = target.with_suffix('.partial.mp4')
                with archive.open(info) as source, temp.open('wb') as dest:
                    while data := source.read(8 * 1024 * 1024):
                        dest.write(data)
                temp.replace(target)
            crc = 0
            with target.open('rb') as source:
                while data := source.read(8 * 1024 * 1024):
                    crc = zlib.crc32(data, crc)
            assert crc == info.CRC
            extracted.append({'video_id': video, 'bytes': info.file_size, 'crc32': f'{crc:08x}'})
    save_json(REPORTS / 'gt_v14_acceptance_extraction.json', extracted)
    rows = prepare_base(videos, OUT / 'gt_v14_acceptance_base', REPORTS / 'gt_v14_acceptance_input_validation.json')
    prepare_detail(rows, OUT / 'gt_v14_acceptance_inputs')


if __name__ == '__main__':
    main()
