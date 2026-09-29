import base64
import math
from pathlib import Path
import threading

import av
from PIL import Image, ImageDraw, ImageFont

from impact_qa.common import ANNOTATIONS, fingerprint, read_json, save_json
from impact_qa.mcq_native import native_trial


FORBIDDEN_KEYS={'phase','anomaly_type','anomaly_types','GT_option_ids','candidate_option_ids','correct_option_ids','answer','correct_answer','GT_phase','origin','rule_ids','visual_review','visual_evidence','model_supported_option_ids','has_anomaly','labels'}
VIDEO_LOCKS={}
LOCK_GUARD=threading.Lock()


def assert_blind(value):
    if isinstance(value, dict):
        for k,v in value.items():
            if k in FORBIDDEN_KEYS:
                raise ValueError('mcq_sop_payload:label_leak:'+k)
            assert_blind(v)
    elif isinstance(value, list):
        for v in value:
            assert_blind(v)


def extract_sparse(video, indices, folder, fps):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    wanted=sorted(set(indices));missing=[i for i in wanted if not (folder/f'f{i:08d}.jpg').exists()]
    if missing:
        with av.open(str(video)) as container:
            stream=container.streams.video[0];stream.thread_count=2
            rate=float(stream.average_rate);origin=float((stream.start_time or 0)*stream.time_base)
            if abs(rate-fps)>max(.01,fps*.001):
                raise ValueError('mcq_sop_payload:fps_mismatch:'+str(video))
            groups=[]
            for index in missing:
                if groups and index-groups[-1][-1]<=round(fps*1.2):groups[-1].append(index)
                else:groups.append([index])
            for group in groups:
                targets=set(group);container.seek(max(0,int((origin+group[0]/fps)/stream.time_base)),stream=stream,backward=True)
                for frame in container.decode(stream):
                    index=round((float(frame.pts*stream.time_base)-origin)*fps)
                    if index>group[-1]:break
                    if index not in targets:continue
                    path=folder/f'f{index:08d}.jpg';tmp=path.with_suffix('.tmp.jpg')
                    frame.to_image().save(tmp,quality=92);tmp.replace(path);targets.remove(index)
                if targets:raise ValueError('mcq_sop_payload:missing_frames:'+str(sorted(targets)))
    return {i:folder/f'f{i:08d}.jpg' for i in wanted}


