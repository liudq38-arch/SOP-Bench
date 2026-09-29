import unittest

from impact_qa.tool_adjudication import route


class AdjudicationTests(unittest.TestCase):
    def test_model_abstention_requires_evidence_not_automatic_rejection(self):
        primary = {'status': 'ok', 'proposed_retain': False}
        self.assertEqual(route(primary), 'needs_direct_evidence_review')
        review = {'reviewer': 'research_agent_direct_evidence', 'source_record': 'review.jsonl', 'note': 'Silver body leaves the table while colored drivers remain.', 'decision': 'supported'}
        self.assertEqual(route(primary, review), 'reviewed_exception_candidate')
        self.assertEqual(route(primary, review | {'decision': 'hold'}), 'hold_visual_evidence')

    def test_model_agreement_does_not_override_audit_or_run_error(self):
        primary = {'status': 'ok', 'proposed_retain': True}
        self.assertEqual(route(primary), 'pending_candidate_audit')
        review = {'reviewer': 'research_agent_direct_evidence', 'source_record': 'review.jsonl', 'note': 'Pickup remains occluded.', 'decision': 'hold'}
        self.assertEqual(route(primary, review), 'hold_visual_evidence')
        self.assertEqual(route(primary | {'status': 'error'}, review | {'decision': 'supported'}), 'hold_run_error')
        with self.assertRaises(ValueError):
            route(primary, review | {'reviewer': 'model_self_review', 'decision': 'supported'})
        with self.assertRaises(ValueError):
            route(primary, review | {'source_record': None})


if __name__ == '__main__':
    unittest.main()
