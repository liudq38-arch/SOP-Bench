import copy
import unittest

from impact_qa.atr_qa import KINDS, validate_generation, validate_reviews
from impact_qa.atr_item_validation import validate_items


class ATRValidationTest(unittest.TestCase):
    def setUp(self):
        self.case={'images':[{'evidence_id':'f00','role':'target'},{'evidence_id':'f01','role':'after'}],'shared_gt':{'allowed_source_ids':['atr_ego']}}
        self.result={'items':[{'kind':k,'answerable':False,'question':'Question?','answer':'','options':[],'correct_option':None,'source_ids':[],'image_ids':[],'evidence':'','grade':0,'limitation':'Missing evidence.'} for k in KINDS]}

    def activate(self,kind):
        q=next(q for q in self.result['items'] if q['kind']==kind)
        q.update(answerable=True,answer='Yes.',options=['Yes.','No.','Unknown.'],correct_option=0,source_ids=['atr_ego'],image_ids=['f00'])
        return q

    def test_annotation_only_not_visual_confidence(self):
        self.activate('tool_error')
        self.assertEqual(validate_generation(self.result,self.case)['items'][2]['grade'],0)

    def test_expected_tool_cannot_be_guessed(self):
        self.activate('expected_tool')
        with self.assertRaisesRegex(ValueError,'unsupported_normative'):validate_generation(self.result,self.case)

    def test_unknown_image_rejected(self):
        self.activate('actual_tool')['image_ids']=['invented']
        with self.assertRaisesRegex(ValueError,'invalid_evidence'):validate_generation(self.result,self.case)

    def test_change_needs_after_and_before(self):
        q=self.activate('observed_correction')
        with self.assertRaisesRegex(ValueError,'missing_change'):validate_generation(self.result,self.case)
        q['image_ids']=['f00','f01']
        validate_generation(self.result,self.case)

    def test_blind_grade_three_without_evidence_rejected(self):
        with self.assertRaisesRegex(ValueError,'missing_image'):validate_reviews({'items':[{'kind':'actual_tool','answer':'Wrench','grade':3,'image_ids':[]}]},['actual_tool'],self.case)

    def test_bad_change_does_not_destroy_valid_tool_item(self):
        self.activate('actual_tool')
        self.activate('observed_correction')
        result=validate_items(self.result,self.case,{k:'Question?' for k in KINDS},{k:0 for k in KINDS})
        self.assertTrue(next(q for q in result['items'] if q['kind']=='actual_tool')['answerable'])
        self.assertFalse(next(q for q in result['items'] if q['kind']=='observed_correction')['answerable'])
        self.assertEqual(result['item_validation_errors'][0]['raw_item']['image_ids'],['f00'])


if __name__=='__main__':unittest.main()
