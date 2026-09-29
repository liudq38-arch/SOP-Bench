import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_grouped import option_ids
from impact_qa.mcq_grouped_review import assess_event


def sheet(record, out):
    import av
    import numpy as np
    from PIL import Image, ImageDraw

    images = []
    for window in record['windows']:
        media = window['media']
        chosen = set(np.rint(np.linspace(0,len(media['sampled_frames'])-1,12)).astype(int).tolist())
        frames = []
        with av.open(media['path']) as container:
            for i, frame in enumerate(container.decode(video=0)):
                if i in chosen:
                    image = frame.to_image().resize((384,216))
                    tile = Image.new('RGB',(384,240),'white')
                    tile.paste(image,(0,0))
                    f=media['sampled_frames'][i]
                    ImageDraw.Draw(tile).text((4,220),f"{f['frame_id']} clip={f['local_pts_s']:.3f}s",fill='black')
                    frames.append(tile)
        canvas=Image.new('RGB',(384*4,240*3),'white')
        for i,tile in enumerate(frames):
            canvas.paste(tile,((i%4)*384,(i//4)*240))
        path=out/(record['unit_id']+'_'+window['window']['window_id']+'.jpg')
        path.parent.mkdir(parents=True,exist_ok=True)
        canvas.save(path,quality=90)
        images.append(str(path.relative_to(ROOT)))
    return images


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('round')
    parser.add_argument('--sheets',action='store_true')
    args=parser.parse_args()
    config=read_json(ROOT/'configs/impact_qa/mcq_grouped_v1.json')
    folder=ROOT/config['output_root']
    run=folder/args.round
    units={u['unit_id']:u for u in read_jsonl(folder/'candidate_units.jsonl')}
    selection=read_json(run/'selection.json')
    config=selection['config']
    records=[read_json(run/'results'/(k+'.json')) for k in selection['unit_ids']]
    hard,details,labels=[],[],Counter()
    for r in records:
        u=units.get(r['unit_id'])
        if r['status']!='ok':
            hard.append([r['unit_id'],'runtime_error'])
            continue
        for w in r['windows']:
            m=w['media']
            if hashlib.sha256(Path(m['path']).read_bytes()).hexdigest()!=m['sha256']:
                hard.append([r['unit_id'],'media_hash'])
            mapping={f['frame_id']:f for f in m['sampled_frames']}
            if len(mapping)!=m['actual_sample_count']:
                hard.append([r['unit_id'],'frame_mapping_duplicate'])
        q=r.get('question')
        if q:
            events=[e for ep in u['episodes'] for e in ep['events']]
            if q['correct_option_ids']!=option_ids(events):
                hard.append([r['unit_id'],'answer_union_mismatch'])
            if sorted(e['event_id'] for e in events)!=sorted(e['event_id'] for e in q['abnormal_segments']):
                hard.append([r['unit_id'],'incomplete_answer_segments'])
            for e in events:
                review=r['event_reviews'][e['event_id']]
                m=next(w['media'] for w in r['windows'] if w['media']['sha256']==review['media_sha256'])
                checked=assess_event(e,review['observation'],review['type_review'],m,config)
                if not checked['accepted']:
                    hard.append([r['unit_id'],'recomputed_visual_gate_failed'])
            labels.update(q['correct_option_ids'])
        details.append({'unit_id':r['unit_id'],'question':q,'held':r.get('held'),'false_positive':r.get('false_positive'),'event_reviews':r.get('event_reviews',{}),'contact_sheets':sheet(r,run/'contact_sheets') if args.sheets else []})
    report={'round':args.round,'completed_records':len(records),'questions':sum(bool(r.get('question')) for r in records),'retained_label_counts':dict(labels),'hard_errors':hard,'controls':sum(r['packaging']=='control' for r in records),'control_false_positives':sum(r.get('false_positive',False) for r in records),'formal_release':False,'quality_note':'Mechanical checks and model judgments; not independently measured human accuracy.'}
    save_json(run/'audit.json',report)
    save_jsonl(run/'audit_details.jsonl',details)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