def build_case(question, group, segment, sop, folder, config):
    fps=float(group['fps']);clip_start=group['start_frame']/fps;clip_end=group['end_frame_exclusive']/fps
    a,b=segment['source_start_s'],segment['source_end_s'];duration=b-a
    first=math.ceil(a*fps-1e-7);last=math.ceil(b*fps-1e-7)-1
    count=config['target_frames_short'] if duration<4 else config['target_frames_medium'] if duration<20 else config['target_frames_long']
    target=sorted(set(round(first+(last-first)*i/(count-1)) for i in range(count)))
    if len(target)<8:raise ValueError('mcq_sop_payload:fewer_than_8_distinct_target_frames')
    before=sorted(set(i for i in [first-round(fps),first-max(1,round(fps*.25))] if group['start_frame']<=i<first))
    after=sorted(set(i for i in [last+max(1,round(fps*.25)),last+round(fps)] if last<i<group['end_frame_exclusive']))
    native=native_trial(group['trial_id'],group['view'])
    if abs(native['fps']-fps)>1e-6:raise ValueError('mcq_sop_payload:group_native_fps_mismatch')
    actions={'L':[],'R':[]}
    for action in native['actions']:
        if action['start_frame']>=group['end_frame_exclusive'] or action['end_frame_exclusive']<=group['start_frame']:continue
        start=max(action['start_frame']/fps,clip_start)-clip_start;end=min(action['end_frame_exclusive']/fps,clip_end)-clip_start
        ta,tb=max(start,segment['start_s']),min(end,segment['end_s'])
        actions['L' if action['hand']=='left' else 'R'].append(dict(t_start=round(start,6),t_end=round(end,6),action=action['action'],verb=action['verb'],object=action['noun'],in_target=tb>ta,target_overlap_s=[round(ta,6),round(tb,6)] if tb>ta else None))
    for seq in actions.values():seq.sort(key=lambda r:r['t_start'])
    stepdoc=read_json(ANNOTATIONS/'TAS-S'/group['view']/(native['video_id']+'.json'))
    sfps=float(stepdoc['meta_data']['fps']);hints=[]
    for row in stepdoc['segments']:
        start,end=row['f_start']/sfps,(row['f_end']+1)/sfps
        if start>=clip_end or end<=clip_start:continue
        hints.append(dict(t_start=round(max(start,clip_start)-clip_start,6),t_end=round(min(end,clip_end)-clip_start,6),step_name=row['label'],overlaps_target=start<b and end>a))
    candidates=[s for s in sop['steps'] if any(h['overlaps_target'] and (h['step_name']==s['tas_s_phase'] or h['step_name'].removeprefix('retrieve_') in s['tas_s_phase']) for h in hints)]
    if not candidates:candidates=sop['steps']
    current=[{k:s[k] for k in ['id','expected_parts','expected_tools','expected','requirement_certainty','unknown']} for s in candidates]
    case=dict(model=group['model'],workflow=group['workflow'],view=group['view'],clip_duration_s=round(group['duration_s'],6),target=dict(start_s=round(segment['start_s'],6),end_s=round(segment['end_s'],6),duration_s=round(segment['duration_s'],6),hand='L' if question['scope']['hand']=='left' else 'R'),current_step_candidates=current,current_step_candidates_are_hints=True,tas_b_hands=actions,tas_s_hints=hints,context_note='上下文帧仅帮助理解状态，不作为目标内证据；缺失某侧上下文时明确保留未知。')
    assert_blind(case);assert_blind(sop)
    indices=before+target+after
    with LOCK_GUARD:
        lock=VIDEO_LOCKS.setdefault(native['video_id'],threading.Lock())
    with lock:
        raw=extract_sparse(group['source_video'],indices,Path(folder)/'source_frames'/native['video_id'],fps)
    media_root=Path(folder)/'media'/fingerprint([question['question_id'],segment['segment_id']])[:20];media_root.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    frames=[]
    for n,index in enumerate(indices,1):
        role='target' if index in target else 'context_before' if index<first else 'context_after'
        timestamp=round(index/fps-clip_start,6);path=media_root/f'image_{n:02d}.jpg'
        if not path.exists():
            original=Image.open(raw[index]).convert('RGB');original.thumbnail((config['image_longest_side'],config['image_longest_side']))
            canvas=Image.new('RGB',(original.width,original.height+32),'black');canvas.paste(original,(0,32))
            ImageDraw.Draw(canvas).text((8,5),f'FRAME {n:02d} | CLIP {timestamp:.6f}s | {role.upper()}',font=font,fill='white');canvas.save(path,quality=91)
        frames.append(dict(frame_index=n,clip_timestamp_s=timestamp,source_frame_index=index,source_timestamp_s=index/fps,role=role,path=str(path.resolve())))
    case['image_timeline']=[{k:v for k,v in f.items() if k not in ['path','source_timestamp_s','source_frame_index']} for f in frames]
    case['sampling']=dict(target_count=len(target),context_before_count=len(before),context_after_count=len(after),maximum_target_frame_gap_s=round(max((y-x)/fps for x,y in zip(target,target[1:])),6),unknown_between_samples=True)
    input_record=dict(question_id=question['question_id'],trial_id=group['trial_id'],segment_id=segment['segment_id'],sop=sop,case=case,frames=frames,source_video=group['source_video'],fps=fps,clip_source_start_s=clip_start)
    save_json(media_root/'manifest.json',input_record)
    return input_record


def image_contents(record):
    result=[]
    for f in record['frames']:
        result.append(dict(type='text',text=f"frame_index={f['frame_index']}, clip_timestamp_s={f['clip_timestamp_s']:.6f}, role={f['role']}"))
        result.append(dict(type='image_url',image_url=dict(url='data:image/jpeg;base64,'+base64.b64encode(Path(f['path']).read_bytes()).decode())))
    return result
