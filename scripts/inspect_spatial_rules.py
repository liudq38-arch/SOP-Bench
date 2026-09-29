import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image, ImageDraw

from impact_qa.anomaly_multiview import anchor, map_interval
from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_native import native_trial
from impact_qa.source_frames import extract_source_frames


FOLDER = ROOT / 'outputs/impact_qa/spatial_rules_v1'
SPECS = [
    ('p1', 'MA07LF04_Reassembly_A_002', 'right', 'place_phillips_screwdriver', 168.733, 211.833),
    ('p2', 'NA07GE21_Disassembly_A_002', 'right', 'place_torx_screwdriver', 90.033, 24.567),
    ('p3', 'MA07LF04_Reassembly_A_001', 'right', 'place_combination_wrench', 80.733, None),
    ('p3n', 'MA07LF04_Reassembly_A_001', 'left', 'place_combination_wrench', None, 92.233),
    ('p4', 'KI03AR28_Disassembly_A_003', 'left', 'place_adapter_plate', 108.633, None),
    ('p4n', 'LE06AS03_Disassembly_A_003', 'left', 'place_adapter_plate', None, 127.133),
    ('p5', 'LE06AS03_Disassembly_A_004', 'right', 'place_bearing_plate', 72.833, None),
    ('p5n', 'MA07LF04_Disassembly_A_001', 'left', 'place_bearing_plate', None, 269.967),
    ('p6', 'KI05KO01_Disassembly_A_001', 'left', 'store_anti_vibration_handle', 17.9, None),
    ('p6n', 'KI05KO01_Disassembly_A_001', 'right', 'store_anti_vibration_handle', None, 57.0),
    ('p7', 'AL07EJ17_Disassembly_A_002', 'right', 'loosen_screw', 51.067, 60.533),
    ('p8', 'NA07GE21_Disassembly_A_004', 'right', 'place_torx_screwdriver', 49.133, 21.733),
]


def prepare():
    frozen = FOLDER / 'selection_frozen.json'
    if frozen.exists():
        rows = read_jsonl(FOLDER / 'cases.jsonl')
        if fingerprint(rows) != read_json(frozen)['cases_fingerprint']:
            raise ValueError('spatial:changed_selection')
        return rows
    refs, cases = [], []
    for pair, name, hand, action, bad, good in SPECS:
        trial = native_trial(name, 'front')
        comparison_role = 'recovery' if pair == 'p6n' else 'normal'
        for role, ts in [('spatial', bad), (comparison_role, good)]:
            if ts is None:
                continue
            matches = [r for r in trial['actions'] if r['hand'] == hand and r['action'] == action and abs(r['start_frame']/trial['fps']-ts) < .02]
            if len(matches) != 1:
                raise ValueError('spatial:ambiguous_selection:' + str((pair, role)))
            row = matches[0]
            expected = [0, 1, 0, 0, 0, 0] if role == 'spatial' else [0]*6
            if row['labels'] != expected or (role != 'spatial' and row['phase'] != role):
                raise ValueError('spatial:unexpected_label:' + pair)
            ref = anchor(trial, row, 'spatial_rule_discovery_not_independent_validation')
            ref.update(anchor_id=pair.removesuffix('n')+'_'+role, pair_id=pair.removesuffix('n'), role=role)
            refs.append(ref)
            for view in ['top', 'ego']:
                native = native_trial(name, view)
                a, b, mapping = map_interval(ref, native)
                fps = native['fps']
                ca, cb = max(0, a-round(4*fps)), min(native['frame_count'], b+round(6*fps))
                ctx = [r for r in native['actions'] if r['start_frame'] < cb and r['end_frame_exclusive'] > ca]
                case = dict(case_id=ref['anchor_id']+'_'+view, anchor=ref, trial_id=name, view=view, target_hand=hand, target_interval_frames=[a,b], context_interval_frames=[ca,cb], fps=fps, source_video=native['source_video'], mapping=mapping, native_context_actions=ctx, native_target_actions=[r for r in ctx if r['hand']==hand and r['start_frame']<b and r['end_frame_exclusive']>a], formal_release=False, human_review='unreviewed')
                if not Path(case['source_video']).is_file() or not 0<=ca<=a<b<=cb<=native['frame_count']:
                    raise ValueError('spatial:media_or_interval:'+case['case_id'])
                cases.append(case)
    if len(refs)!=16 or len(cases)!=32:
        raise ValueError('spatial:selection_count')
    save_jsonl(FOLDER/'anchors.jsonl', refs)
    save_jsonl(FOLDER/'cases.jsonl', cases)
    save_jsonl(FOLDER/'first10_cases.jsonl', cases[:10])
    save_json(frozen, dict(cases_fingerprint=fingerprint(cases), anchors=len(refs), windows=len(cases), selection='targeted_diagnostic', not_independent_holdout=True, comparisons_not_certified_matched=True))
    return cases


