import os
import unittest


os.environ.setdefault('IMPACT_V26_CONFIG', 'configs/impact_qa/component_v27_video_gt_r7p2.json')

from impact_qa.clip_repair import repair_clips
from impact_qa.v26_data import CONFIG, clip_record, source_end_cleanup_tail_reason


def trial(workflow, frame_count):
    return {
        'video_id': 'synthetic_' + workflow,
        'trial_id': 'synthetic',
        'view': 'front',
        'workflow': workflow,
        'fps': 30,
        'frame_count': frame_count,
        'source_video': 'synthetic.mp4',
        'has_asr': True,
        'annotation_splits': [],
        'atr_splits': [],
        'asr_split': None,
    }


class ClipRepairTests(unittest.TestCase):
    def test_source_end_cleanup_tail_is_excluded_but_real_operation_is_kept(self):
        previous = CONFIG.get('drop_source_end_cleanup_tails')
        CONFIG['drop_source_end_cleanup_tails'] = True
        try:
            t = trial('assemble', 300)
            t.update({'episodes': [], 'errors': [], 'events': [
                {'action': 'store_tool', 'verb': 'store', 'phase': 'normal', 'start_frame': 290, 'end_frame_exclusive': 300},
            ]})
            tail = clip_record(t, 290, 300, {'reason': 'source_video_end'}, 0)
            self.assertEqual(source_end_cleanup_tail_reason(t, tail), 'source_end_cleanup_tail_without_component_operation_or_valid_error')
            t['episodes'] = [{'start_frame': 290, 'end_frame_exclusive': 300}]
            self.assertIsNone(source_end_cleanup_tail_reason(t, tail))
        finally:
            if previous is None:
                CONFIG.pop('drop_source_end_cleanup_tails', None)
            else:
                CONFIG['drop_source_end_cleanup_tails'] = previous

    def test_assembly_short_partition_is_merged_and_partition_is_preserved(self):
        t = trial('assemble', 500)
        raw = [
            clip_record(t, 0, 100, {'reason': 'a'}, 0),
            clip_record(t, 100, 101, {'reason': 'short'}, 1),
            clip_record(t, 101, 500, {'reason': 'end'}, 2),
        ]
        repaired, mapping = repair_clips(t, raw, 3.0)
        self.assertEqual([(x['start_frame'], x['end_frame_exclusive']) for x in repaired], [(0, 100), (100, 500)])
        self.assertTrue(all(x['duration_s'] >= 3.0 for x in repaired))
        self.assertEqual(repaired[1]['boundary']['repair_action'], 'merge_adjacent_short_clip')
        self.assertTrue(any(row['action'] == 'merge_adjacent_short_clip' for row in mapping))

    def test_disassembly_short_window_is_extended_inside_source(self):
        t = trial('disassemble', 300)
        raw = [clip_record(t, 295, 300, {'reason': 'window'}, 0)]
        repaired, mapping = repair_clips(t, raw, 3.0)
        self.assertEqual([(x['start_frame'], x['end_frame_exclusive']) for x in repaired], [(210, 300)])
        self.assertGreaterEqual(repaired[0]['duration_s'], 3.0)
        self.assertEqual(mapping[0]['action'], 'extend_short_window')

    def test_unrepairable_source_is_dropped(self):
        t = trial('assemble', 20)
        raw = [clip_record(t, 0, 20, {'reason': 'only'}, 0)]
        repaired, mapping = repair_clips(t, raw, 3.0)
        self.assertEqual(repaired, [])
        self.assertEqual(mapping[0]['action'], 'drop_unrepairable_short_clip')


if __name__ == '__main__':
    unittest.main()
