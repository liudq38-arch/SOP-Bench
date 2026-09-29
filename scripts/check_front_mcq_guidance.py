from collections import Counter
from hashlib import sha256
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import read_jsonl,save_json
from impact_qa.front_mcq_guidance import guidance_payload,guidance_html,REFERENCE,NAMES,STEPS,STATE_NAMES


def main():
    folder=ROOT/'outputs/impact_qa/front_mcq_expansion_v1'
    groups={row['group_id']:row for row in read_jsonl(folder/'groups.jsonl')}
    questions=read_jsonl(folder/'questions.jsonl')
    counts=Counter();untranslated=set();sources={};examples=[]
    for q in questions:
        p=guidance_payload(q,groups[q['group_id']])
        assert p['question']==q['question_id'] and p['target_hand']==q['scope']['hand']
        assert p['model'] in ['A','B']
        counts['questions']+=1;counts['model_'+p['model']]+=1
        counts['with_ASR' if p['has_asr'] else 'without_ASR']+=1
        for kind in ['actions','steps','states']:
            for row in p[kind]:
                assert 0<=row['start']<row['end']<=p['duration']+1e-6,(q['question_id'],kind,row)
                ref=row['source'];sources[ref['path']]=ref['sha256']
                if kind=='actions':
                    assert row['hand'] in ['left','right']
                    if row['noun'] not in NAMES:untranslated.add(row['noun'])
                elif kind=='steps':
                    if row['raw'] not in STEPS:untranslated.add(row['raw'])
                else:
                    assert len(row['values'])==len(p['components'])
                    assert all(str(x) in STATE_NAMES for x in row['values'])
        if p['model']=='B':
            assert not p['has_asr'] and not p['states']
            assert '不套用A' in p['stages']['adapter']['reference']
        if len(examples)<10:examples.append(dict(question_id=q['question_id'],model=p['model'],actions=len(p['actions']),steps=len(p['steps']),state_segments=len(p['states'])))
    for path,value in sources.items():assert sha256((ROOT/path).read_bytes()).hexdigest()==value
    assert not untranslated,untranslated
    assert {r['id'] for r in REFERENCE['categories']}==set('BCDEFG')
    for model in ['A','B']:
        q=next(q for q in questions if groups[q['group_id']]['model']==model)
        html=guidance_html(q,groups[q['group_id']])
        assert 'data-guide=' in html and '六类定义' in html
    report=dict(status='passed',counts=dict(counts),source_documents_verified=len(sources),untranslated=sorted(untranslated),first10=examples,checks=['half_open_intervals','source_SHA','front_only','B_no_invented_ASR','state_values','model_scoped_reference','all_action_and_step_names'],human_reviews_written=False)
    save_json(folder/'guidance_verification.json',report)
    print(report)


if __name__=='__main__':main()
