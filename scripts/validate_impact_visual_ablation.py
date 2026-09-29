import hashlib
import json
import py_compile
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, read_json, read_jsonl, save_json
from impact_qa.gt_qa import verify_reference
from scripts.run_impact_visual_ablation import public_payload


def main():
    cases = read_jsonl(OUT / 'gt_v13_inputs/cases.jsonl')
    results = read_jsonl(OUT / 'gt_v13/compared_results.jsonl')
    grouped = defaultdict(dict)
    for c in cases:
        grouped[c['contract_id']][c['condition']] = c
        assert not {'gt_answer', 'facts', 'kind', 'answer_polarity'}.intersection(public_payload(c))
        for im in c['image_refs']:
            if im['view'] == 'front':
                assert c['start_frame'] <= im['frame_index'] <= c['end_frame_inclusive']
                assert abs(im['requested_time_s'] - im['frame_index'] / 30) < 1e-8
                size = (512, 288) if im['evidence_id'].startswith('context') else (640, 448)
                with Image.open(im['path']) as image:
                    assert image.size == size
    assert len(cases) == 132 and len(grouped) == 33
    for variants in grouped.values():
        a, b, c, d = [variants[k] for k in ['uniform_full', 'uniform_crop', 'dense_crop', 'dense_crop_manual']]
        for field in ['question', 'gt_answer', 'public_procedure']:
            assert len({v[field] for v in variants.values()}) == 1
        assert a['image_refs'][:4] == b['image_refs'][:4] == c['image_refs'][:4] == d['image_refs'][:4]
        assert [im['frame_index'] for im in a['image_refs']] == [im['frame_index'] for im in b['image_refs']]
        assert d['image_refs'][:20] == c['image_refs']
        assert [len(v['image_refs']) for v in [a, b, c, d]] == [20, 20, 20, 22]
    hashes = read_json(OUT / 'gt_v13_inputs/media_hashes.json')
    for path, digest in hashes.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    provenance = read_json(OUT / 'gt_v13_action_reference/provenance.json')
    assert provenance['source_video'] not in {c['video_id'] for c in cases}
    refs = []
    for e in provenance['examples']:
        refs.append(e['source'])
        assert hashlib.sha256(Path(e['image_path']).read_bytes()).hexdigest() == e['sha256']
    glossary = read_json(OUT / 'gt_v13_action_reference/glossary_provenance.json')
    for rows in glossary['support'].values():
        for row in rows:
            refs.extend([row['fine_reference'], row['coarse_reference']])
    for ref in refs:
        verify_reference(ref)
    mismatched_ids = []
    cache_response_differences = []
    for r in results:
        cached = read_json(OUT / 'api_cache' / (r['cache_key'] + '.json'))
        assert cached['status'] == 'ok'
        if cached['result'] != r['visual_review']:
            differences = [k for k in cached['result'] if cached['result'][k] != r['visual_review'].get(k)]
            assert set(differences) <= {'visible_evidence', 'limitations'}, (r['contract_id'], differences)
            same_key = [other for other in results if other['cache_key'] == r['cache_key']]
            assert len(same_key) == 2 and {other['condition'] for other in same_key} == {'uniform_crop', 'dense_crop'}
            cache_response_differences.append({'contract_id': r['contract_id'], 'condition': r['condition'], 'fields': differences, 'reason': 'identical B/C input keys raced; last cache write differs from preserved per-run explanation'})
        meta = cached['request_metadata']
        assert not {'gt_answer', 'facts', 'answer_polarity'}.intersection(meta['payload'])
        ids = {im['evidence_id'] for im in meta['image_refs']}
        for value in r['visual_review'].get('evidence_image_ids', []):
            normalized = str(value).removeprefix('Frame ')
            if normalized not in ids:
                mismatched_ids.append({'id': r['contract_id'], 'condition': r['condition'], 'invalid_image_id': value})
    frozen = read_json(REPORTS / 'frozen_v7.json')['files']
    snapshot = read_json(REPORTS / 'gt_v12_code_snapshot.json')
    for path, digest in dict(frozen, **snapshot).items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    scripts = ['impact_qa/visual_ablation.py', 'scripts/prepare_impact_visual_ablation.py', 'scripts/run_impact_visual_ablation.py', 'scripts/impact_top_view_diagnostic.py', 'scripts/impact_action_reference_diagnostic.py', 'scripts/review_impact_installation_compact.py', 'scripts/analyze_impact_visual_ablation.py', 'scripts/validate_impact_visual_ablation.py']
    for path in scripts:
        py_compile.compile(str(ROOT / path), doraise=True)
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in (OUT / 'api_cache').glob('*.json')}
    subprocess.run([sys.executable, str(ROOT / 'scripts/run_impact_visual_ablation.py')], check=True, cwd=ROOT)
    after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in (OUT / 'api_cache').glob('*.json')}
    assert before == after
    report = {'main_cases': 132, 'contracts': 33, 'valid_response_records': len(results), 'image_hashes_verified': len(hashes), 'reference_checks': len(refs), 'v7_frozen_files': len(frozen), 'v12_snapshot_files': len(snapshot), 'syntax_files': len(scripts), 'resume_api_cache_changes': 0, 'event_frames_within_contract': True, 'fixed_main_questions_and_gt': True, 'current_target_gt_absent_from_review_payload': True, 'annotation_assisted_sampling': True, 'evidence_image_id_issues': mismatched_ids, 'cache_response_differences': cache_response_differences, 'quality_acceptance': False}
    save_json(REPORTS / 'gt_v13_final_validation.json', report)
    save_json(REPORTS / 'gt_v13_code_snapshot.json', {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in scripts})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
