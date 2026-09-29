import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import ANNOTATIONS, FFPROBE, MEDIA, TYPES, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.source_frames import extract_source_frames
from impact_qa.v26_data import merged_intervals


OUT = ROOT / 'outputs/impact_qa/assembly_3d/complete_videos'
APP = ROOT / 'apps/impact_assembly_3d'
SELECTED = ['ER07AD15_Reassembly_A_004_front', 'NA07GE21_Reassembly_B_005_front']
LABELS = {'install_rotor_assembly': '转子轴组件安装', 'attach_adapter_plate': '适配板安装', 'insert_bearing_plate_assembly': '轴承板安装', 'install_locking_lever_assembly': '拨杆组件安装', 'screw_on_anti_vibration_handle': '侧手柄安装', 'finish_angle_grinder_assembly': '安装结束'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (APP / 'media').mkdir(exist_ok=True)
    atr = {}
    for path in (ANNOTATIONS / 'ATR').glob('atr_segments_*/*.jsonl'):
        for row in read_jsonl(path):
            if row['view'] == 'front' and '_Reassembly_' in row['video_id']:
                key = (row['video_id'], row['entity'], row['start_frame'], row['end_frame'], tuple(row['labels']))
                atr.setdefault(key, {**row, 'source_path': str(path.relative_to(ROOT))})
    rankings = []
    selected = []
    for path in sorted((ANNOTATIONS / 'TAS-B/front').glob('*_Reassembly_*.json')):
        data = read_json(path)
        step_path = ANNOTATIONS / 'TAS-S/front' / path.name
        steps = read_json(step_path)
        fps = float(steps['meta_data']['fps'])
        frames = steps['meta_data']['num_frames']
        errors = [dict(s, source_index=i) for i, s in enumerate(data['segments']) if s.get('phase') == 'anomaly' or any(s['anomaly_type'])]
        spans = merged_intervals([(s['start_frame'], s['end_frame']+1) for s in errors])
        error_seconds = sum(b-a for a, b in spans) / fps
        atr_rows = [r for r in atr.values() if r['video_id'] == path.stem]
        label_union_differences = []
        for hand in ['left', 'right']:
            original_all = merged_intervals([(s['start_frame'], s['end_frame']+1) for s in errors if s['entity'] == hand])
            derived_all = merged_intervals([(s['start_frame'], s['end_frame']+1) for s in atr_rows if s['entity'] == hand])
            if original_all != derived_all:
                raise ValueError(f'complete_video_selection: ATR anomaly-union mismatch {path.stem}/{hand}')
            for label in range(6):
                original = merged_intervals([(s['start_frame'], s['end_frame']+1) for s in errors if s['entity'] == hand and s['anomaly_type'][label]])
                derived = merged_intervals([(s['start_frame'], s['end_frame']+1) for s in atr_rows if s['entity'] == hand and s['labels'][label]])
                if original != derived:
                    label_union_differences.append(dict(hand=hand, label=TYPES[label], tas_b=original, atr=derived))
        asr_path = ANNOTATIONS / 'ASR/annotations' / (path.stem + '_asr.json')
        asr = read_json(asr_path) if asr_path.exists() else None
        coverage = sorted({s['label'] for s in steps['segments'] if s['label'] in LABELS})
        final = asr['state_sequence'][-1]['state'] if asr else None
        row = dict(video_id=path.stem, model=path.stem.split('_')[2], duration_s=frames/fps, anomaly_rows=len(errors), atr_segments=len(atr_rows), anomaly_union_s=error_seconds, anomaly_fraction=error_seconds/(frames/fps), has_asr=bool(asr), asr_final_all_installed=all(x == 1 for x in final) if final else None, step_coverage=coverage, atr_grouped_label_expansions=label_union_differences)
        rankings.append(row)
        if path.stem not in SELECTED:
            continue
        source = MEDIA.parent / 'front' / (path.stem + '.mp4')
        probe = json.loads(subprocess.check_output([FFPROBE, '-v', 'error', '-show_entries', 'format=duration,size:stream=codec_name,width,height,r_frame_rate', '-of', 'json', str(source)], text=True))
        if abs(float(probe['format']['duration']) - row['duration_s']) > 1/fps:
            raise ValueError('complete_video_selection: duration mismatch ' + str(source))
        required = set(LABELS) - ({'install_locking_lever_assembly'} if row['model'] == 'B' else set())
        if not required.issubset(coverage):
            raise ValueError('complete_video_selection: missing installation stage ' + path.stem)
        model = row['model']
        dest = APP / 'media' / ('assembly_' + model + '.mp4')
        if not dest.exists():
            dest.symlink_to(source)
        if dest.resolve() != source.resolve():
            raise ValueError('complete_video_selection: unexpected media target ' + str(dest))
        stage_rows = []
        for label, zh in LABELS.items():
            matching = [s for s in steps['segments'] if s['label'] == label]
            if matching:
                stage_rows.append(dict(label=label, title=zh, start_s=min(s['f_start'] for s in matching)/fps, end_s=(max(s['f_end'] for s in matching)+1)/fps))
        stage_rows.sort(key=lambda x: x['start_s'])
        times = sorted({0, 1, frames-1, max(0, frames-60), *[min(frames-1, round(t*fps)) for t in range(5, int(frames/fps), 10)], *[round((s['start_frame']+s['end_frame'])/2) for s in errors]})
        frame_info = extract_source_frames(source, times, OUT / model / 'frames', fps)
        thumbnails = frame_info['frames']
        sheet = Image.new('RGB', (4*320, ((len(thumbnails)+3)//4)*205), '#131d27')
        draw = ImageDraw.Draw(sheet)
        for i, frame in enumerate(thumbnails):
            im = Image.open(frame['path']).convert('RGB');im.thumbnail((320, 180))
            x, y = i%4*320, i//4*205
            sheet.paste(im, (x, y));draw.text((x+6, y+183), f"{frame['annotation_time_s']:.2f}s / frame {frame['source_frame_index']}", fill='white')
        sheet.save(OUT / model / 'contact_sheet.jpg', quality=92)
        poster = Image.open(thumbnails[-2]['path']);poster.save(APP / 'assets' / f'assembly_{model}_poster.jpg', quality=90)
        anomaly_rows = [dict(start_s=s['start_frame']/fps, end_s=(s['end_frame']+1)/fps, hand=s['entity'], types=[TYPES[i] for i, v in enumerate(s['anomaly_type']) if v], source_pointer=f"/segments/{s['source_index']}") for s in errors]
        record = dict(row, source_video=str(source), media_url='media/assembly_'+model+'.mp4', poster_url='assets/assembly_'+model+'_poster.jpg', video_sha256=digest(source), probe=probe, anomalies=anomaly_rows, steps=stage_rows, frames=frame_info, annotation_sha256={str(p.relative_to(ROOT)):digest(p) for p in [path, step_path]+([asr_path] if asr else [])}, atr_rows=atr_rows, visual_review='pending')
        selected.append(record)
    rankings.sort(key=lambda r: (r['model'], r['anomaly_union_s'], r['duration_s']))
    save_jsonl(OUT / 'all_front_assembly_rankings.jsonl', rankings)
    save_json(OUT / 'first10_precheck.json', rankings[:10])
    summary = {model:dict(total=sum(r['model']==model for r in rankings), zero_anomaly=sum(r['model']==model and r['anomaly_rows']==0 for r in rankings), shortest=min(r['duration_s'] for r in rankings if r['model']==model)) for model in ['A', 'B']}
    save_json(OUT / 'selection.json', dict(summary=summary, all_atr_tas_b_anomaly_unions_match=True, per_label_grouping_expansion_trials=sum(bool(r['atr_grouped_label_expansions']) for r in rankings), selected=selected, filtering='All anomaly labels retained, including <1.5s; union across hands, full original videos. ATR grouped type labels do not define exact per-type onset.'))
    public = [{k:r[k] for k in ['video_id','model','duration_s','anomaly_rows','atr_segments','anomaly_union_s','anomaly_fraction','has_asr','asr_final_all_installed','media_url','poster_url','anomalies','steps']} for r in selected]
    save_json(APP / 'assembly_videos.json', dict(summary=summary, videos=public))
    print(json.dumps(dict(summary=summary, selected=public), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
