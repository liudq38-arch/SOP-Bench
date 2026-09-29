import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD_CONFIG = 'configs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix3.json'
NEW_CONFIG = 'configs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix4.json'


def read_json(path):
    return json.loads(path.read_text())


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))


def link_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    os.link(source, target)


def main():
    old_root = ROOT / read_json(ROOT / OLD_CONFIG)['output_root']
    new_config = read_json(ROOT / NEW_CONFIG)
    new_root = ROOT / new_config['output_root']
    excluded = {row['clip_id'] for row in read_jsonl(new_root / 'tail_excluded.jsonl')}
    manifest = read_jsonl(new_root / 'manifest.jsonl')
    kept_ids = {row['clip_id'] for row in manifest}
    if excluded & kept_ids:
        raise RuntimeError('tail_filter:excluded_clip_remains_in_manifest')
    old_manifest = {row['clip_id']: row for row in read_jsonl(old_root / 'manifest.jsonl')}
    if not kept_ids <= set(old_manifest):
        raise RuntimeError('tail_filter:new_manifest_not_subset_of_generated_manifest')

    for name in ['media', 'api_cache', 'api_cache_failures', 'runs']:
        source = old_root / name
        target = new_root / name
        if not source.exists():
            continue
        target.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            destination = target / item.name
            if item.is_file() and not destination.exists():
                link_file(item, destination)

    for clip_id in sorted(kept_ids):
        for name in ['results']:
            source = old_root / name / (clip_id + '_V.json')
            if not source.exists():
                raise RuntimeError(f'tail_filter:missing_{name}:{clip_id}')
            link_file(source, new_root / name / source.name)
        input_source = old_root / 'inputs' / (clip_id + '.json')
        media_manifest_source = old_root / 'media_manifests' / (clip_id + '.json')
        if not input_source.exists() or not media_manifest_source.exists():
            raise RuntimeError('tail_filter:missing_media_manifest:' + clip_id)
        input_value = read_json(input_source)
        media_value = read_json(media_manifest_source)
        old_media_path = Path(media_value['path'])
        new_media_path = new_root / 'media' / old_media_path.name
        if old_media_path.exists() and not new_media_path.exists():
            link_file(old_media_path, new_media_path)
        if not new_media_path.exists():
            raise RuntimeError('tail_filter:missing_media:' + clip_id)
        media_value['path'] = str(new_media_path)
        input_value['media'] = media_value
        write_json(new_root / 'inputs' / input_source.name, input_value)
        write_json(new_root / 'media_manifests' / media_manifest_source.name, media_value)

    old_questions = read_jsonl(old_root / 'questions.jsonl')
    old_reviews = read_jsonl(old_root / 'reviews.jsonl')
    questions = [row for row in old_questions if row.get('clip_id') in kept_ids]
    reviews = [row for row in old_reviews if row.get('clip_id') in kept_ids]
    write_jsonl(new_root / 'questions.jsonl', questions)
    write_jsonl(new_root / 'reviews.jsonl', reviews)

    results = [read_json(new_root / 'results' / (clip_id + '_V.json')) for clip_id in kept_ids]
    from collections import Counter
    progress = {
        'state': 'full_finished',
        'selected_clips': len(manifest),
        'resolved_clips': len(results),
        'pending_clip_count': 0,
        'preparation_error_count': 0,
        'arm_status': dict(Counter(row.get('status') for row in results)),
        'question_status': dict(Counter(row.get('status') for row in questions)),
        'question_kinds': dict(Counter(row.get('kind') for row in questions)),
        'selected_question_count': sum(len(row.get('selected_question_ids', [])) for row in results),
        'human_review': 'pending',
        'formal_release': False,
        'generation_reused_from': str(Path(OLD_CONFIG).as_posix()),
        'excluded_source_end_cleanup_tails': sorted(excluded),
    }
    write_json(new_root / 'progress.json', progress)
    write_json(new_root / 'reuse_manifest.json', {
        'source_output_root': str(old_root.relative_to(ROOT)),
        'kept_clip_count': len(kept_ids),
        'excluded_clip_ids': sorted(excluded),
        'policy': 'Reuse completed per-clip model results for unaffected clips; no new API requests.',
    })
    print(json.dumps({
        'kept_clips': len(kept_ids),
        'excluded_tails': sorted(excluded),
        'questions': len(questions),
        'question_kinds': dict(Counter(row.get('kind') for row in questions)),
        'question_status': dict(Counter(row.get('status') for row in questions)),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
