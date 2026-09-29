import copy
import unittest

from scripts.qualify_evidence_v17 import validate


class EvidenceQualificationTests(unittest.TestCase):
    def setUp(self):
        self.payload = {'allowed_target_image_ids': ['t1'], 'allowed_reference_image_ids': ['r1']}
        self.value = {'answerable': True, 'visual_grade': 3, 'answer': 'A screwdriver.', 'observations': [{'fact': 'A tool is lifted.', 'target_image_ids': ['t1'], 'reference_image_ids': []}], 'needs': ['none'], 'limitation': ''}

    def test_reference_cannot_substitute_target_evidence(self):
        value = copy.deepcopy(self.value)
        value['observations'][0].update(target_image_ids=[], reference_image_ids=['r1'])
        with self.assertRaises(ValueError):
            validate(value, self.payload)

    def test_unmet_need_cannot_pass(self):
        value = {**self.value, 'needs': ['identity_reference']}
        with self.assertRaises(ValueError):
            validate(value, self.payload)

    def test_confident_hold_is_inconsistent(self):
        value = {**self.value, 'answerable': False, 'needs': ['boundary']}
        with self.assertRaises(ValueError):
            validate(value, self.payload)


if __name__ == '__main__':
    unittest.main()
