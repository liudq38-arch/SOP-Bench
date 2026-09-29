import copy
import unittest

from impact_qa.v26_data import CONFIG, FOLDER, boundaries, changes, clip_errors, clips_with_actions, fully_covered, merged_intervals, normal_scope, read_json, read_jsonl
from impact_qa.v26_questions import build_questions, fixed_mcq, relation, state_at, validate_generated, validate_plan


class ComponentV26Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read_jsonl(FOLDER / 'manifest.jsonl')

    def case(self, index=0):
        clip = self.manifest[index]
        return read_json(FOLDER / 'trials' / (clip['video_id'] + '.json')), clip

    def generated(self, plans, arm='A'):
        return {'items': [{'question_id': q['question_id'], 'units': [{'fact_id': f['fact_id'], 'text': f['reference_text']} for f in q['reference_facts']], 'visual_support': 'not_applicable' if arm == 'A' else 'cannot_independently_confirm', 'evidence_note': ''} for q in plans]}

    def test_all_plans_and_literal_reference_answers(self):
        for clip in self.manifest:
            t = read_json(FOLDER / 'trials' / (clip['video_id'] + '.json'))
            q, mcq, _ = build_questions(t, clip)
            validate_plan(t, clip, q, mcq)
            validate_generated(self.generated(q), q, 'A')

    def test_without_asr_still_has_sequence_inventory_order_duration(self):
        t, c = self.case(1)
        q, _, _ = build_questions(t, c)
        self.assertFalse(t['has_asr'])
        self.assertEqual({x['kind'] for x in q}, {'action_sequence', 'tools_parts', 'observed_order', 'duration'})

    def test_action_sequence_starts_with_overall_operation_without_timestamps(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        sequence = next(item for item in q if item['kind'] == 'action_sequence')
        self.assertEqual(sequence['reference_facts'][0]['role'], 'overall')
        self.assertIn('Overall,', sequence['reference_answer'])
        self.assertNotRegex(sequence['reference_answer'], r'\[\d+\.\d+–')
        self.assertTrue(all(item.get('event_ids') for item in sequence['reference_facts'][1:]))

    def test_action_sequence_timestamp_is_rejected(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        v = self.generated(q)
        v['items'][0]['units'][0]['text'] += ' at 1.0 seconds.'
        with self.assertRaisesRegex(ValueError, 'action_sequence_timestamp'):
            validate_generated(v, q, 'A')

    def test_initial_state_is_not_a_completion_event(self):
        doc = {'components': [{'name': 'handle'}], 'state_sequence': [{'frame': 0, 'state': [1]}, {'frame': 5, 'state': [1]}, {'frame': 10, 'state': [0]}]}
        self.assertEqual([(x['frame'], x['state']) for x in changes(doc)], [(10, 0)])

    def test_no_future_state_lookahead(self):
        t = {'state_rows': [{'frame': 0, 'state': [0]}, {'frame': 10, 'state': [1]}]}
        self.assertEqual(state_at(t, 9)['state'], [0])
        self.assertEqual(state_at(t, 10)['state'], [1])

    def test_all_source_frames_are_partitioned_once(self):
        for vid in {c['video_id'] for c in self.manifest}:
            t = read_json(FOLDER / 'trials' / (vid + '.json'))
            clips = boundaries(t)
            if t['workflow'] == 'assemble':
                self.assertEqual(clips[0]['start_frame'], 0)
                self.assertEqual(clips[-1]['end_frame_exclusive'], t['frame_count'])
                self.assertTrue(all(a['end_frame_exclusive'] == b['start_frame'] for a, b in zip(clips, clips[1:])))
            else:
                self.assertTrue(clips)
                self.assertTrue(all(c['boundary']['reason'] == 'component_disassembly_onset_minus4s_completion_plus4s' for c in clips))
                self.assertTrue(any(c['boundary']['overlaps_clip_ids'] for c in clips) or len(clips) == 1)

    def test_disassembly_preroll_is_three_to_five_seconds(self):
        for clip in read_jsonl(FOLDER / 'clips.jsonl'):
            if clip['workflow'] == 'disassemble':
                self.assertGreaterEqual(clip['boundary']['preroll_s'], 0)
                self.assertLessEqual(clip['boundary']['preroll_s'], 4.001)
                self.assertGreaterEqual(clip['boundary']['tail_s'], 0)
                self.assertLessEqual(clip['boundary']['tail_s'], 4.001)

    def test_parallel_installation_not_cut_at_earlier_completion(self):
        t = {'fps': 10, 'frame_count': 160, 'workflow': 'assemble', 'has_asr': True, 'video_id': 'v', 'trial_id': 't', 'view': 'front', 'source_video': 'v.mp4', 'state_changes': [{'frame': 20, 'state': 1, 'component': 'a', 'source_id': 'sa'}, {'frame': 80, 'state': 1, 'component': 'b', 'source_id': 'sb'}], 'episodes': [{'start_frame': 0, 'end_frame_exclusive': 90, 'source_ids': ['step']}]}
        clips = boundaries(t)
        self.assertNotIn(40, [c['end_frame_exclusive'] for c in clips])
        self.assertGreaterEqual(clips[0]['end_frame_exclusive'], 100)

    def test_disassembly_windows_are_independent(self):
        t = {'fps': 10, 'frame_count': 200, 'workflow': 'disassemble', 'has_asr': True, 'video_id': 'v', 'trial_id': 't', 'view': 'front', 'source_video': 'v.mp4', 'episodes': [], 'component_operations': [
            {'operation_id': 'a', 'operation_ids': ['a'], 'component_indices': [0], 'components': ['first'], 'onset_frame': 50, 'completion_frame': 100, 'end_frame_exclusive': 101, 'completion_known': True, 'source_ids': []},
            {'operation_id': 'b', 'operation_ids': ['b'], 'component_indices': [1], 'components': ['second'], 'onset_frame': 80, 'completion_frame': 130, 'end_frame_exclusive': 131, 'completion_known': True, 'source_ids': []},
        ]}
        clips = boundaries(t)
        self.assertEqual(len(clips), 2)
        self.assertEqual(clips[0]['start_frame'], 10)
        self.assertEqual(clips[0]['end_frame_exclusive'], 141)
        self.assertEqual(clips[1]['start_frame'], 40)
        self.assertEqual(clips[1]['end_frame_exclusive'], 171)
        self.assertTrue(clips[0]['boundary']['overlaps_clip_ids'])

    def test_short_errors_never_become_correct(self):
        event = {'event_id': 'e', 'action': 'pick_up_tool', 'start_frame': 0, 'end_frame_exclusive': 30, 'hand': 'left', 'phase': 'normal', 'labels': [0]*6, 'source_ids': ['s']}
        t = {'events': [event], 'raw_errors': [{'start_frame': 5, 'end_frame_exclusive': 10, 'hand': 'left'}]}
        self.assertIsNone(normal_scope(t, {'start_frame': 0, 'end_frame_exclusive': 30}))

    def test_recovery_is_not_correct(self):
        event = {'event_id': 'e', 'action': 'pick_up_tool', 'start_frame': 0, 'end_frame_exclusive': 30, 'hand': 'left', 'phase': 'recovery', 'labels': [0]*6, 'source_ids': ['s']}
        self.assertIsNone(normal_scope({'events': [event], 'raw_errors': []}, {'start_frame': 0, 'end_frame_exclusive': 30}))

    def test_multilabel_mcq_and_mutual_exclusion(self):
        e = {'event_id': 'e', 'action': 'pick_up_tool', 'start_frame': 0, 'end_frame_exclusive': 60, 'hand': 'left', 'phase': 'anomaly', 'labels': [1, 0, 0, 0, 1, 0], 'source_ids': ['atomic']}
        a = dict(e, event_id='a', source_ids=['atr'])
        c = {'clip_id': 'c', 'start_frame': 0, 'end_frame_exclusive': 60, 'fps': 30}
        out = fixed_mcq({'events': [e], 'errors': [a], 'raw_errors': [a]}, c)
        self.assertEqual(out[0]['correct_option_ids'], ['B', 'F'])
        self.assertEqual(len(out[0]['options']), 7)

    def test_merged_atr_mismatch_not_propagated(self):
        e = {'event_id': 'e', 'action': 'pick_up_tool', 'start_frame': 0, 'end_frame_exclusive': 60, 'hand': 'left', 'phase': 'anomaly', 'labels': [1, 0, 0, 0, 0, 0], 'source_ids': ['s']}
        a = dict(e, labels=[1, 1, 0, 0, 0, 0])
        self.assertEqual(fixed_mcq({'events': [e], 'errors': [a], 'raw_errors': [a]}, {'clip_id': 'c', 'start_frame': 0, 'end_frame_exclusive': 60, 'fps': 30}), [])

    def test_partial_atr_not_reclassified_from_cut_duration(self):
        a = {'start_frame': 0, 'end_frame_exclusive': 60}
        self.assertEqual(clip_errors({'errors': [a]}, {'start_frame': 30, 'end_frame_exclusive': 60}), [])

    def test_exact_threshold_frame_policy(self):
        fps = 30
        self.assertTrue(44 + 1e-9 < CONFIG['minimum_error_seconds'] * fps)
        self.assertFalse(45 + 1e-9 < CONFIG['minimum_error_seconds'] * fps)

    def test_missing_sequence_unit_rejected(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        v = self.generated(q)
        v['items'][0]['units'].pop()
        with self.assertRaisesRegex(ValueError, 'fact_coverage'):
            validate_generated(v, q, 'A')

    def test_wrong_tool_rejected(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        v = self.generated(q)
        v['items'][0]['units'][0]['text'] = 'I pick up an imaginary tool with my left hand.'
        with self.assertRaisesRegex(ValueError, 'missing_entity'):
            validate_generated(v, q, 'A')

    def test_flipped_completion_rejected(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        v = self.generated(q)
        for row, plan in zip(v['items'], q):
            if plan['kind'] == 'step_completion':
                text = row['units'][0]['text']
                row['units'][0]['text'] = ('No.' if text.startswith('Yes.') else 'Yes.') + text.split('.', 1)[1]
                break
        with self.assertRaisesRegex(ValueError, 'polarity'):
            validate_generated(v, q, 'A')

    def test_wrong_duration_rejected(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        v = self.generated(q)
        for row, plan in zip(v['items'], q):
            if plan['kind'] == 'duration':
                row['units'][0]['text'] = 'The operation lasts 9999 seconds.'
                break
        with self.assertRaisesRegex(ValueError, 'numeric'):
            validate_generated(v, q, 'A')

    def test_arm_a_cannot_claim_visual_support(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        v = self.generated(q, 'B')
        with self.assertRaisesRegex(ValueError, 'arm_a_visual'):
            validate_generated(v, q, 'A')

    def test_overlapping_actions_are_not_before(self):
        self.assertEqual(relation({'start_frame': 0, 'end_frame_exclusive': 10}, {'start_frame': 5, 'end_frame_exclusive': 20}), 'overlap')

    def test_endpoint_adjacency_is_before(self):
        self.assertEqual(relation({'start_frame': 0, 'end_frame_exclusive': 10}, {'start_frame': 10, 'end_frame_exclusive': 20}), 'before')

    def test_full_clip_selection_requires_a_non_null_tasb_action(self):
        clips = [
            {'clip_id': 'action', 'start_frame': 0, 'end_frame_exclusive': 10},
            {'clip_id': 'null', 'start_frame': 10, 'end_frame_exclusive': 20},
        ]
        trial = {'events': [
            {'action': 'tighten', 'start_frame': 2, 'end_frame_exclusive': 4},
            {'action': 'null', 'start_frame': 12, 'end_frame_exclusive': 18},
        ]}
        self.assertEqual([clip['clip_id'] for clip in clips_with_actions(trial, clips)], ['action'])

    def test_order_duration_questions_do_not_leak_timestamps(self):
        t, c = self.case()
        q, _, _ = build_questions(t, c)
        for plan in q:
            if plan['kind'] in ['observed_order', 'duration']:
                self.assertNotRegex(plan['question'], r'\d+\.\d+')


if __name__ == '__main__':
    unittest.main()
