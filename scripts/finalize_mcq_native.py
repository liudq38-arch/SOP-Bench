from collections import Counter
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import fingerprint,read_json,read_jsonl,save_json,save_jsonl


def main():
    base=ROOT/'outputs/impact_qa/mcq_grouped_v2'
    output=base/'review_export'
    audit=read_json(base/'codex_visual_audit.json')
    decisions={r['case_id']:r for r in audit['cases']}
    cases=read_jsonl(base/'native_r2/cases.jsonl')
    selected=[]
    for case in cases:
        round_name='native_r3_top' if case['view']=='top' else 'native_r2'
        source=base/round_name/'results'/(case['case_id']+'.json')
        record=read_json(source)
        if record['status']!='ok':
            raise ValueError('native_finalizer:incomplete:'+case['case_id'])
        q=record['question']
        decision=decisions[q['question_id']]
        if decision['round']!=round_name or decision['record_fingerprint']!=fingerprint(record):
            raise ValueError('native_finalizer:stale_audit:'+case['case_id'])
        kept=q['automatic_gate']['gt_candidate_supported'] and decision['verdict']=='GT_example_facts_only'
        q.update(source_round=round_name,source_result=str(source),status='GT_example_facts_only' if kept else 'held',codex_visual_audit=decision,formal_release=False,human_review='unreviewed',reason_verified=False)
        selected.append(q)
    if len(selected)!=len(decisions):
        raise ValueError('native_finalizer:audit_case_mismatch')
    candidates=[q for q in selected if q['status']=='GT_example_facts_only']
    held=[q for q in selected if q['status']=='held']
    save_jsonl(output/'cases.jsonl',cases)
    save_jsonl(output/'questions.jsonl',selected)
    save_jsonl(output/'gt_candidates.jsonl',candidates)
    save_jsonl(output/'held.jsonl',held)
    save_jsonl(output/'released_questions.jsonl',[])
    save_json(output/'codex_visual_audit.json',audit)
    report={'unique_view_cases':len(selected),'unique_operation_families':len({q['family_id'] for q in selected}),'gt_facts_candidates':len(candidates),'candidate_anomaly':sum(q['correct_option_ids']!=['A'] for q in candidates),'candidate_correct':sum(q['correct_option_ids']==['A'] for q in candidates),'candidate_option_counts':dict(Counter(o for q in candidates for o in q['correct_option_ids'])),'held':len(held),'diagnostic_short':sum(q['diagnostic_only'] for q in selected),'all_types_reason_verified':0,'formal_released':0,'direct_frame_audit_cases':len(decisions),'reviewer':'Codex','human_review':'unreviewed','formal_release':False,'rounds':{r:read_json(base/r/'summary.json') for r in ['native_r1','native_r2','native_r3_top']}}
    save_json(output/'summary.json',report)
    print({k:v for k,v in report.items() if k!='rounds'})


if __name__=='__main__':
    main()
