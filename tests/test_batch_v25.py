import copy
import unittest

from impact_qa.batch_v25 import fixed_mcq, validate


class BatchContracts(unittest.TestCase):
    def pair(self):
        return {'items': [{'kind': 'step_completion', 'question': 'By the end of the clip, have I correctly installed the handle?', 'answer': 'Yes, the handle is correctly installed.', 'verdict': 'yes', 'eligibility': 'candidate', 'source_ids': ['asr_end'], 'visual_support': 'cannot_independently_confirm'}]}

    def test_gt_supported_not_visually_proven_is_candidate(self):
        validate(self.pair(), {'family': 'completion', 'state_at_end': 1})

    def test_completion_polarity(self):
        with self.assertRaisesRegex(ValueError, 'completion_gt_mismatch'):
            validate(self.pair(), {'family': 'completion', 'state_at_end': -1})

    def test_conflict_not_candidate(self):
        value = self.pair()
        value['items'][0]['visual_support'] = 'conflicts_with_gt'
        with self.assertRaisesRegex(ValueError, 'eligibility_conflict'):
            validate(value, {'family': 'completion', 'state_at_end': 1})

    def test_generic_description_rejected(self):
        value = self.pair()
        value['items'][0]['question'] = 'Describe this video.'
        with self.assertRaisesRegex(ValueError, 'public_prose_contract'):
            validate(value, {'family': 'completion', 'state_at_end': 1})

    def test_multiple_atr_labels_preserved(self):
        value = fixed_mcq({'family': 'atr', 'atr_labels': [1, 0, 1, 0, 0, 0], 'target_hand': 'left'})
        self.assertEqual(value[0]['correct_option_indices'], [1])
        self.assertEqual(value[1]['correct_option_indices'], [0, 2])

    def test_component_state_does_not_create_atr_mcq(self):
        self.assertEqual(fixed_mcq({'family': 'completion'}), [])

    def test_atr_needs_concrete_operation_reference(self):
        value = self.pair()
        value['items'][0].update(kind='execution_correctness', verdict='no', source_ids=['atr'])
        with self.assertRaisesRegex(ValueError, 'missing_operation_source'):
            validate(value, {'family': 'atr'})


if __name__ == '__main__':
    unittest.main()
