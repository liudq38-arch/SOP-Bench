from collections import Counter
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_audit import verify_native_action
from scripts.inspect_spatial_rules import FOLDER, prepare


def main():
    base = prepare()
    followup = read_jsonl(FOLDER/'followup_cases.jsonl')
    assert fingerprint(followup) == read_json(FOLDER/'followup_selection.json')['cases_fingerprint']
    cases = base + followup
    manifests = {m['case_id']:m for m in read_json(FOLDER/'frame_manifest.json') + read_json(FOLDER/'followup_frame_manifest.json')}
    notes = read_json(FOLDER/'direct_review_notes.json')
    documents, frames, segments, rows = {}, set(), set(), []
    maximum_delta = 0
    for case in cases:
        cid=case['case_id'];a,b=case['target_interval_frames'];ca,cb=case['context_interval_frames']
        assert 0<=ca<=a<b<=cb and Path(case['source_video']).is_file(),cid
        manifest=manifests[cid]
        assert len(manifest['frames']) == 18 and Path(manifest['sheet']).is_file(),cid
        assert abs(manifest['stream_average_rate']-case['fps'])<1e-8,cid
        for frame in manifest['frames']:
            idx=frame['source_frame_index']
            assert ca<=idx<cb and Path(frame['path']).is_file(),cid
            expected='TARGET' if a<=idx<b else 'BEFORE' if idx<a else 'AFTER'
            assert frame['scope']==expected,cid
            delta=abs(frame['pts_s']-manifest['stream_start_s']-frame['annotation_time_s'])
            maximum_delta=max(maximum_delta,delta)
            assert delta<.001,cid
            frames.add((case['source_video'],idx))
        assert case['native_target_actions']==[r for r in case['native_context_actions'] if r['hand']==case['target_hand'] and r['start_frame']<b and r['end_frame_exclusive']>a],cid
        for action in case['native_context_actions']:
            assert '/TAS-B/'+case['view']+'/' in action['source']['path'],cid
            segments.add(verify_native_action(action,documents))
        for action in case['anchor']['actions']:
            segments.add(verify_native_action(action,documents))
        aid=case['anchor']['anchor_id'];note=notes['notes'][aid]
        rows.append(dict(case_id=cid,anchor_id=aid,trial_id=case['trial_id'],view=case['view'],hand=case['target_hand'],interval_s=[a/case['fps'],b/case['fps']],native_annotation=case['native_target_actions'],reference_front_annotation=case['anchor']['actions'],mapping=case['mapping'],crossview_match_accepted=False if cid=='p7_spatial_ego' else 'local_candidate_not_frame_alignment',review=note,observation_scope='joint_top_ego_operation_review; limitations_in_review_reason',evidence=manifest['frames'],sheet=manifest['sheet'],reviewer=notes['reviewer'],human_review='unreviewed',formal_release=False))
    assert len(rows)==len(manifests)==len({r['case_id'] for r in rows})==44
    assert {r['anchor_id'] for r in rows}==set(notes['notes'])
    details=read_json(FOLDER/'details/manifest.json')
    assert len(details)==6
    for detail in details:
        assert Path(detail['path']).is_file() and Path(detail['source']).is_file()
    result=dict(target_operations=21,additional_context_windows=2,view_windows=44,trials=len({c['trial_id'] for c in cases}),participants=len({c['trial_id'].split('_')[0] for c in cases}),front_target_phases={'anomaly':10,'normal':10,'recovery':1},contact_sheets_reviewed=44,sampled_frame_entries=792,unique_source_frames=len(frames),detail_full_frames_reviewed=6,detail_frames_reused=True,mapping_statuses=dict(Counter(c['mapping']['status'] for c in cases)),rejected_automatic_crossview_matches=['p7_spatial_ego'],source_files_verified=len(documents),source_segments_verified=len(segments),max_annotation_pts_delta_s=maximum_delta,local_supported_spatial_examples=['p6_spatial','p9_spatial'],probable_missing_label_candidates=['p6_spatial_ego'],possible_false_positive_or_missing_constraint=['p10_spatial'],official_universal_rules_confirmed=0,model_requests=0,new_QA=0,raw_annotations_modified=False,independent_holdout=False,classification_accuracy=None,reviewer=notes['reviewer'])
    save_jsonl(FOLDER/'visual_reviews.jsonl',rows)
    save_json(FOLDER/'audit.json',result)
    paths=['scripts/inspect_spatial_rules.py','scripts/inspect_spatial_followups.py','scripts/audit_spatial_rules.py','impact_qa/evidence_audit.py','impact_qa/source_frames.py','impact_qa/anomaly_multiview.py','prompts/impact_qa/anomaly_first_principles_v4.txt']
    save_json(FOLDER/'code_manifest.json',{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    print(result)


if __name__=='__main__':
    main()
