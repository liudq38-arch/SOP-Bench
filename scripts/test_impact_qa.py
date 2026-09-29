import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, read_jsonl
from impact_qa.pipeline import validate_pairs
from impact_qa.validation import qualifies_for_review_pass, validate_evidence_graph, select_visual_facts, derive_pair_evidence


class EvidenceTests(unittest.TestCase):
    def test_missing_visual_source_is_rejected(self):
        observation = {'observations': [{'id': 'O1', 'evidence_ids': ['f1']}]}
        facts = {'facts': [{'id': 'F1', 'support': 'visual', 'observation_ids': ['O2']}]}
        self.assertIn('fact:F1:unknown_observation', validate_evidence_graph(observation, facts, [{'evidence_id': 'f1'}]))

    def test_annotation_only_answer_is_not_visual_pass(self):
        review = {'decision': 'pass', 'supported': True, 'visually_answerable': True, 'relevant_to_procedure': True, 'answer_leakage': False, 'duplicate': False}
        self.assertFalse(qualifies_for_review_pass({'answerability': 'annotation_only'}, review, []))
        self.assertTrue(qualifies_for_review_pass({'answerability': 'visible'}, review, []))
        self.assertFalse(qualifies_for_review_pass({'answerability': 'visible'}, review, ['missing_source']))

    def test_context_tool_use_cannot_prove_target_tool_use(self):
        pairs = {'qa_pairs': [{'question': 'What tool did I use?', 'answer': 'A screwdriver.', 'dimension': 'tool', 'supporting_fact_ids': ['F1'], 'evidence_ids': ['after']}]}
        facts = {'facts': [{'id': 'F1', 'usable_for_qa': True}]}
        images = [{'evidence_id': 'after', 'time_scope': 'CONTEXT_AFTER'}]
        self.assertIn('0:context_evidence_for_target_claim', validate_pairs(pairs, facts, images))

    def test_qa_frames_follow_visual_fact_chain(self):
        observation = {'observations': [{'id': 'O1', 'evidence_ids': ['f7']}]}
        facts = {'facts': [{'id': 'F1', 'support': 'visual', 'usable_for_qa': True, 'observation_ids': ['O1']}, {'id': 'F2', 'support': 'visual', 'usable_for_qa': True, 'observation_ids': []}]}
        selected, withheld = select_visual_facts(observation, facts, [{'evidence_id': 'f7'}])
        self.assertEqual([f['id'] for f in selected], ['F1'])
        self.assertEqual(withheld[0]['fact_id'], 'F2')
        generated = {'qa_pairs': [{'supporting_fact_ids': ['F1'], 'evidence_ids': ['invented']}]}
        self.assertEqual(derive_pair_evidence(generated, selected)['qa_pairs'][0]['evidence_ids'], ['f7'])

    def test_actual_split_and_target_intervals(self):
        dev = read_jsonl(OUT / 'development_events.jsonl')
        pilot = read_jsonl(OUT / 'pilot_events.jsonl')
        self.assertEqual((len(dev), len(pilot)), (20, 60))
        self.assertFalse({r['execution_id'] for r in dev} & {r['execution_id'] for r in pilot})
        for row in dev + pilot:
            self.assertLessEqual(row['context_start_s'], row['start_s'])
            self.assertLess(row['start_s'], row['end_s_exclusive'])
            self.assertLessEqual(row['end_s_exclusive'], row['context_end_s'])
            if row['phase'] == 'anomaly':
                self.assertTrue(row['anomaly_types'])


if __name__ == '__main__':
    unittest.main()
