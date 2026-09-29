import unittest

from impact_qa.common import OUT, read_jsonl
from impact_qa.evidence_package import CUTOFF_KINDS, blind_payload, generation_payload


class EvidencePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packages = read_jsonl(OUT / 'evidence_v17_inputs/smoke_packages.jsonl')

    def test_cutoff_has_no_future_evidence(self):
        for p in self.packages:
            if p['kind'] in CUTOFF_KINDS:
                cutoff = p['target_visual']['question_cutoff_frame']
                self.assertTrue(all(im['frame_index'] <= cutoff for im in p['target_visual']['images']))
                self.assertTrue(all(r['frame'] <= cutoff for r in p['private_context']['component_states']))
                self.assertTrue(all(r['start_frame'] <= cutoff for r in p['private_context']['atomic_actions']))

    def test_blind_payload_isolates_target_answers_and_context(self):
        for p in self.packages:
            payload = blind_payload(p, 'Test question?')
            self.assertEqual(set(payload), {'question', 'kind', 'reference_procedure', 'reference_examples', 'target_original_frame_interval_inclusive', 'fps', 'allowed_target_image_ids', 'allowed_reference_image_ids'})
            self.assertNotIn('candidate_graph', payload['reference_procedure'])
            self.assertFalse(payload['reference_procedure']['mandatory_prerequisite_edges'])

    def test_generation_has_gt_procedure_context_and_missing_data(self):
        for p in self.packages:
            payload = generation_payload(p)
            self.assertTrue(payload['answer_contract']['GT_answer'])
            self.assertEqual(len(payload['reference_procedure']['steps']), 5)
            self.assertIn('atomic_actions', payload['execution_context'])
            self.assertNotIn('source_catalog_for_provenance_only', payload['execution_context'])
            self.assertFalse(payload['eligibility']['cause_or_correction_enabled'])

    def test_references_disjoint_and_budget_valid(self):
        for p in self.packages:
            refs = p['public_reference']['action_examples']
            self.assertTrue(all(im['source_video'] != p['video_id'] for im in refs))
            self.assertLessEqual(len(refs) + len(p['target_visual']['images']), 32)
            self.assertEqual(p['eligibility']['visual_sufficiency'], 'not_yet_verified')
            self.assertFalse(p['eligibility']['new_generation_allowed'])


if __name__ == '__main__':
    unittest.main()
