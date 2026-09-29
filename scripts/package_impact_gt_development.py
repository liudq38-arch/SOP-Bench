import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import verify_reference
from impact_qa.review_page import write_review_page


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while data := stream.read(8 * 1024 * 1024):
            h.update(data)
    return h.hexdigest()


def main():
    source = OUT / 'gt_v12_2_development'
    target = OUT / 'gt_v12_final'
    target.mkdir(exist_ok=True)
    contracts = read_jsonl(OUT / 'gt_v12_2_inputs/contracts.jsonl')
    opens = read_jsonl(source / 'open_candidates.jsonl')
    mcqs = read_jsonl(source / 'mcq_candidates.jsonl')
    inputs = read_jsonl(source / 'evaluation_inputs.jsonl')
    assert len(opens) == len(mcqs) == len(contracts) == 93
    assert len(inputs) == 186
    lookup = {c['contract_id']: c for c in contracts}
    multiple = {m['contract_id']: m for m in mcqs}
    inspected = read_json(REPORTS / 'gt_v12_inspected_sheets.json')
    selected_tools = {'gt_557c3b73e2d72ad843b8', 'gt_60effcf6fe70f139866d', 'gt_ac252e53430c5f05eb5d', 'gt_bfdade91d3d082a22908', 'gt_eac777425da2bf9c0254', 'gt_fcb467f48529c6849132'}
    disagreements = {'gt_85f49f6c206ca7682d97', 'gt_b798864678cad52d8acd', 'gt_736d6aa567b506dccc52', 'gt_ff33a46e2664a80c198f', 'gt_c33f66a67e2fda487eca', 'gt_dec3de3eecb3286ddf56', 'gt_2f4c67899c117d82da66', 'gt_106908b1a09648302841', 'gt_b56948156e2c6ed45898', 'gt_28c1f0948d9196a8d772', 'gt_2283ec15593bda5e4289'}
    media, cards, audits = {}, [], []
    table = defaultdict(Counter)
    for c in contracts:
        for ref in c['references']:
            verify_reference(ref)
        for im in c['image_refs']:
            p = im['path']
            if p not in media:
                media[p] = {'sha256': sha256(p), 'bytes': Path(p).stat().st_size}
        clip = c['clip_path']
        with av.open(clip) as container:
            stream = container.streams.video[0]
            assert stream.frames == c['end_frame_inclusive'] - c['start_frame'] + 1, c['contract_id']
            assert float(stream.average_rate) == 30 and stream.start_time == 0
            media[clip].update(frames=stream.frames, width=stream.width, height=stream.height, fps=30, start_time=0)
        assert all(c['start_frame'] <= im['frame_index'] <= c['end_frame_inclusive'] for im in c['image_refs'] if im.get('media_type') != 'video')
    for row in opens:
        c = lookup[row['contract_id']]
        m = multiple[c['contract_id']]
        assert len(set(m['options'].values())) == 3
        assert m['options'][m['correct_answer']] == c['choice_texts'][0]
        status = row['blind_visual_review']['answerability']
        table[c['kind']][status] += 1
        table[c['kind']]['total'] += 1
        agreement = 'short_answer_conflicts_with_gt' if c['contract_id'] in disagreements else ('short_answer_consistent_evidence_unverified' if status == 'answerable' else 'no_definite_visual_answer')
        if c['contract_id'] in disagreements:
            assert status == 'answerable'
            decision, reason = 'hold_gt_visual_disagreement', 'Research agent compared the blind short answer with GT: named tool, temporal order or installation polarity conflicts. Do not overwrite GT or accept visual self-confidence as evidence.'
        elif c['contract_id'] in selected_tools:
            decision, reason = 'priority_for_full_review', 'Direct sampled-frame inspection supports generic tool identity; continuous and independent acceptance review still pending.'
        elif c['kind'] in ['action_error_category', 'action_phase']:
            decision, reason = 'hold_visual_evidence', 'GT supports hand/action labels; sparse overview frames do not establish all error attributes or normal correctness. No physical mechanism is inferred.'
        else:
            decision, reason = 'needs_full_review', 'Component identity, exact endpoint or both action onsets require independent continuous review; model confidence alone is insufficient.'
        row.update(agent_decision=decision, agent_reason=reason, visual_answer_agreement=agreement, direct_frame_inspected=c['contract_id'] in inspected['ids'], human_review_status='pending_human_review')
        audit = {'contract_id': c['contract_id'], 'reviewer_kind': 'research_agent_source_aware_development_review', 'source_aware': True, 'continuous_playback': False, 'direct_frame_inspected': row['direct_frame_inspected'], 'S': 'source_references_verified_and_model_semantics_passed', 'V': 'sampled_generic_identity_supported' if c['contract_id'] in selected_tools else 'pending_or_uncertain', 'T': 'media_sync_verified_continuous_action_review_pending', 'Q': 'development_text_checked', 'M': 'unique_source_option_verified_distractor_review_pending', 'D': 'mechanical_isolation_verified', 'decision': decision, 'reason': reason, 'human_review_status': 'pending_human_review'}
        audits.append(audit)
        audit['visual_short_answer_comparison'] = agreement
        cards.append({'contract_id': c['contract_id'], 'clip_path': c['clip_path'], 'contact_sheet': c['contact_sheet'], 'question': row['question'], 'answer': row['answer'], 'gt_reference_answer': c['canonical_answer'], 'mcq_question': m['question'], 'options': m['options'], 'correct_answer': m['correct_answer'], 'references': c['references'], 'time_range': f'{c["start_frame"] / 30:.3f}–{(c["end_frame_inclusive"] + 1) / 30:.3f}s（原视频）；播放器从0开始'})
    prohibited = {'answer', 'correct_answer', 'canonical_answer', 'gt_reference_answer', 'facts', 'source_references', 'references', 'kind', 'answer_polarity', 'source_review', 'blind_visual_review'}
    for item in inputs:
        assert not prohibited.intersection(item)
    manifest = read_json(OUT / 'gt_v12_split_manifest.json')
    assert not set(manifest['development']) & set(manifest['unexposed_reserve'] + manifest['previously_exposed_regression_reserve'])
    frozen = read_json(REPORTS / 'frozen_v7.json')
    for p, digest in frozen['files'].items():
        assert sha256(ROOT / p) == digest, p
    durations = [(c['end_frame_inclusive'] - c['start_frame'] + 1) / 30 for c in contracts]
    summary = {'open_count': len(opens), 'mcq_count': len(mcqs), 'trials': len({c['video_id'] for c in contracts}), 'participants': len({c['video_id'].split('_')[0] for c in contracts}), 'source_gate_pass': sum(r['source_gate_passed'] for r in opens), 'by_kind_visual_self_report': dict(table), 'answer_polarities': dict(Counter(r['answer_polarity'] for r in opens)), 'mcq_positions': dict(Counter(r['correct_answer'] for r in mcqs)), 'agent_dispositions': dict(Counter(r['agent_decision'] for r in opens)), 'directly_inspected_contracts': len(inspected['ids']), 'continuous_playback_reviewed': 0, 'independent_human_reviewed': 0, 'independent_acceptance_passed': False, 'full_scale_release': False, 'clip_duration_s': {'min': min(durations), 'median': statistics.median(durations), 'max': max(durations)}, 'unique_native_clips': len({c['clip_path'] for c in contracts}), 'unique_model_media_assets': len(media), 'model_video_frames': 16, 'model_anchor_images': 4, 'known_unexposed_reserve_trials': len(manifest['unexposed_reserve']), 'prior_exposed_regression_trials': len(manifest['previously_exposed_regression_reserve'])}
    save_jsonl(target / 'open_candidates.jsonl', opens)
    save_jsonl(target / 'mcq_candidates.jsonl', mcqs)
    save_jsonl(target / 'evaluation_inputs.jsonl', inputs)
    save_jsonl(target / 'agent_review_records.jsonl', audits)
    save_jsonl(target / 'gt_visual_disagreements.jsonl', [r for r in opens if r['contract_id'] in disagreements])
    save_jsonl(target / 'priority_for_full_review.jsonl', [r for r in opens if r['agent_decision'] == 'priority_for_full_review'])
    save_jsonl(target / 'review_records_template.jsonl', [{'contract_id': c['contract_id'], 'reviewer_kind': None, 'independent_answer': None, 'evidence_times_s': [], 'S': None, 'V': None, 'T': None, 'Q': None, 'M': None, 'D': None, 'decision': None} for c in contracts])
    save_json(target / 'media_sha256.json', media)
    write_review_page(target / 'review.html', cards)
    summary['visual_short_answer_comparison'] = dict(Counter(r['visual_answer_agreement'] for r in opens))
    summary['visual_comparison_note'] = 'Source-aware research-agent reading of all short answers; consistency is not proof of sound visual evidence or an accuracy evaluation.'
    save_json(REPORTS / 'gt_v12_final_summary.json', summary)
    save_json(REPORTS / 'gt_v12_release_validation.json', {'source_references_verified': sum(len(c['references']) for c in contracts), 'media_frame_counts_verified': len(contracts), 'model_media_hashes': len(media), 'frozen_v7_hashes_unchanged': len(frozen['files']), 'mcq_correct_options_match_gt': len(mcqs), 'public_inputs_exclude_private_fields': len(inputs), 'split_membership_disjoint': True, 'independent_acceptance': False})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
