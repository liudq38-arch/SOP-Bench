import unittest

from impact_qa.history_v23 import history_input, validate_integration, validate_qa


class HistoryContractTest(unittest.TestCase):
    def test_recent_context_bounded_and_latest_state_used(self):
        rows = [{'clip_id': str(i), 'source_interval_s': [i * 2, i * 2 + 2], 'description': str(i), 'events': [], 'uncertainties': [], 'memory_after': {'summary': str(i)}} for i in range(5)]
        result = history_input(rows)
        self.assertEqual([r['clip_id'] for r in result['recent_history']], ['3', '4'])
        self.assertEqual(result['memory_before']['summary'], '4')
        self.assertEqual(len(rows), 5)

    def test_integration_cannot_silently_drop_event(self):
        with self.assertRaisesRegex(ValueError, 'event_coverage'):
            validate_integration({'sections': [{'event_ids': ['a']}]}, [{'event_id': 'a'}, {'event_id': 'b'}])

    def test_no_forced_occurrence_or_order_question(self):
        validate_qa({'items': [{'kind': 'event_description'}]})

    def test_main_description_required(self):
        with self.assertRaisesRegex(ValueError, 'qa_kind_contract'):
            validate_qa({'items': [{'kind': 'observed_order'}]})


if __name__ == '__main__':
    unittest.main()
