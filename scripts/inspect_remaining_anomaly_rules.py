import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.anomaly_multiview import anchor, map_interval
from impact_qa.common import TYPES, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.evidence_audit import verify_native_action
from impact_qa.mcq_native import native_trial, stable_runs
from impact_qa.review_frames import render_case


FOLDER = ROOT / 'outputs/impact_qa/remaining_rules_v1'
SPECS = [
    ('wt1', 'wrong_tool', 'KI03AR28_Disassembly_B_005', 'right', 57.467),
    ('wt2', 'wrong_tool', 'NA07GE21_Disassembly_A_002', 'right', 105.067),
    ('wt3', 'wrong_tool', 'AL07EJ17_Disassembly_B_005', 'right', 36.767),
    ('wt4', 'wrong_tool', 'SS07EL13_Disassembly_A_004', 'right', 105.3),
    ('wp1', 'wrong_part', 'ER10WE06_Reassembly_A_001', 'right', 63.6),
    ('wp2', 'wrong_part', 'ER10WE06_Reassembly_A_001', 'right', 119.767),
    ('wp3', 'wrong_part', 'KI05KO01_Reassembly_A_003', 'right', 16.767),
    ('wp4', 'wrong_part', 'KI05KO01_Reassembly_A_003', 'left', 62.667),
    ('wp5', 'wrong_part', 'KI03AR28_Reassembly_A_003', 'right', 5.2),
    ('wp6', 'wrong_part', 'MA07LF04_Disassembly_A_001', 'right', 34.433),
    ('wp7', 'wrong_part', 'LE06AS03_Reassembly_A_004', 'right', 4.6),
    ('h1', 'handling', 'ER10WE06_Reassembly_A_001', 'right', 21.867),
    ('h2', 'handling', 'LE07UF17_Disassembly_A_003', 'right', 205.967),
    ('h3', 'handling', 'MA07LF04_Disassembly_A_001', 'right', 68.033),
    ('h4', 'handling', 'LE06AS03_Disassembly_A_001', 'right', 315.267),
    ('h5', 'handling', 'KJ03JM25_Reassembly_A_003', 'left', 19.133),
    ('pr1', 'procedural', 'SS07EL13_Reassembly_A_001', 'right', 137.067),
    ('pr2', 'procedural', 'ER10WE06_Disassembly_A_002', 'right', 110.033),
    ('pr3', 'procedural', 'MA07LF04_Disassembly_A_001', 'left', 286.4),
    ('pr4', 'procedural', 'MA07LF04_Reassembly_A_001', 'left', 114.5),
    ('pr5', 'procedural', 'LE06AS03_Reassembly_B_005', 'right', 51.5),
    ('t1', 'temporal', 'LE06AS03_Reassembly_B_005', 'left', 224.567),
    ('t2', 'temporal', 'KI05KO01_Disassembly_A_001', 'right', 219.533),
    ('t3', 'temporal', 'TO08CO25_Disassembly_A_003', 'left', 28.9),
    ('t4', 'temporal', 'AL07EJ17_Reassembly_A_003', 'right', 85.4),
    ('t5', 'temporal', 'MA07LF04_Reassembly_A_002', 'right', 13.733),
]
CONTROLS = [
    ('wt1n', 'wrong_tool', 'KI03AR28_Disassembly_B_005', 'right', 64.733, 'loosen_screw'),
    ('wp1n', 'wrong_part', 'ER10WE06_Reassembly_A_001', 'right', 66.3, 'mount_adapter_plate'),
    ('h1n', 'handling', 'ER10WE06_Reassembly_A_001', 'right', 17.433, 'insert_bevel_gear'),
    ('pr1n', 'procedural', 'SS07EL13_Reassembly_A_001', 'right', 195.667, 'seat_bearing_plate'),
    ('t3n', 'temporal', 'NA07GE21_Disassembly_A_001', 'right', 58.533, 'hold_lever'),
]


