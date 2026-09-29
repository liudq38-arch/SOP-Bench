import copy
import unittest

from impact_qa.quality_v16 import decide, public_payload, validate


class QualityV16Tests(unittest.TestCase):
    def setUp(self):
        self.c = {'kind': 'tool_identity', 'tool': 'wrench', 'correct_option': 1, 'references': [{}, {}], 'start_frame': 1, 'end_frame_inclusive': 3, 'image_refs': [{'evidence_id': 'a', 'frame_index': 1}, {'evidence_id': 'b', 'frame_index': 3}], 'canonical_answer': 'secret', 'facts': {'secret': True}}
        self.g = {'open_question': 'Which tool did I pick up?', 'answer': 'A wrench.', 'mcq_question': 'Which tool did I pick up?', 'visual_grade': 3, 'limitation': '', 'claims': [{'claim': 'I picked up a wrench.', 'source_ids': ['s0', 's1'], 'image_ids': ['a', 'b']}]}
        self.b = {'answer': 'A wrench.', 'visual_grade': 3, 'tool': 'wrench', 'before_id': 'a', 'after_id': 'b', 'image_ids': ['a', 'b'], 'observation': 'It left the surface.', 'limitation': ''}
        self.v = {'visual_grade': 3, 'answer_supported': True, 'blind_agrees': True, 'question_unambiguous': True, 'evidence_valid': True, 'claim_checks': [{'claim_index': 0, 'supported': True, 'image_ids': ['a', 'b'], 'observation': 'Visible.'}], 'supported_option_indices': [1], 'option_checks': [{'index': i, 'verdict': 'supported' if i == 1 else 'contradicted', 'reason': 'Shape.'} for i in range(3)], 'counterevidence': '', 'before_id': 'a', 'after_id': 'b'}
        self.s = {k: True for k in ['source_entails_answer', 'claims_entailed', 'question_preserves_scope', 'open_mcq_equivalent', 'no_answer_leakage', 'unique_correct_option', 'blind_matches_gt']}
        self.s.update(correct_option_index=1, unsupported_claims=[], reason='Entailed.')
        self.stages = dict(generate=self.g, blind=self.b, visual_audit=self.v, source_audit=self.s)

    def test_fake_or_reverse_evidence_rejected(self):
        for change in [{'after_id': 'Picture 2'}, {'before_id': 'b', 'after_id': 'a'}]:
            with self.assertRaises(ValueError):
                validate('blind', {**self.b, **change}, self.c)

    def test_missing_claim_and_inconsistent_option_rejected(self):
        for change in [{'claim_checks': []}, {'supported_option_indices': [0]}]:
            with self.assertRaises(ValueError):
                validate('visual_audit', {**self.v, **change}, self.c, self.g)

    def test_confident_conflict_cannot_pass(self):
        self.b['tool'] = 'screwdriver'
        self.assertEqual(decide(self.c, self.stages)['disposition'], 'quarantine')

    def test_uncertainty_or_extra_claim_cannot_pass(self):
        for key in ['visual_grade', 'tool']:
            stages = copy.deepcopy(self.stages)
            stages['blind'][key] = 2 if key == 'visual_grade' else 'unknown'
            self.assertEqual(decide(self.c, stages)['disposition'], 'quarantine')
        self.s['unsupported_claims'] = ['Invented torque.']
        self.assertEqual(decide(self.c, self.stages)['disposition'], 'quarantine')

    def test_boolean_strings_and_numeric_bools_rejected(self):
        for stage, value in [('blind', {**self.b, 'visual_grade': True}), ('source_audit', {**self.s, 'blind_matches_gt': 'true'})]:
            with self.assertRaises(ValueError):
                validate(stage, value, self.c)

    def test_blind_payload_and_unvalidated_status(self):
        self.assertEqual(set(public_payload(self.c, self.g['open_question'])), {'kind', 'question', 'clip_start_s', 'clip_end_s_exclusive', 'allowed_image_ids'})
        for stage, value in self.stages.items():
            validate(stage, value, self.c, self.g)
        result = decide(self.c, self.stages)
        self.assertEqual(result['disposition'], 'model_passed_unvalidated')
        self.assertFalse(result['formal_release'])
        self.assertIsNone(result['calibrated_probability'])


if __name__ == '__main__':
    unittest.main()
