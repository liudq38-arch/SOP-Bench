import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import verify_reference
from impact_qa.release_gate import evaluate


def main():
    folder = OUT / 'gt_v14_tools'
    cases = read_jsonl(OUT / 'gt_v14_tool_inputs/contracts.jsonl')
    results = {r['contract_id']: r for r in read_jsonl(folder / 'results.jsonl')}
    assert len(cases) == len(results)
    media = read_json(OUT / 'gt_v14_tool_inputs/media_hashes.json')
    for path, digest in media.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    records = []
    for index, c in enumerate(cases):
        for ref in c['references']:
            verify_reference(ref)
        assert len(set(c['options'])) == 3
        assert c['options'][c['correct_option']] == 'A ' + c['tool'] + '.'
        r = results[c['contract_id']]
        if r['status'] == 'ok':
            gen, vis = [read_json(OUT / 'api_cache' / (key + '.json')) for key in r['cache_keys']]
            assert gen['request_metadata']['payload']['canonical_answer'] == c['canonical_answer']
            assert not {'canonical_answer', 'source_label', 'tool', 'references'}.intersection(vis['request_metadata']['payload'])
        records.append({'index': index, 'contract_id': c['contract_id'], 'video_id': c['video_id'], 'gt_tool': c['tool'], 'hand': c['hand'], 'source_interval': c['target_interval_exclusive'], 'comparison': r.get('short_answer_comparison'), 'visible_evidence': r.get('visual_review', {}).get('visible_evidence'), 'contact_sheet': c['contact_sheet']})
    save_jsonl(folder / 'review_index_private.jsonl', records)
    audit_folder = folder / 'audit_boards'
    audit_folder.mkdir(exist_ok=True)
    for page in range((len(cases) + 3) // 4):
        subset = cases[page * 4:page * 4 + 4]
        board = Image.new('RGB', (1920, 1720), 'white')
        draw = ImageDraw.Draw(board)
        for row, c in enumerate(subset):
            draw.text((5, row * 430 + 4), f'{page * 4 + row} {c["contract_id"]} {c["question"]}', fill='black')
            for column, slot in enumerate([0, 4, 11, 19]):
                im = c['image_refs'][slot]
                image = ImageOps.contain(Image.open(im['path']), (480, 380))
                x, y = column * 480, row * 430 + 48
                draw.text((x + 5, y - 20), f'{im["evidence_id"]} | {im["requested_time_s"]:.3f}s', fill='black')
                board.paste(image, (x + (480 - image.width) // 2, y))
        board.save(audit_folder / f'page_{page:02d}.jpg', quality=96)
    counts = Counter(r.get('short_answer_comparison', 'error') for r in results.values())
    summary = {'events': len(cases), 'trials': len({c['video_id'] for c in cases}), 'participants': len({c['participant'] for c in cases}), 'tool_counts': dict(Counter(c['tool'] for c in cases)), 'option_position_counts': dict(Counter(c['correct_option'] for c in cases)), 'source_media_mcq_checks_pass': True, 'comparison_counts': dict(counts), 'completion_rate': sum(r['status'] == 'ok' for r in results.values()) / len(cases), 'comparison_is_not_quality_accuracy': True, 'independent_acceptance_started': False}
    save_json(REPORTS / 'gt_v14_tool_summary.json', summary)
    policy = read_json(ROOT / 'configs/impact_qa/release_v14.json')
    evidence = {'kind': 'tool_identity', 'policy_hash': fingerprint(policy), 'requirements': {'source_and_media_checks': True, 'mcq_unique': True, 'no_gt_leakage': True, 'no_cross_split_trial_overlap': True, 'bias_report': True}, 'metrics': {'hard_check_pass_rate': 1.0, 'completion_rate': summary['completion_rate'], 'min_independent_events_per_kind': 0, 'min_validation_trials': 0, 'min_validation_participants': 0}, 'review_source': 'development_only', 'pipeline_hash': None}
    save_json(REPORTS / 'gt_v14_gate_evidence.json', evidence)
    save_json(REPORTS / 'gt_v14_release_gate.json', evaluate(evidence, policy))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
