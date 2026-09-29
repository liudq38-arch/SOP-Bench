import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import av
import numpy as np
from PIL import Image,ImageDraw

from impact_qa.anomaly_multiview import FOLDER,prepare
from impact_qa.common import fingerprint,read_json,save_json


def render(case, refresh_headers=False):
    folder = FOLDER/'frames'/case['case_id']
    folder.mkdir(parents=True,exist_ok=True)
    manifest = folder/'manifest.json'
    version=fingerprint([case,Path(__file__).read_text()])
    if manifest.exists():
        result=read_json(manifest)
        if refresh_headers:
            if not all(Path(x['path']).exists() for x in result['frames']):
                raise ValueError('multiview:cannot_refresh_missing_frames:'+case['case_id'])
            with Image.open(result['sheet']) as old:
                sheet=old.copy()
            draw=ImageDraw.Draw(sheet)
            draw.rectangle((0,0,sheet.width,39),fill='white')
            a,b=case['target_interval_frames'];fps=case['fps']
            label='approximate review window' if case['mapping'].get('not_a_native_GT_event') else 'native action interval'
            draw.text((5,8),f"{case['case_id']} | {case['target_hand']} | {case['view']} | {label} {a/fps:.3f}-{b/fps:.3f}s",fill='black')
            sheet.save(result['sheet'],quality=96)
            result['header_revision']={'previous_renderer':result['version'],'frame_data_changed':False,'scope_label':label}
            result['version']=version
            save_json(manifest,result)
            return result
        if result['version']!=version:
            raise ValueError('multiview:changed_renderer_requires_new_directory')
        if all(Path(x['path']).exists() for x in result['frames']) and Path(result['sheet']).exists():
            return result
    a,b=case['target_interval_frames'];ca,cb=case['context_interval_frames'];fps=case['fps']
    indices=sorted(set(np.rint(np.concatenate([np.linspace(ca,max(ca,a-1),4),np.linspace(a,b-1,12),np.linspace(min(b,cb-1),cb-1,4)])).astype(int).tolist()))
    rows=[]
    sheet=Image.new('RGB',(1500,40+300*int(np.ceil(len(indices)/3))),'white');draw=ImageDraw.Draw(sheet)
    label='approximate review window' if case['mapping'].get('not_a_native_GT_event') else 'native action interval'
    draw.text((5,8),f"{case['case_id']} | {case['target_hand']} | {case['view']} | {label} {a/fps:.3f}-{b/fps:.3f}s",fill='black')
    with av.open(case['source_video']) as container:
        stream=container.streams.video[0];stream.thread_count=2
        rate=float(stream.average_rate)
        origin=float((stream.start_time or 0)*stream.time_base)
        container.seek(max(0,int((origin+indices[0]/rate)/stream.time_base)),stream=stream,backward=True)
        wanted=set(indices)
        for frame in container.decode(stream):
            pts=float(frame.pts*frame.time_base)
            idx=round((pts-origin)*rate)
            if idx>indices[-1]:break
            if idx not in wanted:continue
            im=frame.to_image();path=folder/f'f{idx:07d}.jpg';im.save(path,quality=96)
            if case['view']=='front':im=im.crop((round(im.width*.1),round(im.height*.30),round(im.width*.9),im.height))
            im.thumbnail((500,274));k=len(rows);x,y=k%3*500,40+k//3*300;sheet.paste(im,(x,y))
            scope='TARGET' if a<=idx<b else 'BEFORE' if idx<a else 'AFTER'
            draw.text((x+3,y+277),f'{scope} f{idx:07d} PTS {pts:.3f}s',fill='red' if scope=='TARGET' else 'black')
            rows.append({'source_frame_index':idx,'frame_id':f'f{idx:07d}','pts_s':pts,'annotation_time_s':idx/fps,'scope':scope,'path':str(path)})
    if [x['source_frame_index'] for x in rows]!=indices:
        raise ValueError('multiview:missing_source_frames:'+case['case_id'])
    path=folder/'sheet.jpg';sheet.save(path,quality=96)
    result={'case_id':case['case_id'],'version':version,'sheet':str(path),'frames':rows,'stream_average_rate':rate,'annotation_fps':fps,'stream_start_s':origin,'max_annotation_pts_clock_delta_s':max(abs(x['pts_s']-origin-x['annotation_time_s']) for x in rows)}
    save_json(manifest,result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--refresh-headers',action='store_true');args=parser.parse_args()
    import torch
    import PIL
    preflight={'cuda':torch.cuda.is_available(),'visible_gpus':torch.cuda.device_count(),'torch':torch.__version__,'cuda_runtime':torch.version.cuda,'av':av.__version__,'pillow':PIL.__version__,'model_requests':0}
    FOLDER.mkdir(parents=True,exist_ok=True);save_json(FOLDER/'preflight.json',preflight)
    cases=prepare()
    for c in cases[:10]:print(c['case_id'],c['target_interval_frames'],c['mapping']['status'],flush=True)
    if args.prepare_only:return
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda c:render(c,args.refresh_headers),cases))
    save_json(FOLDER/'frame_manifest.json',results)
    print({'cases':len(results),'frame_entries':sum(len(x['frames']) for x in results)},flush=True)


if __name__=='__main__':main()
