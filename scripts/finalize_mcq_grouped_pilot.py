from collections import Counter
from pathlib import Path
import sys


ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import read_json,read_jsonl,save_json,save_jsonl


def main():
    folder=ROOT/'outputs/impact_qa/mcq_grouped_v1'
    units={u['unit_id']:u for u in read_jsonl(folder/'candidate_units.jsonl')}
    rounds=['r1','r2','r3','r4_holdout']
    unit_ids,events,controls=set(),set(),set()
    summaries={}
    for name in rounds:
        summaries[name]=read_json(folder/name/'summary.json')
        for uid in read_json(folder/name/'selection.json')['unit_ids']:
            if uid.startswith('control_'):
                controls.add(uid)
            else:
                unit_ids.add(uid)
                events.update(e['event_id'] for ep in units[uid]['episodes'] for e in ep['events'])
    decisions=read_json(folder/'independent_frame_audit.json')['items']
    review_examples=[]
    for row in decisions:
        candidates=read_jsonl(folder/row['round']/'annotation_backed_candidates.jsonl')
        q=next(q for q in candidates if q['question_id']==row['question_id'])
        if row['decision']!='retain_GT_example_for_human_review':
            continue
        if q['correct_option_ids']!=units[q['question_id']]['correct_option_ids']:
            raise ValueError('finalize_mcq:GT_answer_changed')
        critic=read_json(folder/row['round']/'critic_exact/results'/(q['question_id']+'.json'))
        if not critic['accepted_for_human_review']:
            raise ValueError('finalize_mcq:critic_did_not_pass')
        q.update(status='GT_example_only_requires_human_review',independent_frame_audit=row,anomaly_reason_visually_confirmed=False)
        q['answer']='; '.join(o['id']+'. '+o['name'] for o in q['options'] if o['id'] in q['correct_option_ids'])
        q['answer_note']='Anomaly category and timing come from ATR GT. Video confirms the hand operation; the specific abnormality rationale remains unconfirmed.'
        q['review_media']=[e['media']['path'] for e in critic['events']]
        review_examples.append(q)
    save_jsonl(folder/'review_examples.jsonl',review_examples)
    save_jsonl(folder/'final_held_audit.jsonl',[r for r in decisions if r['decision']!='retain_GT_example_for_human_review'])
    calls=Counter()
    for path in folder.glob('**/api_cache/*.json'):
        record=read_json(path)
        calls[record['stage']+':'+record['status']]+=1
    type_short={u['unit_id'] for u in units.values() if any(t<1.5 for ep in u['episodes'] for e in ep['events'] for t in e.get('type_support_seconds',{}).values())}
    report={'rounds':summaries,'unique_anomaly_units_tested':len(unit_ids),'unique_GT_events_tested':len(events),'unique_normal_controls':len(controls),'api_records':dict(calls),'fully_visually_verified_MCQs':0,'initial_action_grounded_candidates':len(decisions),'independent_frame_audited_candidates':len(decisions),'review_examples':len(review_examples),'final_held_candidates':len(decisions)-len(review_examples),'all_candidate_units':len(units),'units_flagged_by_short_type_support':len(type_short),'final_decision':'NOT_READY_FOR_FULL_AUTOMATIC_GENERATION_WITH_VISUAL_EXPLANATIONS','formal_release':False,'human_review':'unreviewed','reason':'Mechanical logic passes, but type-specific visual rationale is unconfirmed; hand/tool attribution and model self-consistency remain unreliable.'}
    save_json(folder/'final_pilot_summary.json',report)
    print({k:v for k,v in report.items() if k!='rounds'})


if __name__=='__main__':
    main()