def render(case):
    folder = FOLDER/'frames'/case['case_id']
    manifest = folder/'manifest.json'
    version = fingerprint([case, Path(__file__).read_text(), (ROOT/'impact_qa/source_frames.py').read_text()])
    if manifest.exists():
        result = read_json(manifest)
        if result['version'] != version:
            raise ValueError('spatial:changed_renderer_requires_new_directory')
        if Path(result['sheet']).exists() and all(Path(r['path']).exists() for r in result['frames']):
            return result
    a,b=case['target_interval_frames']; ca,cb=case['context_interval_frames']; fps=case['fps']
    indices=np.rint(np.concatenate([np.linspace(ca,a-1,4),np.linspace(a,b-1,10),np.linspace(b,cb-1,4)])).astype(int).tolist()
    result=extract_source_frames(case['source_video'],indices,folder,fps)
    sheet=Image.new('RGB',(1800,40+360*int(np.ceil(len(result['frames'])/3))),'white')
    draw=ImageDraw.Draw(sheet)
    scope='APPROXIMATE window' if case['mapping'].get('not_a_native_GT_event') else 'native action interval'
    draw.text((8,8),f"{case['case_id']} {case['trial_id']} {case['target_hand']} {scope} {a/fps:.3f}-{b/fps:.3f}s",fill='black')
    for k,row in enumerate(result['frames']):
        idx=row['source_frame_index']
        row['scope']='TARGET' if a<=idx<b else 'BEFORE' if idx<a else 'AFTER'
        im=Image.open(row['path']); im.thumbnail((600,334))
        x,y=k%3*600,40+k//3*360
        sheet.paste(im,(x,y))
        draw.text((x+3,y+337),f"{row['scope']} {row['frame_id']} {row['pts_s']:.3f}s",fill='red' if row['scope']=='TARGET' else 'black')
    path=folder/'sheet.jpg';sheet.save(path,quality=96)
    result.update(case_id=case['case_id'],version=version,sheet=str(path))
    save_json(manifest,result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    import torch, av, PIL
    preflight=dict(torch=torch.__version__,cuda_available=torch.cuda.is_available(),visible_gpus=torch.cuda.device_count(),cuda_runtime=torch.version.cuda,av=av.__version__,pillow=PIL.__version__,model_requests=0)
    if not preflight['cuda_available']:
        raise RuntimeError('spatial:cuda_preflight_failed')
    save_json(FOLDER/'preflight.json',preflight)
    cases=prepare()
    for c in cases[:10]:
        print(c['case_id'],c['target_interval_frames'],c['mapping']['status'],flush=True)
    if args.prepare_only:
        return
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(render,cases))
    save_json(FOLDER/'frame_manifest.json',results)
    print(dict(cases=len(results),frame_entries=sum(len(x['frames']) for x in results)),flush=True)


if __name__=='__main__':
    main()
