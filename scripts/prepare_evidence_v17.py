import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

import av
from PIL import ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_package import CUTOFF_KINDS, blind_payload, build_package, generation_payload, public_procedure


def materialize(packages):
    by_video = defaultdict(list)
    for p in packages:
        by_video[p['video_id']].append(p)
    for video, local in by_video.items():
        wanted = {}
        for p in local:
            for im in p['target_visual']['images']:
                if im['evidence_id'].startswith('anchor_') and not Path(im['path']).exists():
                    wanted[im['frame_index']] = im['path']
        if wanted:
            with av.open(local[0]['target_visual']['source_video']) as container:
                stream = container.streams.video[0]
                stream.thread_type = 'AUTO'
                for number, path in sorted(wanted.items()):
                    container.seek(int((number / 30) / float(stream.time_base)), stream=stream, backward=True)
                    found = False
                    for frame in container.decode(stream):
                        seconds = float(frame.pts * frame.time_base)
                        n = round(seconds * 30)
                        if n == number:
                            if abs(seconds - number / 30) >= 1e-5:
                                raise ValueError('evidence_materialize:pts_mismatch:' + video)
                            destination = Path(path)
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            ImageOps.pad(frame.to_image().crop((280, 270, 1020, 700)), (960, 560), color='white').save(destination, quality=96)
                            found = True
                            break
                        if n > number:
                            break
                    if not found:
                        raise ValueError('evidence_materialize:missing_frame:' + video + ':' + str(number))
        for p in local:
            for im in p['target_visual']['images']:
                im['sha256'] = hashlib.sha256(Path(im['path']).read_bytes()).hexdigest()
                im['time_scope'] = 'TARGET EXECUTION, original recording clock. ' + im.get('role', 'target_original_frame')
            p['eligibility']['media_materialized'] = True
            p['package_hash'] = fingerprint({k: v for k, v in p.items() if k != 'package_hash'})
        print({'video': video, 'packages': len(local), 'new_frames': len(wanted)}, flush=True)


def check(package):
    images = package['target_visual']['images']
    refs = package['public_reference']['action_examples']
    if len(images) + len(refs) > 32:
        raise ValueError('package_check:image_budget')
    if package['kind'] in CUTOFF_KINDS:
        cutoff = package['target_visual']['question_cutoff_frame']
        if any(im['frame_index'] > cutoff for im in images):
            raise ValueError('package_check:future_image')
        if any(row['frame'] > cutoff for row in package['private_context']['component_states']):
            raise ValueError('package_check:future_state')
        if any(row['start_frame'] > cutoff for row in package['private_context']['atomic_actions']):
            raise ValueError('package_check:future_action')
    if any(im['source_video'] == package['video_id'] for im in refs):
        raise ValueError('package_check:same_execution_demo')
    payload = blind_payload(package, package['answer_contract']['question_proposition'])
    if any(key in payload for key in ['answer_contract', 'private_context', 'GT_answer', 'correct_option', 'facts']):
        raise ValueError('package_check:blind_leak')
    if package['public_reference']['procedure']['mandatory_prerequisite_edges']:
        raise ValueError('package_check:unverified_mandatory_edge')


def main():
    folder = OUT / 'evidence_v17_inputs'
    procedure = public_procedure()
    demonstrations = read_json(OUT / 'gt_v13_action_reference/provenance.json')
    cases = read_jsonl(OUT / 'quality_v16_inputs/contracts.jsonl') + read_jsonl(OUT / 'quality_v16_training_inputs/contracts.jsonl')
    packages = []
    for c in cases:
        p = build_package(c, procedure, demonstrations)
        check(p)
        p['package_hash'] = fingerprint(p)
        save_json(folder / 'packages' / (c['contract_id'] + '.json'), p)
        packages.append(p)
    smoke_ids = {c['contract_id'] for c in read_jsonl(OUT / 'quality_v16_inputs/smoke.jsonl')}
    smoke = [p for p in packages if p['contract_id'] in smoke_ids]
    materialize(smoke)
    for p in smoke:
        check(p)
        save_json(folder / 'packages' / (p['contract_id'] + '.json'), p)
        save_json(folder / 'generation_payloads' / (p['contract_id'] + '.json'), generation_payload(p))
        save_json(folder / 'blind_payloads' / (p['contract_id'] + '.json'), blind_payload(p, p['answer_contract']['question_proposition']))
    save_jsonl(folder / 'smoke_packages.jsonl', smoke)
    save_jsonl(folder / 'first10.jsonl', smoke[:10])
    save_jsonl(folder / 'manifest.jsonl', [{'contract_id': p['contract_id'], 'video_id': p['video_id'], 'kind': p['kind'], 'package_path': str(folder / 'packages' / (p['contract_id'] + '.json')), 'target_images': len(p['target_visual']['images']), 'reference_images': len(p['public_reference']['action_examples']), 'context_source_references': len(p['private_context']['source_catalog_for_provenance_only']), 'eligibility': p['eligibility']} for p in packages])
    report = {'events': len(packages), 'materialized_smoke': len(smoke), 'kinds': dict(Counter(p['kind'] for p in packages)), 'max_images_total': max(len(p['target_visual']['images']) + len(p['public_reference']['action_examples']) for p in packages), 'context_source_references': sum(len(p['private_context']['source_catalog_for_provenance_only']) for p in packages), 'new_generation_started': False, 'future_cutoff_violations': 0, 'same_execution_demo_violations': 0, 'official_val_test_used': False}
    save_json(REPORTS / 'evidence_v17_precheck.json', report)
    print(report, flush=True)
    for p in smoke[:10]:
        print({'id': p['contract_id'], 'kind': p['kind'], 'target_images': len(p['target_visual']['images']), 'reference_images': len(p['public_reference']['action_examples']), 'missing': p['missing_data']}, flush=True)


if __name__ == '__main__':
    main()
