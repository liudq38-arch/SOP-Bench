from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.anomaly_multiview import anchor, map_interval
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_audit import verify_native_action
from impact_qa.mcq_native import native_trial
from impact_qa.review_frames import render_case


BASE = ROOT / 'outputs/impact_qa/remaining_rules_v1'
OUT = BASE / 'followups'
CONTEXTS = [
    ('wp1_dense_top', 'wp1', 'top', 60, 70, 30, 'same_ring_orientation'),
    ('wp3_dense_front', 'wp3', 'front', 15, 20, 30, 'ego_out_of_frame'),
    ('pr1_bridge1_ego', 'pr1', 'ego', 148, 177, 30, 'closure_and_reopening'),
    ('pr1_bridge2_ego', 'pr1', 'ego', 177, 199, 24, 'internal_work_before_closure'),
    ('pr4_bridge_ego', 'pr4', 'ego', 140, 170, 32, 'adapter_state_after_cover_attempt'),
    ('h2_dense_ego', 'h2', 'ego', 205, 222, 32, 'shaft_and_gear_constraint'),
]
SHORT = [
    ('h6', 'ER07AD15_Reassembly_A_003', 'left', 47.833, 'pick_up_M4_nut'),
    ('h7', 'KE03ER16_Disassembly_A_001', 'right', 19.4, 'detach_lever'),
]


def prepare():
    frozen = OUT / 'selection_frozen.json'
    if frozen.exists():
        cases = read_jsonl(OUT / 'cases.jsonl')
        if fingerprint(cases) != read_json(frozen)['fingerprint']:
            raise ValueError('rule_followups:selection_changed')
        return cases
    refs = {a['anchor_id']: a for a in read_jsonl(BASE / 'anchors.jsonl')}
    cases, new_refs, documents = [], [], {}
    specs = []
    for key, parent, view, start, end, samples, purpose in CONTEXTS:
        native = native_trial(refs[parent]['trial_id'], view)
        specs.append((key, refs[parent], native, round(start*native['fps']), round(end*native['fps']), samples, dict(status='manual_context_not_native_event', purpose=purpose)))
    for key, trial_id, hand, start, name in SHORT:
        trial = native_trial(trial_id, 'front')
        matches = [a for a in trial['actions'] if a['hand']==hand and a['action']==name and abs(a['start_frame']/trial['fps']-start)<.02]
        if len(matches)!=1 or not matches[0]['labels'][2]:
            raise ValueError('rule_followups:short_selection:'+key)
        action = matches[0]
        ref = dict(anchor_id=key, category='handling', role='short_diagnostic_anomaly_candidate', trial_id=trial_id, hand=hand, fps=trial['fps'], start_frame=action['start_frame'], end_frame_exclusive=action['end_frame_exclusive'], actions=[action], purpose='short_control_failure_not_production')
        new_refs.append(ref)
        for view in ['top', 'ego']:
            native = native_trial(trial_id, view)
            a,b,mapping = map_interval(ref,native)
            specs.append((key+'_'+view,ref,native,a,b,b-a,mapping))
    for key,ref,native,a,b,samples,mapping in specs:
        fps = native['fps']
        ca,cb = max(0,a-round(2*fps)), min(native['frame_count'],b+round(3*fps))
        if not 0<=ca<=a<b<=cb<=native['frame_count']:
            raise ValueError('rule_followups:invalid_interval:'+key)
        context=[r for r in native['actions'] if r['start_frame']<cb and r['end_frame_exclusive']>ca]
        for action in ref['actions']+context:
            verify_native_action(action,documents)
        cases.append(dict(case_id=key,category=ref['category'],role='diagnostic_followup',anchor=ref,trial_id=ref['trial_id'],view=native['view'],target_hand=ref['hand'],target_interval_frames=[a,b],context_interval_frames=[ca,cb],fps=fps,source_video=native['source_video'],mapping=mapping,native_target_actions=[r for r in context if r['hand']==ref['hand'] and r['start_frame']<b and r['end_frame_exclusive']>a],native_context_actions=context,sample_counts=[4,samples,4],formal_release=False,human_review='unreviewed'))
    save_jsonl(OUT/'anchors.jsonl',new_refs)
    save_jsonl(OUT/'cases.jsonl',cases)
    save_jsonl(OUT/'first10_cases.jsonl',cases[:10])
    save_json(frozen,dict(fingerprint=fingerprint(cases),new_anchors=len(new_refs),windows=len(cases),source_documents=len(documents)))
    return cases


def main():
    import av, torch
    if not torch.cuda.is_available():
        raise RuntimeError('rule_followups:cuda_unavailable')
    print(dict(torch=torch.__version__,cuda=torch.version.cuda,gpus=torch.cuda.device_count(),av=av.__version__),flush=True)
    cases=prepare()
    for c in cases[:10]:
        print(c['case_id'],c['target_interval_frames'],c['mapping']['status'],flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda c:render_case(c,OUT),cases))
    save_json(OUT/'frame_manifest.json',results)
    print(dict(windows=len(results),frame_entries=sum(len(r['frames']) for r in results)),flush=True)


if __name__=='__main__':
    main()
