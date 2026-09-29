import argparse
from collections import Counter
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import av
import numpy as np
from PIL import Image,ImageDraw

from impact_qa.common import read_json,read_jsonl,save_json


def contact_sheet(record,folder):
    media=record['media']
    with av.open(media['path']) as container:
        frames=[frame.to_image() for frame in container.decode(video=0)]
    indices=np.unique(np.rint(np.linspace(0,len(frames)-1,min(12,len(frames)))).astype(int))
    width=420
    height=round(frames[0].height*width/frames[0].width)
    canvas=Image.new('RGB',(width*3,(height+25)*((len(indices)+2)//3)+35),'white')
    draw=ImageDraw.Draw(canvas)
    draw.text((5,8),record['case_id']+' / '+record['view'],fill='black')
    for n,i in enumerate(indices):
        x,y=(n%3)*width,35+(n//3)*(height+25)
        canvas.paste(frames[i].resize((width,height)),(x,y))
        mapped=media['sampled_frames'][i]
        draw.text((x+5,y+height+4),f"{mapped['frame_id']} source {mapped['source_pts_s']:.3f}s",fill='black')
    path=folder/'contact_sheets'/(record['case_id']+'.jpg')
    path.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(path,quality=94)
    return str(path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--round',default='native_r1')
    args=parser.parse_args()
    folder=ROOT/'outputs/impact_qa/mcq_grouped_v2'/args.round
    cases={c['case_id']:c for c in read_jsonl(folder/'cases.jsonl')}
    errors=[]
    sheets=[]
    questions=[]
    hashed={}
    for path in sorted((folder/'results').glob('*.json')):
        r=read_json(path)
        if r['status']!='ok':
            errors.append([r['case_id'],'generation_failed'])
            continue
        c=cases[r['case_id']]
        q=r['question']
        m=r['media']
        a,b=q['scope']['source_interval_frames']
        expected=[chr(66+i) for i,v in enumerate(c['event']['labels']) if v] or ['A']
        checks={'answer':q['correct_option_ids']==expected,'native_view':c['view']==q['view'],'bounds':all(a<=f['source_frame_index']<b for f in m['sampled_frames']),'clock':all(abs(f['local_pts_s']-(f['source_frame_index']-a)/c['clip']['fps'])<1e-6 for f in m['sampled_frames']),'video_hash':hashlib.sha256(Path(m['path']).read_bytes()).hexdigest()==m['sha256'],'release_closed':not q['formal_release']}
        for item in c['event']['actions']:
            source=ROOT/item['source']['path']
            if source not in hashed:
                hashed[source]=hashlib.sha256(source.read_bytes()).hexdigest()
            checks['source_'+item['source']['pointer']]=hashed[source]==item['source']['sha256']
        errors.extend([r['case_id'],key] for key,value in checks.items() if not value)
        sheets.append({'case_id':r['case_id'],'path':contact_sheet(r,folder)})
        questions.append(q)
    if len(questions)!=len(cases):
        errors.append(['population','not_all_cases_completed'])
    report={'cases':len(cases),'completed':len(questions),'hard_errors':errors,'option_counts':dict(Counter(o for q in questions for o in q['correct_option_ids'])),'diagnostic_only':sum(q['diagnostic_only'] for q in questions),'contact_sheets':sheets,'formal_release':False}
    save_json(folder/'structural_audit.json',report)
    print({k:v for k,v in report.items() if k!='contact_sheets'})
    if errors:
        raise SystemExit(1)


if __name__=='__main__':
    main()
