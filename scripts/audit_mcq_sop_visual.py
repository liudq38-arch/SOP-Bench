import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_sop_payload import assert_blind
from impact_qa.mcq_sop_validation import validate_result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    folder=ROOT/'outputs/impact_qa/mcq_sop_visual_v1'
    kept=read_jsonl(folder/'kept_questions.jsonl')
    dropped=read_jsonl(folder/'discarded_questions.jsonl')
    source=read_jsonl(ROOT/'outputs/impact_qa/front_mcq_expansion_v1/questions.jsonl')
    lookup={q['question_id']:q for q in source}
    assert len(lookup)==len(source)==len(kept)+len(dropped)
    for q in kept+dropped:
        original={k:v for k,v in q.items() if k!='filter'}
        assert original==lookup[q['question_id']]
    expected={s['segment_id'] for q in kept for s in q['filter']['target_segments']}
    schema=read_json(ROOT/'prompts/impact_qa/mcq_sop_visual_v1_schema.json')
    frozen=read_json(folder/'generation_frozen.json')['fingerprint']
    all_results=[]
    errors=[]
    images=Counter()
    cases=Counter()
    gaps=defaultdict(list)
    usage=Counter()
    review_flags=[]
    for path in sorted((folder/'results').glob('*.json')):
        result=read_json(path)
        assert result['segment_id'] in expected
        assert result['run_fingerprint']==frozen
        all_results.append(result)
        if result['status']!='ok':
            errors.append(dict(segment_id=result['segment_id'],status=result['status'],error=result.get('error'),validation_errors=result.get('validation_errors')))
            continue
        manifest=read_json(result['media_manifest'])
        payload={k:result[k] for k in schema['required']}
        validate_result(payload,schema,manifest)
        assert_blind(manifest['case'])
        assert_blind(manifest['sop'])
        request=read_json(folder/'requests'/(fingerprint(result['segment_id'])[:24]+'.json'))
        assert request['labels_sent'] is False
        assert request['temperature']==0
        assert request['response_format']['type']=='json_schema'
        assert manifest['question_id']==result['question_id']
        assert manifest['trial_id']==result['trial_id']
        for forbidden in ['GT_option_ids','candidate_option_ids','GT_phase','visual_review','rule_ids',result['question_id'],result['trial_id']]:
            assert forbidden not in request['user_text']
        target=manifest['case']['target']
        frames=manifest['frames']
        inside=[f for f in frames if f['role']=='target']
        assert 8<=len(inside)<=16
        assert len(frames)<=20
        assert frames==request['frame_inputs']
        assert frames==sorted(frames,key=lambda x:x['clip_timestamp_s'])
        assert len({x['source_frame_index'] for x in frames})==len(frames)
        for f in inside:
            assert target['start_s']-1e-6<=f['clip_timestamp_s']<target['end_s']
        indices=[f['source_frame_index'] for f in inside]
        increments=[b-a for a,b in zip(indices,indices[1:])]
        assert max(increments)-min(increments)<=1
        for f in frames:
            assert abs(f['source_frame_index']/manifest['fps']-manifest['clip_source_start_s']-f['clip_timestamp_s'])<1e-6
            assert Path(f['path']).is_file()
        images[(len(inside),len(frames))]+=1
        cases[(manifest['case']['model'],manifest['case']['workflow'],result['verdict'])]+=1
        gap=manifest['case']['sampling']['maximum_target_frame_gap_s']
        gaps[result['verdict']].append(gap)
        for key in ['prompt_tokens','completion_tokens','total_tokens']:
            usage[key]+=(result.get('usage') or {}).get(key,0)
        flags=[]
        if gap>2:flags.append('sparse_target_sampling_over_2s')
        if result['verdict']=='normal' and result['confidence']>=.9:flags.append('high_confidence_normal_requires_review')
        if result['verdict']=='anomaly':flags.append('anomaly_claim_requires_visual_confirmation')
        if flags:review_flags.append(dict(question_id=result['question_id'],segment_id=result['segment_id'],verdict=result['verdict'],flags=flags,maximum_frame_gap_s=gap,reason=result['reason'],media_manifest=result['media_manifest']))
    found={r['segment_id'] for r in all_results}
    assert len(found)==len(all_results)
    source_changes=[]
    before=read_json(folder/'source_integrity_before.json')
    for name,record in before['annotations_sha256'].items():
        p=ROOT/name
        if hashlib.sha256(p.read_bytes()).hexdigest()!=record['sha256']:source_changes.append(name)
    for name,record in before['video_identity_size_mtime'].items():
        s=Path(name).stat()
        if s.st_size!=record['size'] or s.st_mtime_ns!=record['mtime_ns']:source_changes.append(name)
    for name,sha in read_json(folder/'source_frozen.json').items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:source_changes.append(name)
    assert not source_changes
    stats=read_json(folder/'filter_statistics.json')
    audit=folder/'audit'
    audit.mkdir(exist_ok=True)
    for group in ['by_gt_type','by_trial','by_origin']:
        rows=[dict(group=k,**v) for k,v in stats[group].items()]
        keys=list(dict.fromkeys(k for r in rows for k in r))
        with (audit/(group+'_retention.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
    verdicts=Counter(r['verdict'] for r in all_results if r['status']=='ok')
    result=dict(expected=len(expected),returned=len(found),missing=len(expected-found),valid=sum(verdicts.values()),verdict_counts=dict(verdicts),failures=dict(Counter(r['status'] for r in errors)),input_original_fields_identical=True,annotations_unchanged=len(before['annotations_sha256']),videos_identity_unchanged=len(before['video_identity_size_mtime']),requests_blind_contract_passed=sum(verdicts.values()),frame_counts={str(k):v for k,v in images.items()},by_model_workflow_verdict={str(k):v for k,v in cases.items()},maximum_frame_gap_s_by_verdict={k:dict(median=statistics.median(v),max=max(v),above_2s=sum(x>2 for x in v)) for k,v in gaps.items()},token_usage=dict(usage),run_fingerprint=frozen,visual_correctness_not_proven_by_schema=True)
    save_json(audit/'validation.json',result)
    save_jsonl(audit/'failures.jsonl',errors)
    save_jsonl(audit/'review_priority_flags.jsonl',review_flags)
    print(json.dumps(result,ensure_ascii=False))
    if args.require_complete:
        assert expected==found,'audit_mcq_sop_visual:pending_segments'
        assert not errors,'audit_mcq_sop_visual:failed_segments'


if __name__=='__main__':main()
