import copy
import html
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.state_qa import evaluation_input, validate_pair


def main():
    folder = OUT / 'state_v10_2'
    original = read_jsonl(folder / 'open_candidates.jsonl')
    packets = {p['event_id']: p for p in read_jsonl(OUT / 'state_qa_inputs_v10_1/packets.jsonl')}
    audit = read_json(REPORTS / 'state_v10_2_agent_audit.json')
    decisions = {a['qa_id']: a for a in audit['items']}
    candidates, evaluation, revisions = [], [], []
    cards = ['<!doctype html><meta charset="utf-8"><title>IMPACT QA agent review</title><style>body{font:16px sans-serif;max-width:1100px;margin:auto;line-height:1.5}article{border-top:1px solid #aaa;padding:20px 0}video,img{max-width:100%}pre{white-space:pre-wrap}</style><h1>IMPACT 安装与顺序 QA 开发审阅包</h1><p>24对开放题；15条保留候选，3条代理收窄范围，6条需要更清楚的视觉证据。全部待真人审核。顺序题只比较所提供图示，不能把所有不同顺序当作异常。</p><p><a href="review.html">未经代理修改的模型原始输出</a></p>']
    for source in original:
        row = copy.deepcopy(source)
        item = decisions[row['qa_id']]
        row['agent_review'] = item
        row['original_qa_id'] = row['qa_id']
        if item['decision'] == 'revise_scope':
            row['qa_id'] += '__agent_scope_revision'
            row['question'] = item['proposed_question']
            row['answer'] = item['proposed_answer']
            row['reference_claims'] = item['proposed_reference_claims']
            row['original_machine_review'] = row.pop('machine_review')
            row['machine_review'] = {'decision': 'not_rerun_after_agent_scope_revision', 'human_review_required': True}
            row['creation_method'] = 'research_agent_scope_revision_of_source_assisted_model_candidate'
            revisions.append(row)
        packet = packets[row['event_id']]
        errors = validate_pair(packet, row)
        assert not errors, (row['qa_id'], errors)
        model_input = evaluation_input(packet, row, row['qa_id'])
        row['evaluation_id'] = model_input['qa_id']
        row['review_status'] = 'pending_human_review'
        candidates.append(row)
        evaluation.append(model_input)
        media = '../state_qa_inputs_v10/media/' + row['event_id']
        cards.append('<article><h2>' + html.escape(row['event_id']) + '</h2><p>' + html.escape(row['question']) + '</p><p>' + html.escape(row['answer']) + '</p><p><b>代理检查：</b>' + html.escape(item['decision'] + ' — ' + item['reason']) + '</p><video controls preload="none" src="' + media + '/clip.mp4"></video><details><summary>精确帧与来源</summary><img loading="lazy" src="' + media + '/contact.jpg"><pre>' + html.escape(json.dumps({'state_assertions': row['state_assertions'], 'claims': row['reference_claims']}, ensure_ascii=False, indent=2)) + '</pre></details></article>')
    save_jsonl(folder / 'agent_reviewed_candidates.jsonl', candidates)
    save_jsonl(folder / 'agent_evaluation_inputs.jsonl', evaluation)
    save_jsonl(folder / 'agent_priority_candidates.jsonl', [q for q in candidates if q['agent_review']['decision'] != 'needs_visual_evidence'])
    save_jsonl(folder / 'agent_needs_visual_evidence.jsonl', [q for q in candidates if q['agent_review']['decision'] == 'needs_visual_evidence'])
    save_jsonl(folder / 'agent_scope_revisions.jsonl', revisions)
    (folder / 'review_agent.html').write_text('\n'.join(cards))
    mcq = read_jsonl(folder / 'state_mcq_candidates.jsonl')
    mcq_inputs = read_jsonl(folder / 'state_mcq_evaluation_inputs.jsonl')
    assert {q['evaluation_id'] for q in mcq} == {q['qa_id'] for q in mcq_inputs}
    assert all(q['options'][q['correct_answer']] == q['answer_text'] for q in mcq)
    forbidden = {'answer', 'answer_contract', 'state_assertions', 'source_assertion', 'source_state', 'correct_answer', 'answer_text', 'reference_claims', 'component_states', 'reference_annotations', 'machine_review', 'computed_comparisons', 'candidate_graph'}
    def inspect(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    for row in evaluation + mcq_inputs:
        inspect(row)
        assert Path(row['video']).is_file()
        assert '__' not in row['qa_id'] and '__' not in row['video']
    result = {'open_qa': len(candidates), 'state_mcq': len(mcq), 'agent_decisions': dict(Counter(q['agent_review']['decision'] for q in candidates)), 'agent_revisions': len(revisions), 'priority_open_candidates': 18, 'unique_open_questions': len({q['question'] for q in candidates}), 'evaluation_field_and_identifier_isolation': 'pass', 'state_assertions': 'pass', 'human_reviewed': 0}
    save_json(REPORTS / 'state_v10_2_agent_package_validation.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
