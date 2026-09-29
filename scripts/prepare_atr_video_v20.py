import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from impact_qa.common import OUT, ROOT, read_jsonl, save_json, save_jsonl
from impact_qa.video_input import FOLDER, prepare_windows


def main():
    cases=read_jsonl(OUT/'atr_v19/cases.jsonl')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[]
        for records in pool.map(prepare_windows,cases):
            results.extend(records);print(records[0]['case_id'],len(records),flush=True)
    save_jsonl(FOLDER/'windows.jsonl',results);save_jsonl(FOLDER/'first10.jsonl',results[:10])
    report={'cases':len(cases),'windows':len(results),'min_frames':min(r['decoded_frames'] for r in results),'max_frames':max(r['decoded_frames'] for r in results),'max_estimated_visual_tokens':max(r['estimated_visual_tokens'] for r in results),'profiles':{p:sum(r['profile']==p for r in results) for p in ['target','context']},'all_sample_indices_recorded':True,'double_sampling_disabled':True}
    save_json(ROOT/'reports/impact_qa/video_v20_precheck.json',report);print(report,flush=True)


if __name__=='__main__':main()
