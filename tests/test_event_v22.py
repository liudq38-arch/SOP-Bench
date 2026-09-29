import unittest

from impact_qa.event_v22 import render_answer, validate


class EvidenceContractTest(unittest.TestCase):
    def setUp(self):
        self.frames = [{'frame_id': 'a', 'source_pts_s': 1.0}, {'frame_id': 'b', 'source_pts_s': 2.0}]
        self.payload = {'allowed_core_frame_ids': ['a', 'b']}
        self.fact = {'kind': 'transition', 'hand': 'right', 'text': 'The hand moves toward the tool.', 'evidence_frame_ids': ['a', 'b'], 'confidence': 'high'}

    def test_unseen_id_rejected(self):
        self.fact['evidence_frame_ids'] = ['a', 'hidden']
        with self.assertRaises(Exception):
            validate('observe', {'facts': [self.fact], 'unknowns': []}, self.payload, self.frames)

    def test_reversed_transition_rejected(self):
        self.fact['evidence_frame_ids'] = ['b', 'a']
        with self.assertRaisesRegex(ValueError, 'transition_order'):
            validate('observe', {'facts': [self.fact], 'unknowns': []}, self.payload, self.frames)

    def test_single_frame_transition_rejected(self):
        self.fact['evidence_frame_ids'] = ['b']
        with self.assertRaisesRegex(ValueError, 'transition_order'):
            validate('observe', {'facts': [self.fact], 'unknowns': []}, self.payload, self.frames)

    def test_duplicate_verdict_rejected(self):
        payload = {'claims': [{'event_id': 'one'}, {'event_id': 'two'}]}
        v = {'claim_id': 'one', 'verdict': 'supported', 'reason': 'Visible.', 'evidence_frame_ids': ['a']}
        with self.assertRaisesRegex(ValueError, 'duplicate_verdicts'):
            validate('verify', {'verdicts': [v, v], 'omissions': []}, payload, self.frames)

    def test_answer_cannot_add_prose(self):
        events = [{'event_id': 'one', 'text': 'The right hand approaches the opening.'}]
        selected = {'status': 'answerable', 'question': 'What happens?', 'ordered_event_ids': ['one']}
        self.assertEqual(render_answer(selected, events)['answer'], events[0]['text'])
        self.assertFalse(render_answer(selected, events)['formal_release'])


if __name__ == '__main__':
    unittest.main()
