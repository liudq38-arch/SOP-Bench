import copy
import unittest

from impact_qa.common import ROOT, read_json
from scripts.run_step_v24 import validate


class StepQaContracts(unittest.TestCase):
    def setUp(self):
        self.payload = read_json(ROOT / 'outputs/impact_qa/step_v24/inputs/atr_403f880f747b22eb_ego.json')
        source = read_json(ROOT / 'outputs/impact_qa/step_v24/r1/results.json')[0]
        self.value = {'items': copy.deepcopy(source['qa']['items'] + source['held_items'])}
        for q in self.value['items']:
            q['source_ids'] = list(dict.fromkeys(q['source_ids'] + ['tas_s_18']))
            if q['kind'] == 'tool_identity':
                q['answer'] = 'I used a Phillips screwdriver.'

    def test_valid(self):
        validate(self.value, self.payload)

    def test_completion_without_state_rejected(self):
        q = self.value['items'][-1]
        q.update(verdict='yes', eligibility='answerable')
        with self.assertRaisesRegex(ValueError, 'unsupported_completion'):
            validate(self.value, self.payload)

    def test_generic_description_rejected(self):
        self.value['items'][0]['question'] = 'Describe the video.'
        with self.assertRaisesRegex(ValueError, 'generic_description'):
            validate(self.value, self.payload)

    def test_annotation_leakage_rejected(self):
        self.value['items'][1]['answer'] = 'The annotated tool is a screwdriver.'
        with self.assertRaisesRegex(ValueError, 'annotation_leakage'):
            validate(self.value, self.payload)

    def test_missing_step_provenance_rejected(self):
        self.value['items'][0]['source_ids'] = ['atr_ego']
        with self.assertRaisesRegex(ValueError, 'missing_step_name_source'):
            validate(self.value, self.payload)


if __name__ == '__main__':
    unittest.main()
