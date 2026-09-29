from collections import Counter
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_audit import verify_native_action
from impact_qa.review_frames import render_case


BASE = ROOT / 'outputs/impact_qa/remaining_rules_v1'


def main():
    cases = [(BASE,c) for c in read_jsonl(BASE/'cases.jsonl')]
    cases += [(BASE/'followups',c) for c in read_jsonl(BASE/'followups/cases.jsonl')]
    refs = read_jsonl(BASE/'anchors.jsonl')+read_jsonl(BASE/'followups/anchors.jsonl')
    notes = read_json(BASE/'direct_review_notes.json')
    if {r['anchor_id'] for r in refs}!={n['anchor_id'] for n in notes} or len(notes)!=len(refs):
        raise ValueError('rule_audit:anchor_review_coverage')
    followups = {r['case_id']:r for r in read_json(BASE/'followups/direct_review_notes.json')}
    if set(followups)!={c['case_id'] for p,c in cases if p!=BASE}:
        raise ValueError('rule_audit:followup_review_coverage')
    frozen = read_json(BASE/'selection_frozen.json')
    if frozen['cases_fingerprint']!=fingerprint([c for p,c in cases if p==BASE]):
        raise ValueError('rule_audit:frozen_selection')
    frozen = read_json(BASE/'followups/selection_frozen.json')
    if frozen['fingerprint']!=fingerprint([c for p,c in cases if p!=BASE]):
        raise ValueError('rule_audit:frozen_followup_selection')
    documents,segments,unique_frames,records,asset_signatures = {},set(),set(),[],{}
    max_delta,entries = 0.,0
    by_anchor = {n['anchor_id']:dict(n,evidence_windows=[]) for n in notes}
    for folder,c in cases:
        manifest = read_json(folder/'frames'/c['case_id']/'manifest.json')
        assets = [manifest['sheet']]+[r['path'] for r in manifest['frames']]
        before = {p:(Path(p).stat().st_size,Path(p).stat().st_mtime_ns) for p in assets}
        cached = render_case(c,folder)
        if cached!=manifest or before!={p:(Path(p).stat().st_size,Path(p).stat().st_mtime_ns) for p in assets}:
            raise ValueError('rule_audit:cache_changed:'+c['case_id'])
        asset_signatures.update(before)
        a,b=c['target_interval_frames']
        ca,cb=c['context_interval_frames']
        if not 0<=ca<=a<b<=cb:
            raise ValueError('rule_audit:interval:'+c['case_id'])
        for action in c['anchor']['actions']+c['native_context_actions']:
            segments.add(verify_native_action(action,documents))
        expected = [r for r in c['native_context_actions'] if r['hand']==c['target_hand'] and r['start_frame']<b and r['end_frame_exclusive']>a]
        if expected!=c['native_target_actions']:
            raise ValueError('rule_audit:target_actions:'+c['case_id'])
        for r in manifest['frames']:
            idx=r['source_frame_index']
            if not ca<=idx<cb or r['scope']!=('TARGET' if a<=idx<b else 'BEFORE' if idx<a else 'AFTER'):
                raise ValueError('rule_audit:frame_scope:'+c['case_id'])
            max_delta=max(max_delta,abs(r['pts_s']-r['annotation_time_s']))
            unique_frames.add((c['source_video'],idx))
            entries+=1
        if max_delta>1e-6:
            raise ValueError('rule_audit:unexpected_media_clock')
        review=followups.get(c['case_id'])
        windows=dict(case_id=c['case_id'],view=c['view'],source_video=c['source_video'],target_interval_frames=[a,b],fps=c['fps'],mapping=c['mapping'],mapping_assessment=review['mapping_assessment'] if review else 'candidate_not_frame_synchronization',sheet=manifest['sheet'],manifest=str(folder/'frames'/c['case_id']/'manifest.json'),native_target_actions=c['native_target_actions'],frame_ids=[r['frame_id'] for r in manifest['frames']],frame_scopes=[r['scope'] for r in manifest['frames']])
        by_anchor[c['anchor']['anchor_id']]['evidence_windows'].append(windows)
        records.append(dict(**windows,anchor_id=c['anchor']['anchor_id'],category=c['category'],reviewer='Codex direct source-image inspection',human_review='unreviewed',formal_release=False))
    details=read_json(BASE/'followups/detail_manifest.json')
    for d in details:
        m=read_json(BASE/'followups/frames'/d['case_id']/'manifest.json')
        if not Path(d['path']).is_file() or not set(d['frames'])<={r['frame_id'] for r in m['frames']}:
            raise ValueError('rule_audit:detail_reference')
    fullframes=read_json(BASE/'detail_full_frames_reviewed.json')
    for p in fullframes:
        if str(BASE/p) not in asset_signatures:
            raise ValueError('rule_audit:full_frame_reference:'+p)
    for r in refs:
        n=by_anchor[r['anchor_id']]
        n['native_reference']=r
        n['reviewer']='Codex direct source-image inspection; GT visible; not a human expert'
        n['human_review']='unreviewed'
        n['formal_release']=False
        n['gt_is_ground_truth_for_independent_assessment']=False
        n['cause_QA_release']='hold_pending_constraint_and_event_validation'
    code=['impact_qa/review_frames.py','impact_qa/source_frames.py','scripts/inspect_remaining_anomaly_rules.py','scripts/inspect_anomaly_rule_followups.py','scripts/audit_remaining_anomaly_rules.py']
    save_json(BASE/'code_manifest.json',{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in code})
    save_json(BASE/'source_documents.json',{p:checksum for p,(_,checksum) in documents.items()})
    save_jsonl(BASE/'visual_reviews.jsonl',list(by_anchor.values()))
    save_jsonl(BASE/'window_reviews.jsonl',records)
    save_jsonl(BASE/'first10_reviews.jsonl',list(by_anchor.values())[:10])
    metrics=dict(target_operations=len(refs),base_anchors=31,additional_short_anchors=2,base_windows=62,followup_windows=10,view_windows=len(cases),trials=len({r['trial_id'] for r in refs}),participants=len({r['trial_id'].split('_')[0] for r in refs}),roles=dict(Counter(r['role'] for r in refs)),category_counts=dict(Counter(r['category'] for r in refs)),frame_entries=entries,unique_source_frames=len(unique_frames),sheets_reviewed=len(cases),detail_sheets_reviewed=len(details),detail_full_frames_reviewed=len(fullframes),detail_frames_reused=True,source_files_verified=len(documents),source_segments_verified=len(segments),max_annotation_pts_delta_s=max_delta,cache_assets_unchanged=len(asset_signatures),rejected_same_event_matches=['h6_ego'],unavailable_views=read_json(BASE/'unavailable_views.json'),local_tool_mismatch_candidates=['wt1','wt2','wt3'],local_control_loss_candidates=['h6','h7'],confirmed_official_universal_rules=0,raw_annotations_modified=False,model_requests=0,new_QA=0,independent_holdout=False,classification_accuracy=None,reviewer='Codex direct source-image inspection; not a human expert')
    save_json(BASE/'audit.json',metrics)
    print(metrics)


if __name__=='__main__':
    main()
