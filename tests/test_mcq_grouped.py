import unittest

from impact_qa.mcq_grouped import add_type_intervals, audit_units, cluster_events, make_windows, option_ids, question_record
from impact_qa.mcq_grouped_review import assess_event, evidence_errors


def event(eid, a, b, labels=None, hand='left'):
    return {'event_id': eid, 'start_frame': a, 'end_frame_exclusive': b, 'labels': labels or [1,0,0,0,0,0], 'duration_s': (b-a)/30, 'hand': hand, 'source_ids': ['s_'+eid]}


def unit(events):
    return {'unit_id': 'q', 'parent_clip_id': 'c', 'clip': {'clip_id': 'c', 'video_id': 'v', 'start_frame': 0, 'end_frame_exclusive': 12000, 'fps': 30}, 'scope': 'specified_hand_intervals', 'context_only_events': [], 'episodes': cluster_events(events, 30), 'correct_option_ids': option_ids(events)}


class GroupedMCQTests(unittest.TestCase):
    def test_type_intervals_do_not_inherit_other_labels(self):
        e=event('a',0,300,[1,1,0,0,0,0])
        a=dict(event('x',0,150),action='hold')
        b=dict(event('y',150,300,[0,1,0,0,0,0]),action='insert')
        enriched=add_type_intervals(e,{'events':[a,b]})
        self.assertEqual(enriched['type_intervals']['B'][0]['interval_frames'],[0,150])
        self.assertEqual(enriched['type_intervals']['C'][0]['interval_frames'],[150,300])

    def test_type_evidence_cannot_be_taken_from_other_type_interval(self):
        e=event('a',0,300)
        e['type_intervals']={'B':[{'interval_frames':[150,300]}]}
        m={'path':'x','sha256':'h','sampled_frames':[{'frame_id':'a','source_frame_index':0,'source_pts_s':0},{'frame_id':'b','source_frame_index':60,'source_pts_s':2}]}
        observation={'abnormality':'visible','confidence':'high','description':'Failed operation','evidence_frame_ids':['a','b']}
        review={'labels':[{'option_id':'B','verdict':'supported','confidence':'high','reason':'Timing failure','evidence_frame_ids':['a','b']}]}
        out=assess_event(e,observation,review,m,{'minimum_evidence_span_seconds':1,'per_type_evidence':True})
        self.assertIn('evidence_outside_type_subinterval:B',out['hold_reasons'])

    def test_action_grounded_candidate_is_not_type_verified(self):
        e=event('a',0,300)
        e['action_names']=['hand_loosen_screw']
        m={'path':'x','sha256':'h','sampled_frames':[{'frame_id':'a','source_frame_index':0,'source_pts_s':0},{'frame_id':'b','source_frame_index':60,'source_pts_s':2}]}
        observation={'abnormality':'uncertain','confidence':'high','description':'Turns fastener by hand','evidence_frame_ids':['a','b']}
        review={'labels':[{'option_id':'B','verdict':'uncertain','confidence':'low','reason':'No known requirement','evidence_frame_ids':['a','b']}], 'action_grounding':{'verdict':'matches','confidence':'high','observation_consistency':'supports_facts','evidence_frame_ids':['a','b'],'description':'Turns fastener by hand'}}
        out=assess_event(e,observation,review,m,{'minimum_evidence_span_seconds':1,'require_blind_abnormality':False})
        self.assertFalse(out['accepted'])
        self.assertTrue(out['annotation_backed_eligible'])
        review['action_grounding']['observation_consistency']='contradiction'
        self.assertFalse(assess_event(e,observation,review,m,{'minimum_evidence_span_seconds':1})['annotation_backed_eligible'])

    def test_no_known_action_cannot_be_grounded_from_label_only(self):
        e=event('a',0,300)
        m={'path':'x','sha256':'h','sampled_frames':[{'frame_id':'a','source_frame_index':0,'source_pts_s':0},{'frame_id':'b','source_frame_index':60,'source_pts_s':2}]}
        observation={'abnormality':'visible','confidence':'high','description':'Moves item','evidence_frame_ids':['a','b']}
        review={'labels':[], 'action_grounding':{'verdict':'matches','confidence':'high','observation_consistency':'supports_facts','evidence_frame_ids':['a','b'],'description':'Moves item'}}
        self.assertFalse(assess_event(e,observation,review,m,{'minimum_evidence_span_seconds':1})['annotation_backed_eligible'])

    def test_short_type_cannot_inherit_long_event_duration(self):
        e=event('a',0,300)
        e.update(action_names=['hold'],type_support_seconds={'B':0.5})
        m={'path':'x','sha256':'h','sampled_frames':[{'frame_id':'a','source_frame_index':0,'source_pts_s':0},{'frame_id':'b','source_frame_index':60,'source_pts_s':2}]}
        observation={'abnormality':'visible','confidence':'high','description':'Holds part','evidence_frame_ids':['a','b']}
        review={'labels':[{'option_id':'B','verdict':'supported','confidence':'high','reason':'Timing issue','evidence_frame_ids':['a','b']}], 'action_grounding':{'verdict':'matches','confidence':'high','observation_consistency':'supports_facts','evidence_frame_ids':['a','b'],'description':'Holds part'}}
        out=assess_event(e,observation,review,m,{'minimum_evidence_span_seconds':1,'minimum_type_support_seconds':1.5})
        self.assertFalse(out['accepted'])
        self.assertFalse(out['annotation_backed_eligible'])
        self.assertIn('type_support_below_minimum:B',out['hold_reasons'])

    def test_transitive_overlap_keeps_both_hands_and_original_events(self):
        rows = [event('a', 0, 180), event('b', 150, 330, [0,1,0,0,0,0], 'right'), event('c',345,510),event('d',526,700)]
        groups = cluster_events(rows,30)
        self.assertEqual(len(groups),2)
        self.assertEqual([e['event_id'] for e in groups[0]['events']],['a','b','c'])
        self.assertEqual(groups[0]['option_ids'],['B','C'])

    def test_half_open_boundary_and_gap(self):
        self.assertEqual(len(cluster_events([event('a',0,150),event('b',165,330)],30)),1)
        self.assertEqual(len(cluster_events([event('a',0,150),event('b',166,330)],30)),2)

    def test_partial_support_cannot_release_union(self):
        u = unit([event('a',0,150),event('b',300,450)])
        q, held = question_record(u, {'a':{'accepted':True}}, [])
        self.assertIsNone(q)
        self.assertEqual(held['missing_event_ids'],['b'])

    def test_scoped_question_keeps_original_intervals(self):
        u=unit([event('a',300,480),event('b',400,580,hand='right')])
        q,_=question_record(u,{'a':{'accepted':True},'b':{'accepted':True}},[])
        self.assertIn('left hand, 10.00',q['question'])
        self.assertEqual(len(q['abnormal_segments']),2)
        self.assertEqual(q['abnormal_segments'][0]['source_interval_frames'],[300,480])

    def test_windows_cover_long_event_without_changing_gt(self):
        e=event('long',300,6200)
        u=unit([e])
        windows=make_windows(u,{'context_seconds':3,'window_seconds':30})
        covered=set()
        for w in windows:
            covered.update(range(w['start_frame'],w['end_frame_exclusive']))
            self.assertEqual(w['events'][0],e)
            self.assertLessEqual(w['end_frame_exclusive']-w['start_frame'],900)
        self.assertTrue(set(range(300,6200)).issubset(covered))

    def test_dedup_and_lost_event_are_hard_errors(self):
        u=unit([event('a',0,150)])
        self.assertTrue(audit_units([u,u])['hard_errors'])
        self.assertTrue(audit_units([u],{'a':[], 'lost':[]})['hard_errors'])

    def test_outside_or_single_frame_cannot_establish_temporal_error(self):
        e=event('a',30,150)
        m={'sampled_frames':[{'frame_id':'f0','source_frame_index':0,'source_pts_s':0},{'frame_id':'f60','source_frame_index':60,'source_pts_s':2}]}
        self.assertTrue(evidence_errors(['f60'],e,m))
        self.assertEqual(evidence_errors(['f0','f60'],e,m),['evidence_outside_event'])

    def test_gt_label_cannot_override_blind_normal(self):
        e=event('a',0,150)
        m={'path':'x','sha256':'h','sampled_frames':[{'frame_id':'a','source_frame_index':0,'source_pts_s':0},{'frame_id':'b','source_frame_index':60,'source_pts_s':2}]}
        observation={'abnormality':'not_visible','confidence':'high','description':'Normal operation','evidence_frame_ids':['a','b']}
        adjudication={'labels':[{'option_id':'B','verdict':'supported','confidence':'high','reason':'GT says temporal','evidence_frame_ids':['a','b']}]}
        result=assess_event(e,observation,adjudication,m,{'minimum_evidence_span_seconds':1})
        self.assertFalse(result['accepted'])

    def test_multilabel_requires_every_label(self):
        e=event('a',0,150,[1,1,0,0,0,0])
        m={'path':'x','sha256':'h','sampled_frames':[{'frame_id':'a','source_frame_index':0,'source_pts_s':0},{'frame_id':'b','source_frame_index':60,'source_pts_s':2}]}
        observation={'abnormality':'visible','confidence':'high','description':'Concrete failed insertion','evidence_frame_ids':['a','b']}
        adjudication={'labels':[{'option_id':'B','verdict':'supported','confidence':'high','reason':'Repeated failure','evidence_frame_ids':['a','b']}]}
        result=assess_event(e,observation,adjudication,m,{'minimum_evidence_span_seconds':1})
        self.assertIn('gt_label_set_mismatch',result['hold_reasons'])


if __name__ == '__main__':
    unittest.main()
