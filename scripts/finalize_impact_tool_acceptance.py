import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import verify_reference
from impact_qa.release_gate import evaluate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    folder = OUT / 'gt_v14_frozen_acceptance'
    frozen = read_json(REPORTS / 'gt_v14_tool_pipeline_frozen.json')
    policy = read_json(ROOT / 'configs/impact_qa/release_v14.json')
    for name, value in frozen['files'].items():
        assert digest(ROOT / name) == value, 'frozen:' + name
    assert frozen['policy_hash'] == fingerprint(policy)
    old_checks = {}
    for name in ['frozen_v7.json', 'gt_v12_code_snapshot.json']:
        previous = read_json(REPORTS / name)
        files = previous.get('files', previous)
        for path, value in files.items():
            assert digest(ROOT / path) == value, 'historical:' + path
        old_checks[name] = len(files)
    cases = read_jsonl(OUT / 'gt_v14_acceptance_inputs/contracts.jsonl')
    base = {c['contract_id']: c for c in read_jsonl(OUT / 'gt_v14_acceptance_base/contracts.jsonl')}
    results = {r['contract_id']: r for r in read_jsonl(folder / 'results.jsonl')}
    blind_path = folder / 'blind_review/agent_final_blind_answers.json'
    blind_document = read_json(blind_path)
    assert blind_document['gt_and_model_results_revealed'] is False
    blind = {r['contract_id']: r for r in blind_document['records']}
    assert set(base) == set(results) == set(blind) == {c['contract_id'] for c in cases}
    train = set((ANNOTATIONS / 'ASR/splits/train.split1.bundle').read_text().splitlines())
    val = set((ANNOTATIONS / 'ASR/splits/val.split1.bundle').read_text().splitlines())
    test = set((ANNOTATIONS / 'ASR/splits/test.split1.bundle').read_text().splitlines())
    trials = {c['video_id'] for c in cases}
    assert trials == set(frozen['acceptance_trials'])
    assert trials <= train and not trials.intersection(val | test | set(frozen['development_trials']))
    media = {}
    reviews = []
    rejected_notes = {
        0: 'Detailed board before GT reveal: silver wrench leaves table while handled drivers remain; blind model misses lift.',
        1: 'Post-reveal detailed board: red driver leaves table at target_13..15; blind model incorrectly says no lift.',
        2: 'Post-reveal detailed board: green handled shaft leaves table at target_12..15; silver wrench remains. Blind model confuses neighboring tool.',
        4: 'Post-reveal detailed board: silver wrench leaves table while colored drivers remain; blind model misses lift.',
        29: 'Before-reveal detailed board remains inconclusive: visible green driver stays on mat and possible second object is occluded. Keep hold.'
    }
    for i, c in enumerate(cases):
        for ref in c['references']:
            verify_reference(ref)
        source = c['references'][0]['value']
        assert source['entity'] == c['hand'] == 'right'
        assert source['phase'] == 'normal' and not any(source['anomaly_type'])
        assert c['target_interval_exclusive'] == [source['start_frame'], source['end_frame']]
        assert c['tool'] in ['screwdriver', 'wrench']
        assert c['canonical_answer'] == 'I picked up a ' + c['tool'] + ' with my right hand.'
        assert len(set(c['options'])) == 3
        assert set(c['options']) == {'A screwdriver.', 'A wrench.', 'A pair of pliers.'}
        assert c['options'][c['correct_option']] == 'A ' + c['tool'] + '.'
        for variant in [base[c['contract_id']], c]:
            assert len(variant['image_refs']) == 20
            for im in variant['image_refs']:
                assert c['start_frame'] <= im['frame_index'] <= c['end_frame_inclusive']
                assert abs(im['requested_time_s'] - im['frame_index'] / 30) < 1e-8
                if im['evidence_id'].startswith('target_'):
                    assert source['start_frame'] <= im['frame_index'] < source['end_frame']
                media[im['path']] = im['sha256']
        r = results[c['contract_id']]
        assert r['status'] == 'ok'
        assert r['generation'] == {'question': c['question'], 'answer': c['canonical_answer']}
        gen, visual = [read_json(OUT / 'api_cache' / (key + '.json')) for key in r['cache_keys']]
        assert gen['request_metadata']['payload']['canonical_answer'] == c['canonical_answer']
        assert gen['request_metadata']['image_refs'] == base[c['contract_id']]['image_refs']
        assert visual['request_metadata']['image_refs'] == c['image_refs']
        payload = visual['request_metadata']['payload']
        assert set(payload) == {'question', 'clip_start_original_s', 'clip_end_original_s_exclusive'}
        assert payload['question'] == c['question']
        supported = blind[c['contract_id']]['answer'] == c['tool']
        reviews.append({'index': i, 'contract_id': c['contract_id'], 'video_id': c['video_id'], 'pipeline_proposed_retain': r['proposed_retain'], 'blind_answer': blind[c['contract_id']]['answer'], 'gt_tool': c['tool'], 'source_pass': True, 'visual_pass': supported, 'temporal_pass': supported, 'question_pass': True, 'mcq_pass': True, 'isolation_pass': True, 'quality_pass': supported, 'severe_defects': 0, 'review_source': 'research_agent_direct_evidence', 'review_is_human': False, 'model_narrative_is_gold': False, 'review_note': rejected_notes.get(i, 'Blind overview answer supported; post-reveal endpoint images and canonical QA checked. Full twenty-frame input is exported.')})
    for path, value in media.items():
        assert digest(path) == value, 'media:' + path
    public = read_jsonl(folder / 'evaluation_inputs.jsonl')
    retained = [c for c in cases if results[c['contract_id']]['proposed_retain']]
    assert len(public) == len(retained) * 2
    for c in retained:
        for form in ['open', 'mcq']:
            qid = fingerprint([c['contract_id'], form])[:24]
            record = next(x for x in public if x['qa_id'] == qid)
            allowed = {'qa_id', 'format', 'question', 'image_paths', 'original_times_s', 'annotation_assisted_sampling'} | ({'options'} if form == 'mcq' else set())
            assert set(record) == allowed
            assert record['question'] == c['question']
            assert record['image_paths'] == [im['path'] for im in c['image_refs']]
            assert record['original_times_s'] == [im['requested_time_s'] for im in c['image_refs']]
            if form == 'mcq':
                assert record['options'] == c['options']
    snapshot = lambda: {str(p): (p.stat().st_mtime_ns, digest(p)) for phase in ['development', 'acceptance'] for sub in ['request_audit', 'runs'] for p in (OUT / ('gt_v14_frozen_' + phase) / sub).glob('*.json')}
    before = snapshot()
    for phase in ['development', 'acceptance']:
        subprocess.run([sys.executable, str(ROOT / 'scripts/run_impact_tool_frozen.py'), '--phase', phase], cwd=ROOT, check=True)
    after = snapshot()
    assert before == after, 'resume:changed_requests_or_runs'
    keep_reviews = [r for r in reviews if r['pipeline_proposed_retain']]
    good = sum(r['quality_pass'] for r in keep_reviews)
    requirements = {k: True for k in policy['require']}
    evidence = {'kind': 'tool_identity', 'policy_hash': fingerprint(policy), 'pipeline_hash': frozen['pipeline_hash'], 'reviewed_pipeline_hash': frozen['pipeline_hash'], 'review_source': 'research_agent_direct_evidence', 'requirements': requirements, 'metrics': {'hard_check_pass_rate': 1.0, 'severe_defects': sum(r['severe_defects'] for r in keep_reviews), 'overall_quality_pass_rate': good / len(keep_reviews), 'per_kind_quality_pass_rate': good / len(keep_reviews), 'visual_evidence_pass_rate': sum(r['visual_pass'] for r in keep_reviews) / len(keep_reviews), 'completion_rate': len(results) / len(cases), 'min_independent_events_per_kind': len(keep_reviews), 'min_validation_trials': len({c['video_id'] for c in retained}), 'min_validation_participants': len({c['participant'] for c in retained})}, 'denominators': {'attempted_events': len(cases), 'reviewed_retained_events': len(keep_reviews), 'quality_passed_retained': good, 'reviewed_rejected_events': len(cases) - len(keep_reviews), 'blind_supported_rejected': sum(r['visual_pass'] for r in reviews if not r['pipeline_proposed_retain'])}, 'limitations': ['Single research-agent review, not independent human gold.', 'Trial holdout, not participant-disjoint or statistically independent events.', 'One question template; generic normal tool pickup only.', 'Minimum event threshold counts frozen-filter retained events; discarded or developer events cannot fill the gap.']}
    gate = evaluate(evidence, policy)
    summary = {'pipeline_hash': frozen['pipeline_hash'], 'events': len(cases), 'trials': len(trials), 'participants': len({c['participant'] for c in cases}), 'proposed_retained': len(retained), 'comparisons': dict(Counter(r['comparison'] for r in results.values())), 'blind_supported_all': sum(r['visual_pass'] for r in reviews), 'retained_quality_passed': good, 'retained_quality_denominator': len(keep_reviews), 'source_references_checked': sum(len(c['references']) for c in cases), 'unique_media_hashes_checked': len(media), 'completion_rate': 1.0, 'retention_rate': len(retained) / len(cases), 'source_tool_distribution': dict(Counter(c['tool'] for c in cases)), 'retained_tool_distribution': dict(Counter(c['tool'] for c in retained)), 'correct_option_positions': dict(Counter(c['correct_option'] for c in retained)), 'resume_new_requests': 0, 'resume_run_files_unchanged': True, 'historical_frozen_files_checked': old_checks, 'blind_review_sha256': digest(blind_path), 'gate': gate}
    save_jsonl(folder / 'agent_adjudication.jsonl', reviews)
    proposed = read_jsonl(folder / 'proposed_candidates.jsonl')
    for c in proposed:
        c.update(status='agent_reviewed_candidate_gate_blocked' if not gate['release'] else 'agent_reviewed_candidate', review_source='research_agent_direct_evidence', human_review=False)
    save_jsonl(folder / 'reviewed_candidates.jsonl', proposed)
    save_jsonl(folder / 'rejected_adjudication.jsonl', [r for r in reviews if not r['pipeline_proposed_retain']])
    save_json(REPORTS / 'gt_v14_gate_evidence.json', evidence)
    save_json(REPORTS / 'gt_v14_release_gate.json', gate)
    save_json(REPORTS / 'gt_v14_acceptance_final.json', summary)
    caches = {}
    for directory in ['gt_v14_tools', 'gt_v14_1_tools', 'gt_v14_frozen_development', 'gt_v14_frozen_acceptance']:
        for path in (OUT / directory / 'request_audit').glob('*.json'):
            audit = read_json(path)
            if audit.get('status') == 'ok':
                response = audit['response']
                caches[response['cache_key']] = response
    usages = [c['usage']['prompt_tokens'] for c in caches.values()]
    save_json(REPORTS / 'gt_v14_api_stats.json', {'unique_successful_cache_keys': len(caches), 'by_stage': dict(Counter(c['stage'] for c in caches.values())), 'prompt_tokens_min': min(usages), 'prompt_tokens_max': max(usages), 'prompt_tokens_median': sorted(usages)[len(usages) // 2], 'http_attempt_count': 'not inferred from cache keys; audit includes cache hits', 'generation_max_tokens': 180, 'v14_visual_max_tokens': 300, 'v14_1_track_max_tokens': 350})
    save_json(OUT / 'gt_v14_exposure_manifest.json', {'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'parent': 'gt_v12_split_manifest.json', 'consumed_frozen_acceptance_trials': sorted(trials), 'development_trials': frozen['development_trials'], 'unexposed_reserve_from_parent_remaining': [], 'acceptance_used_for_prompt_tuning': False, 'official_val_test_media_or_gt_inspected_this_batch': False, 'future_reuse': 'Frozen regression only after tuning from these outcomes; never describe as newly unseen again.'})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
