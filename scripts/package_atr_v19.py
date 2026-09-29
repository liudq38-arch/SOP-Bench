import json
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from impact_qa.common import FFMPEG, OUT, ROOT, read_jsonl, save_json, save_jsonl


def main():
    folder=OUT/'atr_v19'
    run_folder=OUT/'atr_v19_1'
    cases={c['case_id']:c for c in read_jsonl(folder/'cases.jsonl')}
    results=read_jsonl(run_folder/'results.jsonl') if (run_folder/'results.jsonl').exists() else []
    drafts=[];stats=defaultdict(Counter);paired=defaultdict(dict)
    for r in results:
        c=cases[r['case_id']]
        stats[r['view']]['cases']+=1
        decisions={x['kind']:x for x in r.get('decisions',[])}
        for q in r['stages'].get('generate',{}).get('items',[]):
            decision=decisions.get(q['kind'],{})
            status=decision.get('status','not_answerable' if not q['answerable'] else 'pipeline_incomplete')
            draft={'contract_id':r['case_id']+':'+q['kind'],'case_id':r['case_id'],'pair_id':r['pair_id'],'view':r['view'],'trial':c['trial'],'atr_labels':c['shared_gt']['atr_labels'],**q,'status':status,'decision':decision,'pipeline_error':r.get('error'),'formal_release':False,'human_review':'pending'}
            drafts.append(draft)
            stats[r['view']]['slots']+=1
            if q['answerable']:stats[r['view']]['drafts']+=1;stats[r['view']]['draft_'+q['kind']]+=1
            if status=='model_screened_unvalidated':stats[r['view']]['screened']+=1;stats[r['view']]['screened_'+q['kind']]+=1
            paired[(r['pair_id'],q['kind'])][r['view']]=status
    comparison=Counter()
    for key,views in paired.items():
        if set(views)!= {'ego','front'}:comparison['incomplete_pair_slot']+=1;continue
        e=views['ego']=='model_screened_unvalidated';f=views['front']=='model_screened_unvalidated'
        comparison['both_screened' if e and f else 'ego_only' if e else 'front_only' if f else 'neither_screened']+=1
    save_jsonl(run_folder/'qa_drafts.jsonl',drafts)
    save_json(ROOT/'reports/impact_qa/atr_v19_1_summary.json',{'by_view':{k:dict(v) for k,v in stats.items()},'paired_screening':dict(comparison),'errors':[{'case_id':r['case_id'],'error':r.get('error')} for r in results if r['status']!='complete'],'same_model_roles':True,'screening_not_accuracy':True,'formal_release':False})
    def video(c):
        dest=folder/'clips'/(c['case_id']+'.mp4');dest.parent.mkdir(exist_ok=True)
        start=max(0,c['interval_s'][0]-3);end=min(c['metadata']['num_frames']/c['metadata']['fps'],c['interval_s'][1]+20)
        if not dest.exists():
            temporary=dest.with_name(dest.stem+'.tmp.mp4')
            subprocess.run([FFMPEG,'-nostdin','-v','error','-ss',str(start),'-i',c['source_video'],'-t',str(end-start),'-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(temporary)],check=True,capture_output=True,timeout=180)
            temporary.replace(dest)
        return {'case_id':c['case_id'],'pair_id':c['pair_id'],'view':c['view'],'path':str(dest),'target_start_local_s':c['interval_s'][0]-start,'target_end_local_s':c['interval_s'][1]-start,'original_start_s':start,'original_end_s':end}
    with ThreadPoolExecutor(max_workers=4) as pool:clips=list(pool.map(video,cases.values()))
    save_jsonl(folder/'review_clips.jsonl',clips)
    by_pair=defaultdict(dict)
    for c in cases.values():by_pair[c['pair_id']][c['view']]=c
    for pair,views in by_pair.items():
        board=Image.new('RGB',(1920,980),'white');draw=ImageDraw.Draw(board)
        for col,view in enumerate(['ego','front']):
            c=views[view]
            for j,index in enumerate([4,8,13,19,23,27]):
                im=c['images'][index];x=col*960+(j%2)*480;y=(j//2)*320
                pic=Image.open(im['path']);pic.thumbnail((480,280));board.paste(pic,(x,y+35))
                draw.text((x+5,y+4),f'{pair} {view} {im["evidence_id"]}',fill='black')
                draw.text((x+5,y+18),f'{im["role"]} {im["relative_time_s"]:.2f}s from target onset',fill='black')
        dest=folder/'boards'/(pair+'.jpg');dest.parent.mkdir(exist_ok=True);board.save(dest,quality=95)
    print({'draft_slots':len(drafts),'clips':len(clips),'view_stats':{k:dict(v) for k,v in stats.items()},'paired':dict(comparison)},flush=True)


if __name__=='__main__':main()
