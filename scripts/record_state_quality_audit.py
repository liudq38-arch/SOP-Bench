import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, read_json, read_jsonl, save_json


DEST = REPORTS / 'state_v10_2_independent_audit'
DECISIONS = {
    ('open', 'adapter_done', 'completion'): ('retain_candidate', '状态与安装末段相符，可保留为基本完成题；画面不能证明扭矩等工程要求。'),
    ('open', 'adapter_done', 'reference_order'): ('revise_action_scope', '把壳体的ASR状态译成“安装壳体”缺少动作关系依据；TAS-S与概览显示该阶段实际安装转子组件。'),
    ('open', 'bearing_done', 'completion'): ('hold_visual_evidence', 'ASR支持state=1，末段显示停止拧紧并移开工具；细小接合面仍遮挡，不能独立确认“正确安装”的完整视觉依据。'),
    ('open', 'bearing_done', 'reference_order'): ('retain_candidate', '源状态及时间线支持适配板先于轴承板；只支持与给定图示一致，不证明该顺序唯一合法。'),
    ('open', 'bearing_incomplete', 'completion'): ('revise_task_scope', 'ASR=-1与原答案数值对应，但此时仍在安装；建议改成截至末帧是否完成，不能自动升级为操作错误。'),
    ('open', 'bearing_incomplete', 'reference_order'): ('deduplicate', '与同一trial的bearing_done顺序题具有相同问句、答案及状态断言；窗口不同但事件事实重复。'),
    ('open', 'handle_done', 'install_relation'): ('retain_candidate', '末段可见旋拧侧手柄及连接结果，与ASR和已有壳体关系解释一致；不证明规定扭矩。'),
    ('open', 'handle_done', 'reference_order'): ('retain_candidate', '已修订为单个locking lever，源状态与实际时间线支持其先于手柄；不能扩大为整套组件均正确。'),
    ('mcq', 'adapter_done', 'state'): ('retain_candidate', '三选项互斥且答案与ASR一致，末段可支持基本完成候选；不提供具体异常机制。'),
    ('mcq', 'bearing_done', 'state'): ('hold_visual_evidence', '答案忠实于ASR=1，但当前视角不足以独立检验细部安装正确性。'),
    ('mcq', 'bearing_incomplete', 'state'): ('hold_anomaly_semantics', 'Incorrectly installed是ASR=-1的忠实映射，但画面显示安装仍进行，不能据此断言发生了具体操作错误。'),
    ('mcq', 'handle_done', 'state'): ('retain_candidate', 'ASR=1且可见手柄连接结果，可保留作原生状态识别候选。'),
}


def main():
    manifest = read_json(DEST / 'frame_manifest.json')
    checks = read_json(DEST / 'objective_checks.json')
    boundaries = {r['event_id']: r for r in checks['endpoint_source_labels']}
    videos = {r['video_id']: r for r in manifest}
    files = {'open': OUT / 'state_v10_2/agent_reviewed_candidates.jsonl', 'mcq': OUT / 'state_v10_2/state_mcq_candidates.jsonl'}
    rows, proposals = [], []
    for form, source in files.items():
        for q in read_jsonl(source):
            video, event = q['event_id'].split('__')
            decision, reason = DECISIONS[(form, event, q['type'] if form == 'open' else 'state')]
            assertions = q['state_assertions'] if form == 'open' else [q['source_assertion']]
            asr = read_json(ANNOTATIONS / 'ASR/annotations' / (video + '_asr.json'))
            for a in assertions:
                index = next(i for i, c in enumerate(asr['components']) if c['name'] == a['component_id'])
                state = max((s for s in asr['state_sequence'] if s['frame'] <= a['at_frame']), key=lambda s: s['frame'])['state'][index]
                assert state == a['state'], q['qa_id']
            boards = [b['path'] for b in videos[video]['boards'] if b['kind'] == 'whole_recording_5s_overview' or b.get('event_id') == q['event_id']]
            assert all(Path(p).is_file() for p in boards)
            record = {
                'qa_id': q['qa_id'], 'event_id': q['event_id'], 'form': form,
                'question': q['question'], 'answer': q.get('answer', q.get('answer_text')),
                'options': q.get('options'), 'decision': decision, 'reason_zh': reason,
                'source_state_assertions_match': True, 'source_assertions': assertions,
                'endpoint_annotations': boundaries[q['event_id']], 'evidence_boards': boards,
                'reviewer_kind': 'research_agent_direct_text_source_and_frame_inspection',
                'review_protocol': 'Source-aware review of 22 boards; no new generator or reviewer API calls; not blind human review.',
                'human_review_status': 'pending_human_review', 'benchmark_ready': False,
            }
            if decision == 'deduplicate':
                record['duplicate_of'] = q['qa_id'].replace('__bearing_incomplete__', '__bearing_done__')
            rows.append(record)
            if decision in {'revise_action_scope', 'revise_task_scope'}:
                if decision == 'revise_action_scope':
                    question = 'Which did I work on first: installing the rotor assembly or attaching the adapter plate?'
                    answer = 'I worked on installing the rotor assembly first, then attached the adapter plate.'
                    segments = read_json(ANNOTATIONS / 'TAS-S/front' / (video + '.json'))['segments']
                    evidence = [s for s in segments if s['label'] in {'install_rotor_assembly', 'attach_adapter_plate'}]
                    assert max(s['f_end'] for s in evidence if s['label'] == 'install_rotor_assembly') < min(s['f_start'] for s in evidence if s['label'] == 'attach_adapter_plate')
                    scope = 'observed_action_order; not mandatory_order_or_correctness'
                else:
                    question = 'Had I finished installing the bearing plate by the end of this clip?'
                    answer = 'No, I was still working on its installation when the clip ended.'
                    evidence = boundaries[q['event_id']]
                    scope = 'completion_at_boundary; not operator_error'
                proposals.append({'original_qa_id': q['qa_id'], 'proposed_question': question, 'proposed_answer': answer, 'scope': scope, 'source_evidence': evidence, 'status': 'agent_proposal_pending_validation', 'applied_to_original': False})
    assert len(rows) == 36 and len({r['qa_id'] for r in rows}) == 36
    assert len(proposals) == 6
    with (DEST / 'per_question_audit.jsonl').open('w') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    with (DEST / 'revision_proposals.jsonl').open('w') as f:
        for row in proposals:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    fields = ['qa_id', 'form', 'question', 'answer', 'decision', 'reason_zh', 'human_review_status']
    with (DEST / 'per_question_audit.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        'audit_date': '2026-09-18', 'scope': 'v10.2 state and order candidates only; not a re-audit of v7-v9',
        'reviewer_kind': 'research_agent_direct_review', 'human_signed_off': False,
        'distinct_source_frames_inspected': sum(v['selected_distinct_frames'] for v in manifest),
        'boards_inspected': sum(len(v['boards']) for v in manifest), 'continuous_playback': False,
        'decisions': {form: dict(Counter(r['decision'] for r in rows if r['form'] == form)) for form in files},
        'source_state_checks_passed': len(rows), 'source_state_checks_are_semantic_accuracy': False,
        'readiness': {'small_development_candidates': 'selected_subset_only', 'scale_unchanged': False, 'formal_anomaly_benchmark': False},
        'inputs_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()},
        'revision_proposals': len(proposals), 'new_model_requests': 0,
    }
    save_json(DEST / 'audit_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
