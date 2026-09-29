import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import verify_reference


def main():
    originals = read_jsonl(OUT / 'gt_v11_inputs/contracts.jsonl')
    contracts = {c['contract_id']: c for c in originals}
    contracts.update({c['contract_id']: c for c in read_jsonl(OUT / 'gt_v11_1_inputs/contracts.jsonl')})
    rows = {r['contract_id']: dict(r, source_version='gt_v11') for r in read_jsonl(OUT / 'gt_v11/open_candidates.jsonl')}
    rows.update({r['contract_id']: dict(r, source_version='gt_v11_1') for r in read_jsonl(OUT / 'gt_v11_1/open_candidates.jsonl')})
    mcqs = {r['contract_id']: r for r in read_jsonl(OUT / 'gt_v11/mcq_candidates.jsonl')}
    mcqs.update({r['contract_id']: r for r in read_jsonl(OUT / 'gt_v11_1/mcq_candidates.jsonl')})
    decisions = {
        'component_installed': ('retain_development_candidate', 'GT=1与适配板安装、紧固后收工具的画面相符；保留粗安装状态候选，不声称可验证扭矩和内部公差。'),
        'component_unassembled': ('hold_component_identification', 'GT=0明确，改问是否安装更准确；无GT审核虽答No，但理由仍出现适配板/轴承板混淆，需可靠部件图示或同刻清晰视角。'),
        'handle_installed': ('retain_development_candidate', 'GT=1且末态可见侧手柄连接，支持粗安装状态；不扩大到装置整体完成或工程紧固验收。'),
        'ongoing_step': ('retain_development_candidate', 'TAS-S动作在末帧仍有效、ASR未正确装配、目视仍拧紧；仅问尚未完成，未推导操作错误。'),
        'observed_order': ('retain_development_candidate', '直接看图与TAS-S实际区间支持转子先于适配板；包含真实反向命题No，不引用强制顺序。'),
        'tool_identity': ('retain_development_candidate', 'GT具体工具类蕴含螺丝刀大类，改写后画面及无GT回答均支持；不凭手柄颜色推断刀头类型。'),
        'action_duration': ('hold_temporal_boundary', 'GT闭区间计算无误，但自然语言拾取的起止定义与稀疏帧可见边界不完全相同；需连续短片/明确边界口径后再用于时长评测。'),
        'action_error_category': ('hold_visual_anomaly', '具名手和动作的原生handling异常GT明确，但当前帧不能解释可见异常；保留GT来源，暂缓视觉异常理解题，不编造具体机制。'),
    }
    output, audit, evaluation = [], [], []
    for c_id, row in rows.items():
        c = contracts[c_id]
        for ref in c['references']:
            verify_reference(ref)
        assert row['source_gate_passed']
        decision, reason = decisions[c['kind']]
        review = {'contract_id': c_id, 'decision': decision, 'reason_zh': reason, 'reviewer_kind': 'research_agent_direct_source_text_and_frame_review', 'source_aware': True, 'human_review_status': 'pending_human_review', 'evidence_sheet': c['contact_sheet'], 'continuous_video_playback': False, 'covers_formats': ['open', 'mcq'], 'mcq_note': 'Source, options and shared visual answerability reviewed; no separate blind MCQ inference was run.'}
        row['agent_review'] = review
        output.append(row)
        audit.append(review)
        mcqs[c_id]['agent_review'] = review
        assert mcqs[c_id]['options'][mcqs[c_id]['correct_answer']] == c['choice_texts'][0]
        for form, item in [('open', row), ('mcq', mcqs[c_id])]:
            public = {'qa_id': 'qa_' + fingerprint(item['qa_id'])[:20], 'format': form, 'question': item['question'], 'public_procedure': c['public_procedure'], 'clip_start_s': c['start_frame'] / 30, 'clip_end_s_exclusive': (c['end_frame_inclusive'] + 1) / 30, 'frame_paths': [r['path'] for r in c['image_refs']], 'frame_times_s': [r['requested_time_s'] for r in c['image_refs']]}
            if form == 'mcq':
                public['options'] = item['options']
            assert not any(k in public for k in ['answer', 'references', 'facts', 'correct_answer', 'kind', 'contract_id'])
            assert all(c['start_frame'] <= r['frame_index'] <= c['end_frame_inclusive'] for r in c['image_refs'])
            evaluation.append(public)
    folder = OUT / 'gt_v11_final'
    save_jsonl(folder / 'open_candidates.jsonl', output)
    save_jsonl(folder / 'mcq_candidates.jsonl', list(mcqs.values()))
    save_jsonl(folder / 'evaluation_inputs.jsonl', evaluation)
    save_jsonl(folder / 'agent_review.jsonl', audit)
    save_jsonl(folder / 'priority_open_candidates.jsonl', [r for r in output if r['agent_review']['decision'] == 'retain_development_candidate'])
    save_jsonl(folder / 'held_open_candidates.jsonl', [r for r in output if r['agent_review']['decision'] != 'retain_development_candidate'])
    usages = []
    for version in ['gt_v11_smoke', 'gt_v11', 'gt_v11_1']:
        for run in (OUT / version / 'runs').glob('*.json'):
            r = read_json(run)
            for key in r['cache_keys']:
                cache = read_json(OUT / 'api_cache' / (key + '.json'))
                meta = cache['request_metadata']
                stage = cache['stage']
                if stage.endswith('_generate'):
                    assert meta['image_refs'] and meta['payload']['canonical_answer']
                    assert meta['payload']['references']
                if stage.endswith('_visual_review'):
                    assert not any(k in meta['payload'] for k in ['canonical_answer', 'facts', 'references', 'proposed_qa', 'answer', 'kind'])
                usages.append({'stage': stage, 'seconds': cache['seconds'], 'usage': cache['usage'], 'key': key})
    summary = {'open': len(output), 'mcq': len(mcqs), 'agent_decisions': dict(Counter(r['decision'] for r in audit)), 'open_polarity': dict(Counter(r['answer_polarity'] for r in output)), 'unique_open_questions': len({r['question'] for r in output}), 'source_gate_passed': sum(r['source_gate_passed'] for r in output), 'new_generation_protocol_verified': 'All generation API requests included original frames, GT references and canonical GT answer.', 'blind_visual_protocol_verified': 'No GT answer or execution annotations in visual-review payload.', 'source_frame_count': len({(c['video_id'], n) for c in originals for n in c['frame_indices']}), 'distinct_boards_directly_inspected': 18, 'same_model_calls_including_smoke': len(usages), 'max_prompt_tokens': max(u['usage']['prompt_tokens'] for u in usages), 'median_request_seconds': statistics.median(u['seconds'] for u in usages), 'human_signed_off': False, 'not_an_accuracy_measurement': True, 'limitations': ['One participant and three trials; development only.', 'Three anomaly questions all handling; not category-balanced anomaly benchmark.', 'MCQ options are three-choice by dimension, not EgoErrorVQA taxonomy reproduction.', 'GT-driven boundary frame selection is an oracle annotation-assisted sampling protocol; not end-to-end unsegmented-video evaluation.', 'Retained candidates still require human confirmation.']}
    save_json(REPORTS / 'gt_v11_final_summary.json', summary)
    save_json(REPORTS / 'gt_v11_runtime_metrics.json', usages)
    frozen = read_json(REPORTS / 'frozen_v7.json')
    for p, expected in frozen['files'].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == expected
    assert len(output) == len(mcqs) == 24 and len(evaluation) == 48
    assert len({r['qa_id'] for r in evaluation}) == 48
    save_json(REPORTS / 'gt_v11_release_validation.json', {'contracts_source_hash_and_pointer_check': True, 'generation_sees_visual_and_gt_verified': True, 'evaluation_gt_fields_excluded': True, 'no_future_frames': True, 'mcq_answers_match_gt': True, 'frozen_v7_hashes_unchanged': len(frozen['files']), 'candidate_counts': [24, 24], 'human_approval': False})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
