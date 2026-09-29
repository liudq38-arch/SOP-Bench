from fractions import Fraction
from hashlib import sha256
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

from impact_qa.common import fingerprint, read_json, save_json
from impact_qa.source_frames import extract_source_frames


def prepare_media(group, folder, config):
    source=Path(group['source_video'])
    key=fingerprint([group['group_id'], source.stat().st_size,source.stat().st_mtime_ns,config['video_pixel_budget'],Path(__file__).read_text()])
    root=folder/'media'/group['group_id']
    manifest=root/'manifest.json'
    if manifest.exists():
        value=read_json(manifest)
        if value['preparation_key']!=key or sha256(Path(value['path']).read_bytes()).hexdigest()!=value['sha256']:
            raise ValueError('front_mcq_media:cache_changed:'+group['group_id'])
        return value
    a,b=group['start_frame'],group['end_frame_exclusive']
    indices=set(np.rint(np.linspace(a,b-1,64)).astype(int).tolist())
    for event in group['events']:
        count=min(32,max(8,int(np.ceil(event['duration_s']*2))))
        indices.update(np.rint(np.linspace(event['start_frame'],event['end_frame_exclusive']-1,count)).astype(int).tolist())
    indices=sorted(indices)
    if len(indices)%2:
        candidate=next(i for i in range(a,b) if i not in indices)
        indices=sorted(indices+[candidate])
    extracted=extract_source_frames(source,indices,root/'frames',group['fps'])
    path=root/'model.mp4'
    tmp=path.with_suffix('.tmp.mp4')
    mapped=[]
    with av.open(str(tmp),'w') as out:
        stream=out.add_stream('libx264',rate=4)
        stream.width,stream.height=1200,576
        stream.pix_fmt='yuv420p'
        stream.options={'crf':'20','preset':'veryfast'}
        for k,row in enumerate(extracted['frames']):
            original=Image.open(row['path'])
            crop=original.crop((round(.04*original.width),round(.2*original.height),round(.96*original.width),original.height))
            crop.thumbnail((960,540))
            canvas=Image.new('RGB',(1200,576),'black')
            canvas.paste(crop,(0,24))
            inset=original.copy();inset.thumbnail((240,190));canvas.paste(inset,(960,24))
            draw=ImageDraw.Draw(canvas)
            draw.text((5,5),f"{row['frame_id']} SOURCE {row['pts_s']:.3f}s",fill='white')
            targets=[str(i+1)+':'+e['hand'] for i,e in enumerate(group['events']) if e['start_frame']<=row['source_frame_index']<e['end_frame_exclusive']]
            draw.text((5,554),'TARGET '+','.join(targets) if targets else 'CONTEXT ONLY',fill='yellow' if targets else 'white')
            frame=av.VideoFrame.from_image(canvas);frame.pts=k;frame.time_base=Fraction(1,4)
            for packet in stream.encode(frame):out.mux(packet)
            mapped.append(dict(frame_id=row['frame_id'],source_frame_index=row['source_frame_index'],source_pts_s=row['pts_s'],
                               local_pts_s=row['pts_s']-a/group['fps'],encoded_s=k/4,path=row['path']))
        for packet in stream.encode():out.mux(packet)
    tmp.replace(path)
    from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
    height,width=smart_resize(len(mapped),576,1200,min_pixels=4096,max_pixels=config['video_pixel_budget'])
    value=dict(path=str(path.resolve()),sha256=sha256(path.read_bytes()).hexdigest(),preparation_key=key,
               source_video=str(source),source_interval_frames=[a,b],sampled_frames=mapped,
               sampling_strategy='64 context frames plus 8-32 frames per complete target; nonuniform source-time sampling',
               encoded_fps=4,playback_is_not_realtime=True,
               media_io_kwargs={'video':{'video_backend':'opencv','fps':4,'num_frames':len(mapped)}},
               mm_processor_kwargs={'do_sample_frames':False,'size':{'shortest_edge':4096,'longest_edge':config['video_pixel_budget']}},
               estimated_visual_tokens=int(np.ceil(len(mapped)/2)*(height//32)*(width//32)),
               target_sample_counts={e['event_id']:sum(e['start_frame']<=f['source_frame_index']<e['end_frame_exclusive'] for f in mapped) for e in group['events']})
    if any(n<2 for n in value['target_sample_counts'].values()):
        raise ValueError('front_mcq_media:undersampled_target')
    save_json(manifest,value)
    return value
