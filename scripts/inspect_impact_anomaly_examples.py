from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import av
import numpy as np
from PIL import Image,ImageDraw

from impact_qa.common import ANNOTATIONS,read_json,save_json


SELECTIONS=[
    ('temporal','TO08CO25_Disassembly_A_003',25,46),
    ('spatial','NA07GE21_Disassembly_A_001',214,224),
    ('handling','KI03AR28_Disassembly_B_005',128,150),
    ('wrong_part','KI05KO01_Reassembly_A_003',27,43),
    ('wrong_tool','KI03AR28_Disassembly_B_005',57,70),
    ('procedural','SS07EL13_Reassembly_A_001',127,158),
]


def extract(item):
    category,trial,a,b=item
    view='front'
    doc=read_json(ANNOTATIONS/'TAS-B'/view/(trial+'_'+view+'.json'))
    fps=doc['meta_data']['fps']
    indices=np.rint(np.linspace(a*fps,b*fps,12)).astype(int).tolist()
    wanted=set(indices)
    source=Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos')/view/(trial+'_'+view+'.mp4')
    folder=ROOT/'reports/impact_qa/anomaly_taxonomy_audit/visual'
    folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    canvas=Image.new('RGB',(1440,4*322+30),'white')
    draw=ImageDraw.Draw(canvas)
    draw.text((6,7),category+' | '+trial+' | CONTEXT included; see native labels for exact target intervals',fill='black')
    with av.open(str(source)) as container:
        stream=container.streams.video[0]
        stream.thread_count=2
        container.seek(int(a/stream.time_base),stream=stream,backward=True)
        for frame in container.decode(stream):
            t=float(frame.pts*frame.time_base)
            index=round(t*fps)
            if index>indices[-1]:break
            if index not in wanted:continue
            original=frame.to_image()
            crop=original.crop((round(original.width*.24),round(original.height*.3),round(original.width*.8),round(original.height*.92)))
            crop=crop.resize((480,298))
            n=len(rows);x,y=(n%3)*480,30+(n//3)*322
            canvas.paste(crop,(x,y));draw.text((x+5,y+302),f'frame {index} | {t:.3f}s',fill='black')
            path=folder/f'{category}_{index}.jpg';original.save(path,quality=94)
            rows.append({'frame_index':index,'source_pts_s':t,'original_frame':str(path.relative_to(ROOT))})
    if len(rows)!=len(indices):raise ValueError('taxonomy_frames:missing:'+trial)
    sheet=folder/(category+'.jpg');canvas.save(sheet,quality=94)
    actions={x['id']:x['name'] for x in doc['action_labels']}
    context=[dict(s,action=actions[s['action_label']],source_pointer=f'/segments/{i}') for i,s in enumerate(doc['segments']) if s['start_frame']<b*fps and s['end_frame']>=a*fps]
    return {'category':category,'trial_id':trial,'view':view,'source':str(source),'fps':fps,'context_window_s':[a,b],'annotation':str((ANNOTATIONS/'TAS-B'/view/(trial+'_'+view+'.json')).relative_to(ROOT)),'source_frame_rows':rows,'sheet':str(sheet.relative_to(ROOT)),'context_actions':context,'reason_status':'requires_separate_normative_rule_not_implied_by_frames'}


def main():
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(extract,SELECTIONS))
    save_json(ROOT/'reports/impact_qa/anomaly_taxonomy_audit/visual/manifest.json',records)
    print({'cases':len(records),'frames':sum(len(r['source_frame_rows']) for r in records)})


if __name__=='__main__':
    main()
