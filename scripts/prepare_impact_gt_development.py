import json
import random
import sys
import zipfile
import zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_development import FOLDER, contracts_for_video, prepare_media_for_video
from impact_qa.state_qa import FRONT


def split_manifest():
    train = (ANNOTATIONS / 'ASR/splits/train.split1.bundle').read_text().splitlines()
    assembly = [v for v in train if 'Reassembly' in v]
    prior = {}
    for name in ['development_events.jsonl', 'pilot_events.jsonl']:
        for r in read_jsonl(OUT / name):
            prior.setdefault(r['execution_id'] + '_front', []).append(name)
    for r in read_jsonl(OUT / 'gt_v11_inputs/contracts.jsonl'):
        prior.setdefault(r['video_id'], []).append('gt_v11_state_development')
    dev_names = ['MA07LF04_Reassembly_A_001', 'LE06AS03_Reassembly_A_001', 'SS07EL13_Reassembly_A_001', 'LE07UF17_Reassembly_A_002', 'ER10WE06_Reassembly_A_004', 'KE03ER16_Reassembly_A_002', 'KJ03JM25_Reassembly_A_003', 'KI03AR28_Reassembly_A_003']
    development = [v + '_front' for v in dev_names]
    assert all(v in assembly for v in development)
    clean = sorted(v for v in assembly if v not in prior)
    remaining = [v for v in assembly if v not in development + clean and not v.startswith('AL07EJ17')]
    random.Random(20260918).shuffle(remaining)
    regression = remaining[:16 - len(clean)]
    summary = read_json(ANNOTATIONS / 'ASR/splits/split1_summary.json')
    result = {'seed': 20260918, 'development': development, 'unexposed_reserve': clean, 'previously_exposed_regression_reserve': regression, 'reserve_is_not_one_clean_independent_set': True, 'history_scope': 'v7 development/pilot event manifests plus v11 state contracts; source inventory inspected, not an assertion that no other historic file ever referenced the videos', 'exposure_history': {v: sorted(set(prior.get(v, []))) for v in assembly}, 'official_training_bundle_count': len(train), 'official_training_assembly_count': len(assembly), 'summary_training_assembly_count': summary['summary']['assemble']['train']['count'], 'bundle_vs_summary_note': 'Use actual bundle entries; summary reports one more assembly entry than bundle.', 'development_participants': len({v.split('_')[0] for v in development}), 'unexposed_reserve_participants': len({v.split('_')[0] for v in clean}), 'official_test_untouched_by_this_batch': True}
    path = OUT / 'gt_v12_split_manifest.json'
    if path.exists():
        assert read_json(path) == result, 'split_manifest:existing_manifest_changed'
    save_json(path, result)
    return result


def extract(videos):
    archive = Path('/data_1/ldq/dataset/impact/downloads/v1.1/videos/IMPACT-v1.1-videos-front.zip')
    records = []
    with zipfile.ZipFile(archive) as z:
        for video in videos:
            member = 'IMPACT-v1.1/videos/front/' + video + '.mp4'
            info = z.getinfo(member)
            target = FRONT / (video + '.mp4')
            if not target.exists() or target.stat().st_size != info.file_size:
                temp = target.with_suffix('.partial.mp4')
                with z.open(info) as source, temp.open('wb') as dest:
                    while chunk := source.read(8 * 1024 * 1024):
                        dest.write(chunk)
                temp.replace(target)
            crc = 0
            with target.open('rb') as f:
                while chunk := f.read(8 * 1024 * 1024):
                    crc = zlib.crc32(chunk, crc)
            assert crc == info.CRC and target.stat().st_size == info.file_size
            records.append({'video': video, 'bytes': info.file_size, 'crc32': f'{crc:08x}', 'verified': True})
            print(json.dumps({'extracted': video, 'bytes': info.file_size}), flush=True)
    save_json(REPORTS / 'gt_v12_extraction.json', records)


def main():
    manifest = split_manifest()
    extract(manifest['development'])
    procedure = read_jsonl(OUT / 'gt_v11_inputs/contracts.jsonl')[0]['public_procedure']
    rows, skipped = [], []
    for index, video in enumerate(manifest['development']):
        contracts, skips = contracts_for_video(video, procedure, index)
        skipped.extend([dict(s, video=video) for s in skips])
        prepare_media_for_video(video, contracts)
        save_jsonl(FOLDER / 'by_video' / (video + '.jsonl'), contracts)
        rows.extend(contracts)
        print(json.dumps({'prepared': video, 'contracts': len(contracts), 'skipped': skips}), flush=True)
    assert len({r['contract_id'] for r in rows}) == len(rows)
    save_jsonl(FOLDER / 'contracts.jsonl', rows)
    save_jsonl(FOLDER / 'first10.jsonl', rows[:10])
    summary = {'contracts': len(rows), 'videos': len(manifest['development']), 'participants': manifest['development_participants'], 'kinds': dict(Counter(r['kind'] for r in rows)), 'polarities': dict(Counter(r['answer_polarity'] for r in rows)), 'anomaly_attributes': dict(Counter(a for r in rows for a in r['facts'].get('error_attributes', []))), 'skipped': skipped, 'continuous_clips_saved': True, 'model_video_frames': 16, 'model_exact_anchors': 4, 'review_sheet_frames': 8, 'gt_source_references': sum(len(r['references']) for r in rows), 'reserve_generated_or_viewed': False}
    save_json(REPORTS / 'gt_v12_input_validation.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
