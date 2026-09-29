import unittest

from scripts.run_completion_v24 import validate


class CompletionContracts(unittest.TestCase):
    def pair(self, verdict):
        return {'items': [{'question': 'Have I correctly installed the anti-vibration handle by the end of this clip?', 'answer': 'Yes, I have correctly installed the handle.' if verdict == 'yes' else 'No, the handle is not correctly installed.', 'verdict': verdict}]}

    def test_final_correct_state(self):
        validate(self.pair('yes'), {'state_at_end': 1})

    def test_misassembled_is_not_absent(self):
        validate(self.pair('no'), {'state_at_end': -1})

    def test_polarity_cannot_override_gt(self):
        with self.assertRaisesRegex(ValueError, 'state_polarity_mismatch'):
            validate(self.pair('yes'), {'state_at_end': -1})

    def test_completion_cannot_generalize_to_device(self):
        pair = self.pair('yes')
        pair['items'][0]['answer'] = 'Yes, the entire device is finished.'
        with self.assertRaisesRegex(ValueError, 'provenance_leak_or_scope'):
            validate(pair, {'state_at_end': 1})


if __name__ == '__main__':
    unittest.main()
