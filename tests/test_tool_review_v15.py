import unittest

from impact_qa.tool_review_v15 import select_images, validate


class ToolReviewTests(unittest.TestCase):
    def test_reordering_preserves_media_and_compact_endpoints(self):
        refs = [{'evidence_id': f'context_{i}', 'frame_index': i * 10, 'path': f'c{i}.jpg'} for i in range(4)] + [{'evidence_id': f'target_{i}', 'frame_index': i + 5, 'path': f't{i}.jpg'} for i in range(16)]
        ordered = select_images({'image_refs': refs}, 'chronological20')
        self.assertEqual(len(ordered), 20)
        self.assertEqual({r['path'] for r in ordered}, {r['path'] for r in refs})
        self.assertEqual([r['frame_index'] for r in ordered], sorted(r['frame_index'] for r in refs))
        compact = select_images({'image_refs': refs}, 'transition8')
        self.assertEqual(len(compact), 8)
        self.assertEqual(compact[0]['evidence_id'], 'context_0')
        self.assertEqual(compact[-1]['evidence_id'], 'context_3')
        ordered[0]['path'] = 'changed'
        self.assertEqual(refs[0]['path'], 'c0.jpg')

    def test_identity_alone_does_not_prove_pickup(self):
        refs = [{'evidence_id': 'a', 'frame_index': 1}, {'evidence_id': 'b', 'frame_index': 2}]
        raw = {'tool': 'screwdriver', 'shape': 'handled_shaft', 'before_image_id': 'a', 'before_state': 'grasping', 'after_image_id': 'b', 'after_state': 'held_away', 'observation': 'Shaft leaves the surface in the hand.'}
        self.assertTrue(validate(raw, refs, 'transition8')[2])
        for change in [{'before_state': 'already_held'}, {'after_state': 'on_surface'}, {'shape': 'flat_wrench_body'}, {'tool': 'unknown'}]:
            self.assertFalse(validate(raw | change, refs, 'transition8')[2])
        self.assertEqual(raw['before_state'], 'grasping')

    def test_false_or_reverse_evidence_rejected(self):
        refs = [{'evidence_id': 'a', 'frame_index': 1}, {'evidence_id': 'b', 'frame_index': 2}]
        raw = {'tool': 'wrench', 'shape': 'flat_wrench_body', 'before_image_id': 'a', 'before_state': 'on_surface', 'after_image_id': 'b', 'after_state': 'held_away', 'observation': 'Metal wrench moves away with the hand.'}
        for change in [{'after_image_id': 'a'}, {'before_image_id': 'missing'}, {'before_image_id': None}]:
            with self.assertRaises(AssertionError):
                validate(raw | change, refs, 'transition8')
        value, changes, answerable = validate(raw | {'before_image_id': 'Frame a'}, refs, 'transition8')
        self.assertTrue(answerable)
        self.assertEqual(value['tool'], raw['tool'])
        self.assertEqual(len(changes), 1)


if __name__ == '__main__':
    unittest.main()
