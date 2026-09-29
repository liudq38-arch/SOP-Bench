import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import verify_reference
from prepare_evidence_v17 import check, materialize


def main():
    folder = OUT / 'evidence_v18_inputs'
    originals = read_jsonl(OUT / 'evidence_v17_inputs/manifest.jsonl')
    groups = defaultdict(list)
    for row in originals:
        groups[row['video_id']].append(row)
    packages = []
    checked_sources = set()
    media = {}
    for video, rows in groups.items():
        checkpoint = folder / 'trials' / (video + '.json')
        parent = [read_json(row['package_path']) for row in rows]
        key = fingerprint(parent)
        if checkpoint.exists():
            previous = read_json(checkpoint)
            if previous['source_hash'] != key:
                raise ValueError('prepare_v18:changed_source:' + video)
            local = previous['packages']
        else:
            local = parent
            materialize(local)
        for p in local:
            check(p)
            refs = p['answer_contract']['source_references'] + p['private_context']['source_catalog_for_provenance_only'] + [im['source_reference'] for im in p['public_reference']['action_examples']]
            for ref in refs:
                basic = {k: ref[k] for k in ['path', 'sha256', 'pointer', 'value']}
                digest = fingerprint(basic)
                if digest not in checked_sources:
                    verify_reference(basic)
                    checked_sources.add(digest)
            images = p['target_visual']['images'] + p['public_reference']['action_examples']
            for im in images:
                actual = media.get(im['path'])
                if actual is None:
                    actual = hashlib.sha256(Path(im['path']).read_bytes()).hexdigest()
                    media[im['path']] = actual
                if actual != im['sha256']:
                    raise ValueError('prepare_v18:media_hash:' + im['path'])
            save_json(folder / 'packages' / (p['contract_id'] + '.json'), p)
        save_json(checkpoint, {'source_hash': key, 'packages': local})
        packages.extend(local)
        print({'video': video, 'events': len(local), 'total': len(packages)}, flush=True)
    if len({p['contract_id'] for p in packages}) != len(packages):
        raise ValueError('prepare_v18:duplicate_contract')
    save_jsonl(folder / 'packages.jsonl', packages)
    save_jsonl(folder / 'first10.jsonl', packages[:10])
    save_json(folder / 'media_hashes.json', media)
    summary = {'events': len(packages), 'trials': len(groups), 'kinds': dict(Counter(p['kind'] for p in packages)), 'materialized_events': sum(p['eligibility']['media_materialized'] for p in packages), 'unique_source_references_verified': len(checked_sources), 'unique_media_hashes': len(media), 'max_images': max(len(p['target_visual']['images']) + len(p['public_reference']['action_examples']) for p in packages), 'official_val_test_used': False, 'visual_sufficiency_not_automatically_established': True}
    save_json(REPORTS / 'evidence_v18_precheck.json', summary)
    print(summary, flush=True)
    for p in packages[:10]:
        print(p['contract_id'], p['kind'], len(p['target_visual']['images']), flush=True)


if __name__ == '__main__':
    main()
