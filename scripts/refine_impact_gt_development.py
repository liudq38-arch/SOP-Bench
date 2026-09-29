import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, fingerprint, read_jsonl, save_jsonl


VERBS = {'install': 'installing', 'attach': 'attaching', 'insert': 'inserting', 'align': 'aligning', 'dismount': 'dismounting', 'hold': 'holding', 'loosen': 'loosening', 'place': 'placing', 'remove': 'removing', 'thread': 'threading', 'tighten': 'tightening'}


def phrase(label):
    if label.startswith('screw_on_'):
        return 'screwing on the ' + label[9:].replace('_', ' ').replace('anti vibration', 'anti-vibration')
    if label.startswith('pick_up_'):
        return 'picking up the ' + label[8:].replace('_', ' ')
    if label.startswith('hand_'):
        return phrase(label[5:]) + ' by hand'
    if label.startswith('spin_'):
        return 'spinning the ' + label[5:].replace('_', ' ')
    verb, obj = label.split('_', 1)
    return VERBS[verb] + ' the ' + obj.replace('_', ' ').replace('anti vibration', 'anti-vibration')


def attributes_text(attrs):
    names = [a.replace('-', ' ') for a in attrs]
    joined = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]
    return joined[0].upper() + joined[1:] + (' error.' if len(names) == 1 else ' errors.')


def main():
    rows = []
    for original in read_jsonl(OUT / 'gt_v12_inputs/contracts.jsonl'):
        if original['kind'] not in ['observed_order', 'action_error_category', 'action_phase']:
            continue
        c = copy.deepcopy(original)
        facts = c['facts']
        if c['kind'] == 'observed_order':
            x, y = phrase(facts['first_action']), phrase(facts['second_action'])
            mcq = f'Which did I start first: {x} or {y}?'
            if c['answer_polarity'] == 'yes':
                q, answer = f'Did I start {x} before {y}?', f'Yes, I started {x} first.'
            elif c['answer_polarity'] == 'no':
                q, answer = f'Did I start {y} before {x}?', f'No, I started {x} before {y}.'
            else:
                q, answer = mcq, f'I started {x} first.'
            choices = [x.capitalize() + '.', y.capitalize() + '.', 'Both started at the same time.']
        else:
            action = phrase(facts['action'])
            hand = facts['hand']
            if c['kind'] == 'action_phase':
                q = f'Did I make an error while {action} with my {hand} hand?'
                mcq = f'Was I performing a normal action, making an error, or recovering while {action} with my {hand} hand?'
                answer, choices = c['canonical_answer'], c['choice_texts']
            else:
                q = f'What types of error occurred while I was {action} with my {hand} hand?'
                mcq = f'Which option gives the complete set of error types while I was {action} with my {hand} hand?'
                attrs = facts['error_attributes']
                vocabulary = ['timing', 'spatial', 'object-handling', 'wrong-part', 'wrong-tool', 'procedural']
                replacements = [a for a in vocabulary if a not in attrs][:2]
                choices = [attributes_text(attrs)] + [attributes_text(attrs[:-1] + [a]) for a in replacements]
                answer = choices[0]
        c.update(question_proposition=q, canonical_answer=answer, choice_texts=choices, mcq_question_proposition=mcq, parent_input_hash=original['input_hash'], refinement='grammatical_action_phrases_and_equal_cardinality_error_options')
        c['contract_hash'] = fingerprint({k: v for k, v in c.items() if k not in ['contract_hash', 'input_hash']})
        c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
        assert len(set(choices)) == 3
        rows.append(c)
    save_jsonl(OUT / 'gt_v12_1_inputs/contracts.jsonl', rows)
    print({'refined_contracts': len(rows)})


if __name__ == '__main__':
    main()
