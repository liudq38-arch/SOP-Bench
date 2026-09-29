import sys
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.state_qa import FRONT
from prepare_impact_tool_release import main as prepare_base
from refine_impact_tool_release import prepare as prepare_detail
from prepare_quality_v16 import normalize


def main():
    split = read_json(OUT / 'gt_v12_split_manifest.json')
    previous = set(split['development'] + split['unexposed_reserve'])
    videos = sorted(v for v in split['exposure_history'] if v not in previous)
    folder = OUT / 'quality_v16_training_inputs'
    extraction = []
    rows = []
    with zipfile.ZipFile('/data_1/ldq/dataset/impact/downloads/v1.1/videos/IMPACT-v1.1-videos-front.zip') as archive:
        for video in videos:
            info = archive.getinfo('IMPACT-v1.1/videos/front/' + video + '.mp4')
            target = FRONT / (video + '.mp4')
            if not target.exists() or target.stat().st_size != info.file_size:
                temporary = target.with_suffix('.partial.mp4')
                with archive.open(info) as source, temporary.open('wb') as dest:
                    while data := source.read(8 * 1024 * 1024):
                        dest.write(data)
                temporary.replace(target)
            crc = 0
            with target.open('rb') as source:
                while data := source.read(8 * 1024 * 1024):
                    crc = zlib.crc32(data, crc)
            if crc != info.CRC:
                raise ValueError('training_extract:crc_mismatch:' + video)
            extraction.append({'video_id': video, 'bytes': info.file_size, 'crc32': f'{crc:08x}'})
            save_json(folder / 'extraction.json', extraction)
            local = folder / video
            ready = local / 'validated_contracts.jsonl'
            if ready.exists():
                cases = [normalize(c) for c in read_jsonl(ready)]
            else:
                cases = prepare_base([video], local / 'base', local / 'base_validation.json')
                cases = [normalize(c) for c in prepare_detail(cases, local / 'detail')]
                save_jsonl(ready, cases)
            rows.extend(cases)
            print({'video': video, 'events': len(cases), 'total_events': len(rows)}, flush=True)
    save_jsonl(folder / 'contracts.jsonl', rows)
    save_jsonl(folder / 'first10.jsonl', rows[:10])
    all_rows = read_jsonl(OUT / 'quality_v16_inputs/contracts.jsonl') + rows
    if len({c['contract_id'] for c in all_rows}) != len(all_rows):
        raise ValueError('training_prepare:duplicate_event')
    save_jsonl(folder / 'all_contracts.jsonl', all_rows)
    save_json(folder / 'summary.json', {'additional_trials': len(videos), 'additional_events': len(rows), 'total_events': len(all_rows), 'tool_scope': 'all eligible normal >=15 frame screwdriver/wrench pickups across 31 training reassembly trials', 'other_kinds_scope': '77 previously prepared development events only', 'official_val_test_used': False, 'independent_acceptance': False})


if __name__ == '__main__':
    main()
