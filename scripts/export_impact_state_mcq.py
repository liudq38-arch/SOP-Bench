import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_jsonl, save_json, save_jsonl
from impact_qa.state_qa import evaluation_input


def main(args):
    packets = read_jsonl(args.input)
    candidates, evaluation = [], []
    names = {-1: 'Incorrectly installed.', 0: 'Not installed.', 1: 'Correctly installed.'}
    for packet in packets:
        target = packet['target']
        question = 'What was the installation status of the ' + target['component_id'].replace('_', ' ') + ' at the end of this segment?'
        states = [-1, 0, 1]
        seed = int(hashlib.sha256(packet['event_id'].encode()).hexdigest()[:16], 16)
        random.Random(seed).shuffle(states)
        options = {chr(65 + i): names[s] for i, s in enumerate(states)}
        correct = chr(65 + states.index(target['state_at_end']))
        qa_id = packet['event_id'] + '__asr_mcq_v10_1'
        fact = packet['answer_contract']['target_at_end']
        row = {'qa_id': qa_id, 'event_id': packet['event_id'], 'question': question, 'options': options, 'correct_answer': correct, 'answer_text': names[target['state_at_end']], 'source_state': target['state_at_end'], 'source_assertion': fact, 'creation_method': 'deterministic_native_ASR_state_to_three_choice_question', 'taxonomy': 'IMPACT ASR component states; not EgoErrorVQA error-category taxonomy', 'review_status': 'pending_human_review', 'visual_review_status': 'not_independently_reviewed_as_MCQ; use linked open-QA review for triage only'}
        assert len(set(options.values())) == 3 and options[correct] == names[fact['state']]
        candidates.append(row)
        model_input = evaluation_input(packet, {'question': question}, qa_id)
        row['evaluation_id'] = model_input['qa_id']
        model_input['options'] = options
        evaluation.append(model_input)
    folder = OUT / args.version
    save_jsonl(folder / 'state_mcq_candidates.jsonl', candidates)
    save_jsonl(folder / 'state_mcq_evaluation_inputs.jsonl', evaluation)
    save_json(REPORTS / 'v10_1_mcq_first10.json', candidates[:10])
    summary = {'qa_count': len(candidates), 'state_distribution': dict(Counter(r['source_state'] for r in candidates)), 'answer_position_distribution': dict(Counter(r['correct_answer'] for r in candidates)), 'format_checks_passed': True, 'human_reviewed': 0, 'scope': 'Three native ASR states; deterministic conversion, no measured MCQ accuracy; source -1 is not a PPR anomaly label.'}
    save_json(REPORTS / 'v10_1_mcq_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=OUT / 'state_qa_inputs_v10_1/packets.jsonl')
    parser.add_argument('--version', default='state_v10_1')
    main(parser.parse_args())
