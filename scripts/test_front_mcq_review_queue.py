from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import gradio as gr

from impact_qa.common import read_jsonl,save_json,save_jsonl
from impact_qa.front_mcq_collaboration import current_reviews,record,revision
import impact_qa.front_mcq_page as page


def main():
    original=page.questions()
    samples=deepcopy(original[:5])
    with TemporaryDirectory() as temporary:
        folder=Path(temporary)
        save_jsonl(folder/'questions.jsonl',samples)
        save_json(folder/'progress.json',dict(questions=len(samples),visual_completed_questions=len(samples)))
        record(folder,samples[0],revision(samples[0]),'first','pass',samples[0]['candidate_option_ids'],'existing')
        with patch.object(page,'FOLDER',folder),patch.object(page,'review_media',return_value=None):
            with gr.Blocks() as app:page.build_tab(app)
            callbacks={value.api_name:value.fn for value in app.fns.values() if value.fn}
            initial=callbacks['initialize_front_mcq']('first')
            assert initial[4]['value']==samples[1]['question_id']
            assert samples[0]['group_id'] not in [value for _,value in initial[8]['choices']]
            refreshed=callbacks['refresh_front_mcq'](samples[0]['question_id'],'first','全部','全部','已有视觉解释','未审核')
            assert refreshed[4]['value']==samples[1]['question_id']
            submitted=callbacks['pass_front_mcq'](samples[1]['question_id'],revision(samples[1]),'first',[page.LABELS[k] for k in samples[1]['candidate_option_ids']],'','全部','全部','已有视觉解释','未审核')
            assert submitted[4]['value'] not in {samples[0]['question_id'],samples[1]['question_id']}
            assert samples[1]['question_id'] in submitted[10] and '已保存' in submitted[10]
            assert len(current_reviews(folder,samples[1]))==1
            assert '已审核 2 道' in submitted[12]
            assert samples[1]['question_id'] not in [value for _,value in submitted[4]['choices']]
            group=callbacks['load_front_mcq_group'](samples[1]['group_id'],'first','全部','全部','已有视觉解释','未审核')
            assert group[4]['value']==samples[2]['question_id']
            assert samples[1]['question_zh'] not in group[2]
            reviewed=callbacks['set_front_mcq_review_mode']('first','全部','全部','已有视觉解释','已审核')
            assert reviewed[4]['value']==samples[0]['question_id'] and '人通过' in reviewed[9]
            shared=callbacks['filter_front_mcq']('second','全部','全部','已有视觉解释','未审核')
            assert shared[4]['value'] not in {samples[0]['question_id'],samples[1]['question_id']}
            for q in samples[2:]:record(folder,q,revision(q),'second','pass',q['candidate_option_ids'],'exhaust')
            exhausted=callbacks['filter_front_mcq']('first','全部','全部','已有视觉解释','未审核')
            assert exhausted[4]['value'] is None and exhausted[8]['choices']==[]
            exhausted_submit=callbacks['pass_front_mcq'](samples[-1]['question_id'],revision(samples[-1]),'first',[page.LABELS[k] for k in samples[-1]['candidate_option_ids']],'','全部','全部','已有视觉解释','已审核')
            assert exhausted_submit[4]['value'] is None and exhausted_submit[13]=='未审核'
            revised=deepcopy(samples);revised[0]['visual_review']['facts']+=' Updated evidence.'
            assert [q['question_id'] for q in page.filtered_questions(rows=revised)]==[samples[0]['question_id']]
            assert all(component['type']!='browserstate' for component in app.config['components'])
            print('PASS initial, refresh, filtered clip/question lists, receipt, shared reviewed state, history, exhausted queue, revision reset, nickname initialization')


if __name__=='__main__':main()
