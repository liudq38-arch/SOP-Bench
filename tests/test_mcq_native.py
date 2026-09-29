import unittest
from unittest.mock import patch

from impact_qa.mcq_native import draft_question, make_case, match_run, stable_runs
from impact_qa.mcq_native_checks import interaction_issues
from scripts.run_mcq_native import gate


def action(a,b,labels,hand='right',name='loosen_screw',phase='anomaly'):
    return {'start_frame':a,'end_frame_exclusive':b,'labels':labels,'hand':hand,'action':name,'phase':phase}


def trial(actions,view='front',fps=30):
    return {'video_id':'test_'+view,'trial_id':'test','view':view,'fps':fps,'actions':actions,'source_video':'/test.mp4'}


class NativeMCQTests(unittest.TestCase):
    def test_claimed_confidence_cannot_override_action_contradiction(self):
        examples=[('hand_loosen_screw','rotating_fastener_with_tool'),('hand_spin_drive_shaft','holding'),('hold_gearbox_housing_drive_shaft','rotating_fastener_with_tool')]
        for gt,visual in examples:
            case={'event':{'hand':'right','action_names':[gt]}}
            observation={'hands':[{'hand':'right','interaction':visual,'tool_contact':'absent'}]}
            self.assertTrue(interaction_issues(case,observation))

    def test_tool_tip_pointing_away_cannot_establish_tool_use(self):
        case={'event':{'hand':'right','action_names':['loosen_screw']}}
        observation={'hands':[{'hand':'right','interaction':'rotating_fastener_with_tool','tool_contact':'used_for_action','tool_tip_relation':'pointing_away'}]}
        self.assertIn('tool_use_claim_contradicts_visible_tip_relation',interaction_issues(case,observation))

    def test_short_type_never_inherits_long_union(self):
        t=trial([action(0,210,[0,0,0,0,1,0]),action(210,225,[0,1,0,0,0,0])])
        runs=stable_runs(t)
        self.assertEqual([r['duration_s'] for r in runs],[7,0.5])
        self.assertEqual(runs[0]['labels'],[0,0,0,0,1,0])

    def test_merge_only_adjacent_same_hand_and_labels(self):
        labels=[0,0,1,0,0,0]
        t=trial([action(0,90,labels),action(90,180,labels,name='hold_tool'),action(181,210,labels),action(0,180,labels,hand='left')])
        runs=stable_runs(t)
        self.assertEqual(len(runs),3)
        self.assertEqual(len(next(r for r in runs if r['hand']=='right')['actions']),2)

    def test_other_view_has_own_labels_and_fps(self):
        front=trial([action(0,180,[0,0,0,0,1,0])])
        ego=trial([action(5,155,[0,0,1,0,1,0])],view='ego',fps=25)
        native,mapping=match_run(stable_runs(front)[0],30,ego)
        self.assertEqual(native['labels'],[0,0,1,0,1,0])
        self.assertTrue(mapping['native_labels_differ'])
        self.assertEqual(native['start_frame'],5)

    def test_changed_action_or_distant_time_not_matched(self):
        ref=stable_runs(trial([action(0,180,[1,0,0,0,0,0])]))[0]
        for rows in [[action(0,180,[1,0,0,0,0,0],name='adjust_shaft')],[action(300,480,[1,0,0,0,0,0])]]:
            self.assertIsNone(match_run(ref,30,trial(rows))[0])

    def test_normal_requires_no_raw_atr_overlap(self):
        t=trial([action(0,180,[0]*6,phase='normal')])
        run=stable_runs(t)[0]
        with patch('impact_qa.mcq_native.atr_index',return_value={('test_front','right'):[{'start_frame':100,'end_frame':101,'labels':[1,0,0,0,0,0]}]}):
            with self.assertRaisesRegex(ValueError,'normal_conflicts_with_ATR'):
                make_case(t,run,'family')

    def test_short_interval_is_diagnostic_even_with_good_evidence(self):
        t=trial([action(0,90,[0,0,0,0,1,0])])
        atr={('test_front','right'):[{'start_frame':0,'end_frame':89,'labels':[0,0,0,0,1,0]}]}
        with patch('impact_qa.mcq_native.atr_index',return_value=atr):
            case=make_case(t,stable_runs(t)[0],'family')
        media={'sampled_frames':[{'frame_id':'a','source_frame_index':0,'source_pts_s':0},{'frame_id':'b','source_frame_index':60,'source_pts_s':2}]}
        observed={'hands':[{'hand':'right','hand_identity':'clear','confidence':'high','tool_contact':'absent','interaction':'manipulating_part','evidence_frame_ids':['a','b']}]}
        grounded={'visible_action':'supported','claim_consistency':'consistent','hand_identity':'clear','confidence':'high','tool_contact':'absent','evidence_frame_ids':['a','b'],'anomaly_evidence':[{'option_id':'F','evidence_status':'observed_only','evidence_frame_ids':['a','b']} ]}
        decision=gate(case,media,observed,grounded)
        self.assertFalse(decision['gt_candidate_supported'])
        self.assertIn('below_5s_diagnostic_only',decision['issues'])
        self.assertEqual(draft_question(case,[])['correct_option_ids'],['F'])


if __name__=='__main__':
    unittest.main()
