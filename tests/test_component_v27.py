import os
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
os.environ['IMPACT_V26_CONFIG'] = 'configs/impact_qa/component_v27_video_gt_r7p2.json'

from impact_qa.v27_media import _valid_presentation_indexes, select_source_frames
from impact_qa.v27_pipeline import _chunks, anomaly_visual_schema, apply_selection_budget, compact_candidates, compact_plans, selection_payload, validate_anomaly_visual
from impact_qa.v27_questions import _distinct_targets, _operation_windows, _specific_tool_names, _summary_fact, validate_generated, validate_selection
from impact_qa.structured_video_client import StructuredVideoPool
from impact_qa.common import fingerprint, read_json


class ComponentV27Tests(unittest.TestCase):
    def test_long_atr_segments_get_in_interval_source_frames(self):
        clip = {'clip_id': 'c', 'start_frame': 0, 'end_frame_exclusive': 900, 'fps': 30}
        trial = {
            'errors': [{'event_id': 'atr1', 'start_frame': 300, 'end_frame_exclusive': 600, 'duration_s': 10.0}],
            'events': [{'event_id': 'tasb1', 'action': 'install', 'start_frame': 610, 'end_frame_exclusive': 700}],
        }
        indexes, reasons, errors = select_source_frames(trial, clip, 64)
        self.assertLessEqual(len(indexes), 64)
        self.assertEqual([e['event_id'] for e in errors], ['atr1'])
        self.assertTrue(any('atr_center:atr1' in reasons[str(i)] for i in indexes if 300 <= i < 600))
        self.assertTrue(any(300 <= i < 600 for i in indexes))
        self.assertTrue(any(610 <= i < 700 for i in indexes))

    def test_atr_priority_frames_never_push_video_over_frame_cap(self):
        errors = [
            {'event_id': f'atr{index}', 'start_frame': index * 200, 'end_frame_exclusive': index * 200 + 180, 'duration_s': 6.0}
            for index in range(40)
        ]
        clip = {'clip_id': 'many-errors', 'start_frame': 0, 'end_frame_exclusive': 8000, 'fps': 30}
        indexes, _, qualifying = select_source_frames({'errors': errors, 'events': []}, clip, 64)
        self.assertEqual(len(qualifying), 40)
        self.assertLessEqual(len(indexes), 64)
        centers = {(error['start_frame'] + error['end_frame_exclusive'] - 1) // 2 for error in errors}
        self.assertTrue(centers.issubset(set(indexes)))

    def test_short_clip_media_sampling_pads_to_three_temporal_frames(self):
        trial = {'fps': 30, 'events': [], 'errors': []}
        clip = {'clip_id': 'short', 'start_frame': 7, 'end_frame_exclusive': 8}
        indexes, reasons, qualifying = select_source_frames(trial, clip, 64)
        self.assertEqual(indexes, [7, 7, 7])
        self.assertEqual(reasons['7'], ['uniform_context', 'uniform_fill'])
        self.assertEqual(qualifying, [])

    def test_video_frame_mapping_accepts_ordered_downsampled_indexes(self):
        self.assertTrue(_valid_presentation_indexes([0, 4, 8, 79], 80))
        self.assertFalse(_valid_presentation_indexes([0, 4, 4, 79], 80))
        self.assertFalse(_valid_presentation_indexes([0, 8, 4], 80))
        self.assertFalse(_valid_presentation_indexes([0, 80], 80))

    def test_generic_tool_label_does_not_mask_specific_gt_tool(self):
        clip = {'clip_id': 'tools', 'workflow': 'disassemble', 'start_frame': 0, 'end_frame_exclusive': 100}
        events = [
            {'noun': 'tool', 'source_ids': ['generic-tool']},
            {'noun': 'phillips_screwdriver', 'source_ids': ['specific-tool']},
            {'noun': 'bearing_plate', 'source_ids': ['component']},
        ]
        fact = _summary_fact({'state_changes': []}, clip, events)
        self.assertEqual(fact['tools'], ['phillips screwdriver'])
        self.assertNotIn('tool', fact['tools'])
        self.assertEqual(_specific_tool_names(['tool']), ['tool'])

    def test_selection_requires_atr_interval_evidence(self):
        candidates = [
            {'candidate_id': 'mcq', 'kind': 'mcq_anomaly_clip', 'gt_facts': [{'event_id': 'atr1', 'interval_frames': [100, 200]}]},
            {'candidate_id': 'overall', 'kind': 'overall_operation', 'gt_facts': []},
        ]
        frames = [{'frame_id': 'in', 'source_frame_index': 150}, {'frame_id': 'out', 'source_frame_index': 250}]
        value = {'items': [
            {'candidate_id': 'mcq', 'include': True, 'visual_support': 'supports_visible_outcome', 'evidence_frame_ids': ['in']},
            {'candidate_id': 'overall', 'include': False, 'visual_support': 'cannot_independently_confirm', 'evidence_frame_ids': []},
        ]}
        validate_selection(value, candidates, frames)
        value['items'][0]['evidence_frame_ids'] = ['out']
        with self.assertRaisesRegex(ValueError, 'evidence_outside_atr_intervals'):
            validate_selection(value, candidates, frames)

    def test_blind_visual_result_must_cite_frame_inside_event(self):
        mcq = {'qualifying_errors': [{'event_id': 'atr1', 'interval_frames': [100, 200]}]}
        frames = [{'frame_id': 'in', 'source_frame_index': 150}, {'frame_id': 'out', 'source_frame_index': 250}]
        value = {'items': [{'event_id': 'atr1', 'visible_abnormal_operation': True, 'evidence_frame_ids': ['in'], 'observed_description': 'The hand holds the tool away from the workpiece.'}]}
        validate_anomaly_visual(value, mcq, frames)
        value['items'][0]['evidence_frame_ids'] = ['out']
        with self.assertRaisesRegex(ValueError, 'in_interval_evidence'):
            validate_anomaly_visual(value, mcq, frames)

    def test_selection_payload_compacts_duplicate_gt_tables(self):
        clip = {'clip_id': 'c', 'workflow': 'assemble', 'duration_s': 10.0, 'start_frame': 100, 'fps': 30}
        candidates = [
            {'candidate_id': 'd', 'kind': 'detailed_operation', 'topic': 'Summarize the main phases.', 'answer_constraints': {}, 'selection_rule': 'select if useful', 'phase_count': 2, 'gt_facts': [{'fact_id': 'f1', 'reference_text': 'I pick up the wrench.', 'source_ids': ['source1'], 'event_ids': ['e1'], 'interval_s': [0.0, 1.0]}]},
            {'candidate_id': 'm', 'kind': 'mcq_anomaly_clip', 'question': 'Is there an anomaly?', 'selection_rule': 'select if visible', 'gt_facts': [{'event_id': 'a1', 'duration_s': 6.0, 'labels': [0, 0, 1, 0, 0, 0], 'source_ids': ['source2'], 'interval_frames': [120, 300]}]},
        ]
        media = {'sampled_frames': [{'frame_id': 'f0000120', 'source_frame_index': 120, 'local_pts_s': 2.0}]}
        payload = selection_payload(clip, {'events': [], 'errors': [], 'state_changes': []}, candidates, media)
        self.assertNotIn('gt_events', payload)
        self.assertNotIn('gt_errors', payload)
        self.assertNotIn('gt_state_changes', payload)
        detailed = payload['question_candidates'][0]['gt_facts'][0]
        self.assertNotIn('reference_text', detailed)
        self.assertEqual(detailed['fact_id'], 'f1')
        anomaly = payload['question_candidates'][1]['gt_facts'][0]
        self.assertEqual(anomaly['sampled_frame_ids'], ['f0000120'])
        self.assertIn('Handling', anomaly['anomaly_types'])

    def test_long_detail_candidate_is_gated_without_suppressing_other_questions(self):
        candidates = [
            {'candidate_id': 'd', 'kind': 'detailed_operation', 'phase_count': 9, 'gt_facts': [{}] * 65},
            {'candidate_id': 'o', 'kind': 'overall_operation', 'gt_facts': [{}]},
        ]
        model = {'items': [
            {'candidate_id': 'd', 'include': True, 'visual_support': 'supports_visible_outcome', 'evidence_frame_ids': [], 'reason': 'sequence is clear'},
            {'candidate_id': 'o', 'include': True, 'visual_support': 'supports_visible_outcome', 'evidence_frame_ids': [], 'reason': 'overview is clear'},
        ]}
        effective, gates = apply_selection_budget(model, candidates, 8)
        self.assertTrue(model['items'][0]['include'])
        self.assertFalse(effective['items'][0]['include'])
        self.assertTrue(effective['items'][1]['include'])
        self.assertEqual(gates[0]['phase_count'], 9)

    def test_prompt_marks_error_rules_and_normal_motion_boundary(self):
        select = (ROOT / 'prompts/impact_qa/v27r7p2/select.txt').read_text()
        generate = (ROOT / 'prompts/impact_qa/v27r7p2/generate.txt').read_text()
        review = (ROOT / 'prompts/impact_qa/v27r7p2/review.txt').read_text()
        blind = (ROOT / 'prompts/impact_qa/v27r7p2/mcq_visual.txt').read_text()
        self.assertIn('ERROR RULES', select)
        self.assertIn('Empty holding', select)
        self.assertIn('Conflicted placement/return', select)
        self.assertIn('not an error by itself', blind)
        self.assertIn('generate BOTH a natural question and its answer', generate)
        self.assertIn('at most four sentences and 95 words', generate)
        self.assertIn('one to three main objects', generate)
        self.assertIn('aggregated multi-component state interval', select)
        self.assertIn('single named operation episode', review)
        self.assertIn('one concise sentence of at most 20 words', blind)

    def test_many_mcq_visual_events_are_chunked_and_keep_short_evidence(self):
        events = list(range(19))
        chunks = _chunks(events, 8)
        self.assertEqual([len(chunk) for chunk in chunks], [8, 8, 3])
        self.assertEqual([event for chunk in chunks for event in chunk], events)
        schema = anomaly_visual_schema(['f1', 'f2', 'f3'], 8)
        item = schema['properties']['items']['items']
        self.assertEqual(item['properties']['evidence_frame_ids']['maxItems'], 2)

    def test_generated_answer_cannot_merge_location_specific_parts(self):
        plans = [{'candidate_id': 'q', 'kind': 'step_completion', 'answer_constraints': {'required_terms': ['bearing screw lowright', 'bearing screw topleft']}, 'reference_facts': [{'fact_id': 'f', 'required_phrases': ['bearing screw lowright', 'bearing screw topleft']}], 'selection_evidence_frame_ids': []}]
        value = {'items': [{'candidate_id': 'q', 'question': 'What did I install?', 'answer': 'I installed the bearing screws.', 'source_fact_ids': ['f'], 'visual_support': 'cannot_independently_confirm', 'evidence_frame_ids': [], 'evidence_note': ''}]}
        with self.assertRaisesRegex(ValueError, 'missing_grounded_term'):
            validate_generated(value, plans, [])

    def test_overall_answer_may_summarize_instead_of_listing_every_gt_item(self):
        plans = [{
            'candidate_id': 'overall', 'kind': 'overall_operation',
            'answer_constraints': {
                'required_terms': ['assembly'],
                'required_tool_options': ['phillips screwdriver', 'torx screwdriver'],
                'required_object_options': ['bearing plate', 'anti vibration handle'],
                'operation': 'assembly',
                'max_words': 55,
            },
            'reference_facts': [{
                'fact_id': 'f', 'required_phrases': ['assembly'],
                'parts': ['screw', 'washer'],
                'components': ['bearing screw lowright', 'bearing screw topleft', 'bearing plate', 'anti vibration handle'],
            }],
            'selection_evidence_frame_ids': [],
        }]
        value = {'items': [{
            'candidate_id': 'overall',
            'question': 'What does the clip show overall?',
            'answer': 'I assemble the gearbox with a phillips screwdriver, fitting the bearing plate and anti vibration handle.',
            'source_fact_ids': ['f'],
            'visual_support': 'cannot_independently_confirm',
            'evidence_frame_ids': [],
            'evidence_note': 'The sampled frames do not show all component details clearly.',
        }]}
        validate_generated(value, plans, [])
        value['items'][0]['answer'] = 'I assemble the gearbox and fit the bearing plate.'
        with self.assertRaisesRegex(ValueError, 'overall_tool_missing'):
            validate_generated(value, plans, [])

    def test_duration_uses_single_episode_not_multi_component_state_group(self):
        clip = {'start_frame': 0, 'end_frame_exclusive': 1000, 'fps': 30}
        trial = {
            'episodes': [
                {'start_frame': 10, 'end_frame_exclusive': 310, 'label': 'remove_adapter_plate', 'source_ids': ['s1']},
                {'start_frame': 500, 'end_frame_exclusive': 950, 'label': 'remove_adapter_plate', 'source_ids': ['s2']},
            ],
            'component_operations': [{
                'onset_frame': 10, 'end_frame_exclusive': 950, 'completion_known': True,
                'components': ['adapter_plate', 'M4_nut_plate_lowright', 'screw_adaptor_lowright'],
                'source_ids': ['s1', 's2'],
            }],
        }
        windows = _operation_windows(trial, clip)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]['target'], 'adapter plate')
        self.assertEqual(windows[0]['duration_s'], 15.0)
        self.assertEqual(windows[0]['basis'], 'tas_b_episode')

    def test_duration_ignores_short_and_unbounded_operations(self):
        clip = {'start_frame': 0, 'end_frame_exclusive': 500, 'fps': 30}
        trial = {'episodes': [
            {'start_frame': 10, 'end_frame_exclusive': 40, 'label': 'install_bearing_plate', 'source_ids': ['s1']},
            {'start_frame': 450, 'end_frame_exclusive': 520, 'label': 'install_lever', 'source_ids': ['s2']},
        ]}
        self.assertEqual(_operation_windows(trial, clip), [])

    def test_generation_input_contains_gt_facts_not_prebuilt_public_qa(self):
        candidate = {
            'candidate_id': 'q', 'kind': 'step_completion', 'topic': 'Ask whether installation was complete.',
            'answer_constraints': {'expected_polarity': 'no'},
            'reference_facts': [{'fact_id': 'f', 'reference_text': 'No. The adapter plate was uninstalled.', 'required_phrases': ['adapter plate'], 'verdict': 'no', 'queried_component': 'adapter plate', 'completed_components': ['bearing plate'], 'operation': 'installation'}],
        }
        payload = compact_plans([candidate])[0]
        self.assertNotIn('question', payload)
        self.assertNotIn('reference_text', payload['gt_facts'][0])
        self.assertEqual(payload['topic'], candidate['topic'])
        self.assertEqual(payload['gt_facts'][0]['verdict'], 'no')

    def test_negative_completion_answer_must_name_completed_component(self):
        plans = [{
            'candidate_id': 'c', 'kind': 'step_completion',
            'answer_constraints': {'expected_polarity': 'no', 'queried_component': 'adapter plate', 'completed_components': ['bearing plate']},
            'reference_facts': [{'fact_id': 'f', 'required_phrases': ['adapter plate', 'bearing plate'], 'verdict': 'no'}],
            'selection_evidence_frame_ids': [],
        }]
        value = {'items': [{
            'candidate_id': 'c', 'question': 'Was the adapter plate installation completed? If not, what was completed?',
            'answer': 'No. The adapter plate remained uninstalled, but the bearing plate installation was completed.',
            'source_fact_ids': ['f'], 'visual_support': 'cannot_independently_confirm', 'evidence_frame_ids': [], 'evidence_note': '',
        }]}
        validate_generated(value, plans, [])
        value['items'][0]['answer'] = 'Yes. The adapter plate was installed, and I completed the bearing plate installation.'
        with self.assertRaisesRegex(ValueError, 'completion_polarity'):
            validate_generated(value, plans, [])

    def test_order_targets_must_be_distinct_component_operations(self):
        self.assertFalse(_distinct_targets('screw', 'M4 screw'))
        self.assertFalse(_distinct_targets('screw', 'screw'))
        self.assertTrue(_distinct_targets('adapter plate', 'bearing plate'))


class StructuredClientRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_cache_entry_is_archived_and_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            config = {'model': 'test-model', 'base_urls': ['http://test/v1'], 'temperature': 0, 'top_p': 1, 'seed': 1, 'max_model_len': 4096}
            schema = {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'], 'additionalProperties': False}
            prompt = 'Return JSON.'
            payload = {'case_id': 'case'}
            prompt += '\nOutput schema:\n' + json.dumps(schema, separators=(',', ':'))
            text_payload = json.dumps(payload, ensure_ascii=False)
            request = {
                'model': config['model'],
                'messages': [
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': [{'type': 'text', 'text': text_payload}]},
                ],
                'temperature': config['temperature'],
                'top_p': config['top_p'],
                'seed': config['seed'],
                'max_tokens': 8,
                'chat_template_kwargs': {'enable_thinking': False},
                'response_format': {'type': 'json_schema', 'json_schema': {'name': 'retry_test', 'schema': schema, 'strict': True}},
            }
            key = fingerprint([request, 'model-checkpoint', None])
            (folder / 'api_cache').mkdir()
            (folder / 'api_cache' / f'{key}.json').write_text(json.dumps({'status': 'error', 'error': 'old failed result'}))

            def respond(_):
                return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok":true}'}}]})

            pool = object.__new__(StructuredVideoPool)
            pool.config = config
            pool.folder = folder
            pool.clients = [httpx.AsyncClient(base_url='http://test/v1', transport=httpx.MockTransport(respond))]
            pool.slots = asyncio.Queue()
            pool.slots.put_nowait(0)
            pool.identity = 'model-checkpoint'
            pool.tokenizer = type('Tokenizer', (), {'encode': lambda self, _: [1]})()
            pool.calls = []
            result = await pool.call('retry_test', 'Return JSON.', payload, schema, 8)
            await pool.close()

            self.assertEqual(result['status'], 'ok')
            self.assertTrue(result['retried_after_cached_failure'].startswith('api_cache_failures/'))
            self.assertEqual(len(list((folder / 'api_cache_failures').glob('*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
