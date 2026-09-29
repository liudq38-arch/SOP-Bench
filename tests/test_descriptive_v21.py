import unittest

from impact_qa.descriptive_v21 import validate


class FrameContractTest(unittest.TestCase):
    def setUp(self):
        self.frames = [{'frame_id': 'f0', 'source_pts_s': 1.0}, {'frame_id': 'f1', 'source_pts_s': 1.04}]
        self.payload = {'case_id': 'case', 'view': 'ego', 'target_frames': self.frames}
        self.result = {'case_id': 'case', 'view': 'ego', 'cards': [dict(f, details='Visible hand and partly occluded tool.', change_from_previous='No resolved change.', unknowns=['Tool tip hidden.']) for f in self.frames], 'missing_frame_ids': []}

    def test_exact_coverage(self):
        validate('describe_frames', self.result, self.payload, self.frames)

    def test_duplicate_frame_rejected(self):
        self.result['cards'][1] = self.result['cards'][0]
        with self.assertRaisesRegex(ValueError, 'frame_coverage'):
            validate('describe_frames', self.result, self.payload, self.frames)

    def test_timestamp_drift_rejected(self):
        self.result['cards'][1]['source_pts_s'] = 2
        with self.assertRaisesRegex(ValueError, 'frame_timestamp'):
            validate('describe_frames', self.result, self.payload, self.frames)

    def test_missing_frame_rejected(self):
        self.result['missing_frame_ids'] = ['f1']
        with self.assertRaisesRegex(ValueError, 'frame_coverage'):
            validate('describe_frames', self.result, self.payload, self.frames)

    def test_wrong_view_rejected(self):
        self.result['view'] = 'front'
        with self.assertRaisesRegex(ValueError, 'case_or_view_mismatch'):
            validate('describe_frames', self.result, self.payload, self.frames)


if __name__ == '__main__':
    unittest.main()