def prepare():
    frozen = FOLDER / 'selection_frozen.json'
    if frozen.exists():
        cases = read_jsonl(FOLDER / 'cases.jsonl')
        if fingerprint(cases) != read_json(frozen)['cases_fingerprint']:
            raise ValueError('remaining_rules:changed_selection')
        return cases
    refs, cases, documents, unavailable = [], [], {}, []
    for spec in SPECS + CONTROLS:
        key, category, name, hand, start = spec[:5]
        trial = native_trial(name, 'front')
        if len(spec) == 5:
            matches = [r for r in stable_runs(trial) if r['hand'] == hand and abs(r['start_frame']/trial['fps']-start) < .02]
            if len(matches) != 1 or not matches[0]['labels'][TYPES.index(category)]:
                raise ValueError('remaining_rules:run_selection:' + key)
            selected = matches[0]
            actions = selected['actions']
            role = 'anomaly_candidate'
        else:
            matches = [r for r in trial['actions'] if r['hand'] == hand and r['action'] == spec[5] and abs(r['start_frame']/trial['fps']-start) < .02]
            if len(matches) != 1 or any(matches[0]['labels']) or matches[0]['phase'] != 'normal':
                raise ValueError('remaining_rules:control_selection:' + key)
            selected = matches[0]
            actions = [selected]
            role = 'normal_comparison_not_certified_matched'
        ref = dict(anchor_id=key, category=category, role=role, trial_id=name, hand=hand, fps=trial['fps'], start_frame=selected['start_frame'], end_frame_exclusive=selected['end_frame_exclusive'], actions=actions, purpose='targeted_diagnostic_not_independent_validation')
        refs.append(ref)
        for requested_view in ['top', 'ego']:
            view = requested_view
            candidate = native_trial(name, view)
            if ref['end_frame_exclusive']/ref['fps'] > candidate['frame_count']/candidate['fps']:
                unavailable.append(dict(anchor_id=key, requested_view=view, reason='reference_interval_beyond_view_duration', reference_end_s=ref['end_frame_exclusive']/ref['fps'], view_duration_s=candidate['frame_count']/candidate['fps'], fallback_view='front'))
                view = 'front'
            native = native_trial(name, view)
            if view == 'front':
                a, b, mapping = ref['start_frame'], ref['end_frame_exclusive'], dict(status='native_reference_fallback', requested_view=requested_view)
            elif len(actions) == 1:
                a, b, mapping = map_interval(ref, native)
            else:
                first = anchor(trial, actions[0], 'boundary_candidate')
                last = anchor(trial, actions[-1], 'boundary_candidate')
                a, _, left = map_interval(first, native)
                _, b, right = map_interval(last, native)
                mapping = dict(status='aggregate_context_from_boundary_candidates', start_mapping=left, end_mapping=right, not_frame_synchronization=True, not_a_native_GT_event=True)
            fps = native['fps']
            before, after = (15, 18) if category in ['procedural', 'wrong_part'] else (6, 12)
            ca, cb = max(0, a-round(before*fps)), min(native['frame_count'], b+round(after*fps))
            ctx = [r for r in native['actions'] if r['start_frame'] < cb and r['end_frame_exclusive'] > ca]
            c = dict(case_id=key+'_'+view, category=category, role=role, anchor=ref, trial_id=name, view=view, target_hand=hand, target_interval_frames=[a,b], context_interval_frames=[ca,cb], fps=fps, source_video=native['source_video'], mapping=mapping, native_target_actions=[r for r in ctx if r['hand']==hand and r['start_frame']<b and r['end_frame_exclusive']>a], native_context_actions=ctx, sample_counts=[4,16,4] if (b-a)/fps>30 else [4,10,4], formal_release=False, human_review='unreviewed')
            if not Path(c['source_video']).is_file() or not 0 <= ca <= a < b <= cb <= native['frame_count']:
                raise ValueError('remaining_rules:media_or_interval:' + c['case_id'])
            for r in actions + ctx:
                verify_native_action(r, documents)
            cases.append(c)
    save_jsonl(FOLDER / 'anchors.jsonl', refs)
    save_jsonl(FOLDER / 'cases.jsonl', cases)
    save_jsonl(FOLDER / 'first10_cases.jsonl', cases[:10])
    save_json(FOLDER / 'unavailable_views.json', unavailable)
    save_json(frozen, dict(cases_fingerprint=fingerprint(cases), anchors=len(refs), windows=len(cases), source_documents=len(documents), not_independent_holdout=True, annotation_truth_assumed=False))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--category', choices=TYPES)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    import torch, av, PIL
    if not torch.cuda.is_available():
        raise RuntimeError('remaining_rules:cuda_preflight_failed')
    save_json(FOLDER / 'preflight.json', dict(torch=torch.__version__, cuda_available=True, visible_gpus=torch.cuda.device_count(), cuda_runtime=torch.version.cuda, av=av.__version__, pillow=PIL.__version__, model_requests=0, renderer='CPU PyAV 3 workers, 2 decode threads each', gpu_snapshot=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,driver_version','--format=csv,noheader'],text=True)))
    cases = prepare()
    for c in cases[:10]:
        print(c['case_id'], c['target_interval_frames'], c['mapping']['status'], flush=True)
    if args.prepare_only:
        return
    selected = [c for c in cases if not args.category or c['category'] == args.category]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda c: render_case(c, FOLDER), selected))
    save_json(FOLDER / ('frame_manifest_'+(args.category or 'all')+'.json'), results)
    print(dict(windows=len(results), frame_entries=sum(len(r['frames']) for r in results)), flush=True)


if __name__ == '__main__':
    main()
