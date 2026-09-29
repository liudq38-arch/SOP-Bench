from collections import Counter
from hashlib import sha256
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import fingerprint,read_json,read_jsonl,save_json
from impact_qa.evidence_audit import verify_native_action
from impact_qa.front_mcq_expansion import FOLDER,duration_bin
from scripts.run_front_mcq_expansion import validate


def main():
    groups=read_jsonl(FOLDER/'groups.jsonl');qs=read_jsonl(FOLDER/'questions.jsonl');events=read_jsonl(FOLDER/'events.jsonl')
    if fingerprint(groups)!=read_json(FOLDER/'selection_frozen.json')['fingerprint']:raise ValueError('audit_front_mcq:changed_groups')
    if len(qs)!=1977 or len({q['question_id'] for q in qs})!=1977:raise ValueError('audit_front_mcq:question_count')
    documents={};pointers=set();completed=0;issues=[];media_count=0;frames=0
    question_map={q['question_id']:q for q in qs}
    source_refs=set();targetcounts=[];durations=[];maxerr=0;atr_supported=0;atr_unmatched=[]
    for group in groups:
        if group['view']!='front' or group['duration_s']<45-1e-6:raise ValueError('audit_front_mcq:view_or_duration')
        resultpath=FOLDER/'results'/(group['group_id']+'.json')
        result=read_json(resultpath) if resultpath.exists() else {'status':'queued'}
        if result['status']=='ok':
            validate({'items':result['items']},group,result['media']);completed+=1
            media=result['media'];media_count+=1;frames+=len(media['sampled_frames'])
            if sha256(Path(media['path']).read_bytes()).hexdigest()!=media['sha256']:raise ValueError('audit_front_mcq:media_hash')
            for f in media['sampled_frames']:
                if not group['start_frame']<=f['source_frame_index']<group['end_frame_exclusive']:raise ValueError('audit_front_mcq:frame_scope')
                maxerr=max(maxerr,abs(f['source_pts_s']-f['source_frame_index']/group['fps']))
                source_refs.add((group['source_video'],f['source_frame_index']))
            targetcounts.extend(media['target_sample_counts'].values())
        else:issues.append(dict(group_id=group['group_id'],status=result['status'],error=result.get('error')))
        for event in group['events']:
            if not group['start_frame']<=event['start_frame']<event['end_frame_exclusive']<=group['end_frame_exclusive']:raise ValueError('audit_front_mcq:target_bounds')
            for action in event['actions']:pointers.add(verify_native_action(action,documents))
            q=question_map[event['event_id']]
            if q['formal_release'] or q['final_option_ids'] is not None:raise ValueError('audit_front_mcq:unreviewed_release')
            if q['scope']['source_interval_s']!=[event['start_frame']/group['fps'],event['end_frame_exclusive']/group['fps']]:raise ValueError('audit_front_mcq:question_scope')
            if q['GT_option_ids']!=event['gt_option_ids']:raise ValueError('audit_front_mcq:GT_mismatch')
            if event['origin']=='GT_anomaly':
                matched=any(r['start_frame']<=event['start_frame'] and r['end_frame']+1>=event['end_frame_exclusive'] and all(not flag or r['labels'][i] for i,flag in enumerate(event['labels'])) for r in event['atr_sources'])
                atr_supported+=matched
                if not matched:atr_unmatched.append(event['event_id'])
            if (result['status']=='ok')!=(q['visual_review'] is not None):issues.append(dict(group_id=group['group_id'],status='export_stale_during_generation'))
            durations.append(event['duration_s'])
    if maxerr>1/30:raise ValueError('audit_front_mcq:PTS')
    audit=dict(status='complete' if completed==len(groups) and not issues else 'partial',questions=len(qs),GT_events=sum(e['origin']=='GT_anomaly' for e in events),
               proxy_events=sum(e['origin']!='GT_anomaly' for e in events),groups=len(groups),completed_groups=completed,
               visual_completed_questions=sum(q['visual_review'] is not None for q in qs),
               question_status=dict(Counter(q['automatic_status'] for q in qs)),
               source_files=len(documents),unique_source_actions=len(pointers),
               video_count=len({g['source_video'] for g in groups}),frame_entries=frames,unique_source_frames=len(source_refs),
               minimum_target_frame_count=min(targetcounts) if targetcounts else None,maximum_PTS_difference_s=maxerr,
               ATR_supported_GT_events=atr_supported,ATR_unmatched_GT_events=atr_unmatched,
               event_duration_bins=dict(Counter(duration_bin(d) for d in durations)),remaining=issues,
               conclusions='candidates only; model judgments not human verification; no inferred Correct',formal_release=False)
    save_json(FOLDER/'audit.json',audit)
    print({k:v for k,v in audit.items() if k!='remaining'})


if __name__=='__main__':main()
