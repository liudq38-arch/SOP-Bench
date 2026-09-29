import copy
import unittest

from impact_qa.evidence_validation import validate_qualification, validate_stage
from impact_qa.quality_v16 import decide
from test_quality_v16 import QualityV16Tests


class EvidenceValidationTests(unittest.TestCase):
    def setUp(self):
        fixture = QualityV16Tests()
        fixture.setUp()
        self.c, self.stages = fixture.c, fixture.stages

    def test_long_private_text_is_preserved_with_warning(self):
        raw = copy.deepcopy(self.stages['visual_audit'])
        raw['claim_checks'][0]['observation'] = 'visible ' * 50
        value, warnings = validate_stage('visual_audit', raw, self.c, self.stages['generate'])
        self.assertEqual(value, raw)
        self.assertEqual(warnings[0]['words'], 50)
        self.assertEqual(raw['claim_checks'][0]['observation'], 'visible ' * 50)

    def test_long_text_never_masks_invalid_evidence(self):
        raw = copy.deepcopy(self.stages['visual_audit'])
        raw['claim_checks'][0].update(observation='visible ' * 50, image_ids=['invented'])
        with self.assertRaises(ValueError):
            validate_stage('visual_audit', raw, self.c, self.stages['generate'])

    def test_public_answer_limit_and_metadata_remain_hard(self):
        raw = copy.deepcopy(self.stages['generate'])
        raw['answer'] = 'word ' * 46
        with self.assertRaises(ValueError):
            validate_stage('generate', raw, self.c)
        raw = {**self.stages['generate'], 'open_question': 'According to the annotation, which tool?'}
        with self.assertRaises(ValueError):
            validate_stage('generate', raw, self.c)

    def test_source_conflict_survives_style_warning(self):
        raw = {**self.stages['source_audit'], 'reason': 'word ' * 80, 'blind_matches_gt': False}
        value, warnings = validate_stage('source_audit', raw, self.c)
        stages = {**self.stages, 'source_audit': value}
        self.assertTrue(warnings)
        self.assertEqual(decide(self.c, stages)['disposition'], 'quarantine')

    def test_qualification_reference_only_cannot_pass(self):
        payload = {'allowed_target_image_ids': ['t'], 'allowed_reference_image_ids': ['r']}
        value = {'answerable': True, 'visual_grade': 3, 'answer': 'A tool.', 'observations': [{'fact': 'word ' * 50, 'target_image_ids': [], 'reference_image_ids': ['r']}], 'needs': ['none'], 'limitation': ''}
        with self.assertRaises(ValueError):
            validate_qualification(value, payload)

    def test_private_text_character_guard_is_hard(self):
        raw = {**self.stages['source_audit'], 'reason': 'x' * 2001}
        with self.assertRaises(ValueError):
            validate_stage('source_audit', raw, self.c)


if __name__ == '__main__':
    unittest.main()
