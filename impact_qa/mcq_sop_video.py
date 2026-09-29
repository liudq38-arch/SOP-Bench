import copy
import hashlib
import math
from pathlib import Path
import subprocess

from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
from vllm.multimodal.media.image import ImageMediaIO
from vllm.multimodal.media.video import VideoMediaIO

from impact_qa.common import FFMPEG, ROOT, fingerprint, read_json, save_json
from impact_qa.mcq_sop_payload import assert_blind, build_case
from impact_qa.video_input import windows


def target_windows(segment, group, config, profile):
    fps=group['fps']
    a=round(segment['start_s']*fps)
    b=round(segment['end_s']*fps)
    length=group['end_frame_exclusive']-group['start_frame']
    context=round(config['context_s']*fps)
    maximum=math.floor(profile['max_window_s']*fps)
    target_size=maximum-2*context
    overlap=round(config['target_overlap_s']*fps)
    if target_size<=overlap:raise ValueError('mcq_sop_video:invalid_window_policy')
    result=[]
    for i,(start,end) in enumerate(windows(a,b,target_size,overlap)):
        lo=max(0,start-context)
        hi=min(length,end+context)
        result.append(dict(index=i,clip_start_frame=lo,clip_end_frame_exclusive=hi,target_start_frame=start,target_end_frame_exclusive=end))
    return result


def prepare_video(question,group,segment,sop,window,config,profile_name):
    profile=config['profiles'][profile_name]
    folder=ROOT/config['output_root']
    source=Path(group['source_video'])
    fps=group['fps']
    lo=group['start_frame']+window['clip_start_frame']
    hi=group['start_frame']+window['clip_end_frame_exclusive']
    key=fingerprint([question['question_id'],segment['segment_id'],window,profile,config['encoded_width'],config['crf'],source.stat().st_size,source.stat().st_mtime_ns])[:24]
    path=folder/'videos'/f'{key}.mp4'
    manifest=folder/'video_manifests'/f'{key}.json'
    if manifest.exists():
        record=read_json(manifest)
        if not path.exists():raise ValueError('mcq_sop_video:missing_cached_video')
        return record
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        tmp=path.with_suffix('.tmp.mp4')
        args=[FFMPEG,'-nostdin','-v','error','-ss',format(lo/fps,'.12f'),'-i',str(source),'-frames:v',str(hi-lo),'-vf',f"scale={config['encoded_width']}:-2",'-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf',str(config['crf']),'-pix_fmt','yuv420p','-movflags','+faststart','-y',str(tmp)]
        run=subprocess.run(args,capture_output=True,text=True,timeout=300)
        if run.returncode:raise ValueError('mcq_sop_video:ffmpeg:'+run.stderr[-1000:])
        tmp.replace(path)
    io=dict(video_backend='opencv',fps=profile['fps'],num_frames=profile['num_frames'])
    frames,metadata=VideoMediaIO(ImageMediaIO(),**io).load_file(path)
    if metadata['total_num_frames']!=hi-lo or abs(metadata['fps']-fps)>1e-4:
        raise ValueError('mcq_sop_video:encoded_timing_mismatch')
    if not 8<=len(frames)<=profile['num_frames']:raise ValueError('mcq_sop_video:frame_count_outside_policy')
    v1_config=read_json(ROOT/'configs/impact_qa/mcq_sop_visual_v1.json')
    base=build_case(question,group,segment,sop,folder/'text_context',v1_config)
    case=copy.deepcopy(base['case'])
    shift=window['clip_start_frame']/fps
    end=window['clip_end_frame_exclusive']/fps
    duration=(hi-lo)/fps
    ta=(window['target_start_frame']-window['clip_start_frame'])/fps
    tb=(window['target_end_frame_exclusive']-window['clip_start_frame'])/fps
    case['target'].update(start_s=round(ta,6),end_s=round(tb,6),duration_s=round(tb-ta,6))
    case['clip_duration_s']=round(duration,6)
    case['time_basis']='input_video_window_seconds; output evidence must use these times, not source trial or parent clip times'
    case['context_note']='本次视频时间从0开始；仅target区间内行为属于待判定目标，前后视频用于上下文。输出将由程序映射回原clip时间。'
    for hand in ['L','R']:
        seq=[]
        for action in base['case']['tas_b_hands'][hand]:
            a=max(shift,action['t_start'])-shift
            b=min(end,action['t_end'])-shift
            if b<=a:continue
            x,y=max(a,ta),min(b,tb)
            seq.append(dict(action,t_start=round(a,6),t_end=round(b,6),in_target=y>x,target_overlap_s=[round(x,6),round(y,6)] if y>x else None))
        case['tas_b_hands'][hand]=seq
    hints=[]
    for hint in base['case']['tas_s_hints']:
        a=max(shift,hint['t_start'])-shift
        b=min(end,hint['t_end'])-shift
        if b>a:hints.append(dict(hint,t_start=round(a,6),t_end=round(b,6),overlaps_target=b>ta and a<tb))
    case['tas_s_hints']=hints
    mapping=[]
    for i,index in enumerate(metadata['frames_indices'],1):
        role='target' if window['target_start_frame']<=window['clip_start_frame']+index<window['target_end_frame_exclusive'] else 'context_before' if window['clip_start_frame']+index<window['target_start_frame'] else 'context_after'
        mapping.append(dict(frame_index=i,clip_timestamp_s=round(index/fps,6),parent_clip_timestamp_s=round(shift+index/fps,6),source_frame_index=lo+index,role=role))
    case['image_timeline']=[dict(frame_index=f['frame_index'],video_timestamp_s=f['clip_timestamp_s'],role=f['role']) for f in mapping]
    selected=[f for f in mapping if f['role']=='target']
    gaps=[b['clip_timestamp_s']-a['clip_timestamp_s'] for a,b in zip(selected,selected[1:])]
    case['sampling']=dict(mode='video',requested_fps=profile['fps'],frame_cap=profile['num_frames'],decoded_frames=len(frames),target_count=len(selected),maximum_target_frame_gap_s=round(max(gaps,default=0),6),unknown_between_samples=True)
    h,w=frames.shape[1:3]
    nh,nw=smart_resize(len(frames),h,w,min_pixels=4096,max_pixels=profile['total_pixel_budget'])
    assert_blind(case)
    assert_blind(sop)
    record=dict(question_id=question['question_id'],trial_id=question['trial_id'],segment_id=segment['segment_id'],window_id=key,window=window,profile=profile_name,sop=sop,case=case,frames=mapping,video_path=str(path.resolve()),source_video=str(source),source_start_frame=lo,source_end_frame_exclusive=hi,clip_offset_s=shift,fps=fps,loader_metadata=metadata,media_io_kwargs={'video':io},mm_processor_kwargs={'do_sample_frames':False,'size':{'shortest_edge':4096,'longest_edge':profile['total_pixel_budget']}},processor_shape=[nh,nw],estimated_visual_tokens=math.ceil(len(frames)/2)*(nh//32)*(nw//32),video_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    save_json(manifest,record)
    return record
