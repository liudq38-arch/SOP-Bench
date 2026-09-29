from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.anomaly_multiview import anchor, map_interval
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_native import native_trial
from scripts.inspect_spatial_rules import FOLDER, render


SPECS = [
    ('p9_spatial', 'KI05KO01_Disassembly_A_001', 'left', 'store_lever', 55.567),
    ('p9_normal', 'KI05KO01_Disassembly_A_001', 'left', 'store_lever', 59.033),
    ('p10_spatial', 'LE06AS03_Reassembly_A_001', 'right', 'store_adapter_plate', 127.433),
    ('p11_normal', 'AL07EJ17_Disassembly_A_001', 'left', 'store_anti_vibration_handle', 9.167),
    ('p12_normal', 'NA07GE21_Disassembly_A_002', 'left', 'store_anti_vibration_handle', 8.433),
]


def build(ref, view, override=None):
    trial = native_trial(ref['trial_id'], view)
    a,b,mapping = map_interval(ref, trial)
    if override:
        a,b = [round(s*trial['fps']) for s in override]
        mapping = dict(status='manual_visual_followup_context', not_a_native_GT_event=True, not_frame_synchronization=True, prior_match=mapping)
    fps=trial['fps'];ca=max(0,a-round(4*fps));cb=min(trial['frame_count'],b+round(6*fps))
    ctx=[r for r in trial['actions'] if r['start_frame']<cb and r['end_frame_exclusive']>ca]
    result=dict(case_id=ref['anchor_id']+'_'+view, anchor=ref, trial_id=ref['trial_id'], view=view, target_hand=ref['hand'], target_interval_frames=[a,b], context_interval_frames=[ca,cb],fps=fps,source_video=trial['source_video'],mapping=mapping,native_context_actions=ctx,native_target_actions=[r for r in ctx if r['hand']==ref['hand'] and r['start_frame']<b and r['end_frame_exclusive']>a],formal_release=False,human_review='unreviewed')
    if not Path(result['source_video']).is_file():
        raise ValueError('spatial_followup:missing_video')
    return result


def main():
    frozen=FOLDER/'followup_selection.json'
    if frozen.exists():
        cases=read_jsonl(FOLDER/'followup_cases.jsonl')
        if fingerprint(cases)!=read_json(frozen)['cases_fingerprint']:
            raise ValueError('spatial_followup:changed_selection')
    else:
        cases=[]
        for key,name,hand,action,ts in SPECS:
            trial=native_trial(name,'front')
            rows=[r for r in trial['actions'] if r['hand']==hand and r['action']==action and abs(r['start_frame']/trial['fps']-ts)<.02]
            if len(rows)!=1:
                raise ValueError('spatial_followup:ambiguous_action:'+key)
            ref=anchor(trial,rows[0],'adaptive_followup_not_independent_validation')
            ref.update(anchor_id=key,pair_id=key.split('_')[0],role=rows[0]['phase'])
            cases.extend(build(ref,view) for view in ['top','ego'])
        old={r['anchor_id']:r for r in read_jsonl(FOLDER/'anchors.jsonl')}
        ref=dict(old['p7_spatial'],anchor_id='p7_visual_window')
        cases.append(build(ref,'ego',[50.5,52.3]))
        ref=dict(old['p6_spatial'],anchor_id='p6_identity_bridge')
        cases.append(build(ref,'top',[21.333,57]))
        save_jsonl(FOLDER/'followup_cases.jsonl',cases)
        save_json(frozen,dict(cases_fingerprint=fingerprint(cases),purpose='after_discovery_resolve_placement_and_matching',windows=len(cases)))
    for c in cases[:10]:
        print(c['case_id'],c['mapping']['status'],flush=True)
    results=[render(c) for c in cases]
    save_json(FOLDER/'followup_frame_manifest.json',results)
    print(dict(windows=len(cases),frame_entries=sum(len(r['frames']) for r in results)),flush=True)


if __name__=='__main__':
    main()
