import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import read_json
from impact_qa.mcq_sop_filter import filter_question
from impact_qa.mcq_sop_payload import assert_blind
from impact_qa.mcq_sop_reference import build_reference
from impact_qa.mcq_sop_validation import validate_result


class Contracts(unittest.TestCase):
    def setUp(self):
        self.group={'fps':30,'start_frame':300,'end_frame_exclusive':600}
        self.q={'question_id':'q','scope':{'playback_interval_s':[1,2.5]}}

    def test_strict_boundary(self):
        self.assertEqual(filter_question(self.q,self.group)['status'],'kept')
        self.q['scope']['playback_interval_s'][1]=2.499999
        self.assertEqual(filter_question(self.q,self.group)['discard_reason'],'too_short')

    def test_missing_invalid_outside(self):
        self.assertEqual(filter_question({'scope':{}},self.group)['discard_reason'],'no_segment')
        for interval in [[1,1],[3,2],[True,3],['1',4],[1,float('nan')],[1,None]]:
            self.q['scope']['playback_interval_s']=interval
            self.assertEqual(filter_question(self.q,self.group)['discard_reason'],'invalid')
        for interval in [[-1,2],[9,11]]:
            self.q['scope']['playback_interval_s']=interval
            self.assertEqual(filter_question(self.q,self.group)['discard_reason'],'out_of_range')

    def test_multi_segment_minimum(self):
        self.q['scope']={'target_segments':[{'interval':[0,2],'time_basis':'clip'},{'interval':[5,6.49],'time_basis':'clip'}]}
        self.assertEqual(filter_question(self.q,self.group)['discard_reason'],'too_short')

    def test_trial_time_and_fps(self):
        self.q['scope']={'source_interval_s':[11,12.5]}
        result=filter_question(self.q,self.group)
        self.assertEqual(result['target_segments'][0]['start_s'],1)
        self.q['scope']={'target_segments':[{'interval':[330,375],'time_basis':'trial','unit':'frames','fps':30}]}
        self.assertEqual(filter_question(self.q,self.group)['status'],'kept')
        self.q['scope']['target_segments'][0]['fps']=60
        self.assertEqual(filter_question(self.q,self.group)['discard_reason'],'out_of_range')

    def test_exact_frames_correct_float_subtraction(self):
        self.q['scope']={'playback_interval_s':[1.00000000000003,2.5]}
        self.group['events']=[{'event_id':'q','start_frame':330,'end_frame_exclusive':375}]
        self.assertEqual(filter_question(self.q,self.group)['status'],'kept')
        self.q['scope']['playback_interval_s'][0]=1.1
        self.assertEqual(filter_question(self.q,self.group)['discard_reason'],'invalid')

    def test_blind_whitelist(self):
        assert_blind({'tas_b_hands':{'L':[{'action':'hold_part','in_target':True}]}})
        for key in ['phase','labels','GT_option_ids','visual_review','candidate_option_ids']:
            with self.assertRaises(ValueError):assert_blind({'nested':[{key:[]} ]})

    def test_repeating_decimal_frame_boundaries(self):
        for start in range(1,60):
            self.q['scope']={'target_segments':[{'interval':[300+start,345+start],'time_basis':'trial','unit':'frames','fps':30}]}
            self.assertEqual(filter_question(self.q,self.group)['status'],'kept')

    def test_sop_graphs_and_unknowns(self):
        ref=build_reference();self.assertFalse(ref['psr_audit']['dependency_edges_provided'])
        for sop in ref['procedures'].values():
            assert_blind(sop)
            ids={s['id'] for s in sop['steps']};self.assertEqual(len(ids),len(sop['steps']))
            edges=sop['hard_prerequisites'];done=set()
            while len(done)<len(ids):
                ready={i for i in ids-done if all(e['before'] in done for e in edges if e['after']==i)}
                self.assertTrue(ready,'cycle');done.update(ready)
            for group in sop['interchangeable_step_groups']:
                self.assertTrue(set(group['steps'])<=ids)
        b=ref['procedures']['B_assemble'];self.assertTrue(any(s['unknown'] for s in b['steps']))

    def test_output_temporal_contract(self):
        schema=read_json(ROOT/'prompts/impact_qa/mcq_sop_visual_v1_schema.json')
        record={'case':{'target':{'start_s':2,'end_s':4,'hand':'L'}},'frames':[{'frame_index':1,'role':'context_before','clip_timestamp_s':1},{'frame_index':2,'role':'target','clip_timestamp_s':2.5}],'sop':{'steps':[{'id':'A_I_ROTOR'}]}}
        value={'verdict':'anomaly','anomaly_type':'operational','is_redundant_action':False,'redundant_subtype':'none','matched_sop_step':'A_I_ROTOR','expected_vs_observed':'应持稳，左手部件掉落','evidence_actions':[{'t_start':2,'t_end':3,'hand':'L','action':'drop','observation':'部件掉落'}],'evidence_frames':[2],'confidence':.8,'reason':'左手部件掉落'}
        validate_result(value,schema,record)
        bad=copy.deepcopy(value);bad['evidence_frames']=[1]
        with self.assertRaises(ValueError):validate_result(bad,schema,record)
        bad=copy.deepcopy(value);bad['evidence_actions'][0]['t_end']=4.1
        with self.assertRaises(ValueError):validate_result(bad,schema,record)
        bad=copy.deepcopy(value);bad.update(verdict='insufficient_evidence',anomaly_type='none')
        with self.assertRaises(ValueError):validate_result(bad,schema,record)


if __name__=='__main__':unittest.main()
