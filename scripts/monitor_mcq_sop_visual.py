import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import read_json, read_jsonl, save_json


def alive(pid):
    try:
        stat=Path(f'/proc/{pid}/stat').read_text()
        command=Path(f'/proc/{pid}/cmdline').read_bytes()
        return stat.split(') ',1)[1][0]!='Z' and b'run_mcq_sop_visual.py' in command
    except (FileNotFoundError,PermissionError,ProcessLookupError):
        return False


def snapshot(folder):
    rows=[read_json(p) for p in (folder/'results').glob('*.json')]
    expected=sum(len(q['filter']['target_segments']) for q in read_jsonl(folder/'kept_questions.jsonl'))
    counts=Counter(r.get('verdict',r['status']) for r in rows)
    result=dict(expected=expected,returned=len(rows),pending=expected-len(rows),counts=dict(counts),failures=sum(r['status']!='ok' for r in rows),updated_unix=time.time())
    save_json(folder/'live_progress.json',result)
    return result


def main():
    folder=ROOT/'outputs/impact_qa/mcq_sop_visual_v1'
    with (folder/'monitor.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save_json(folder/'monitor_status.json',dict(pid=os.getpid(),started_unix=time.time(),status='monitoring'))
        pid=read_json(folder/'run_status.json').get('pid',0)
        while alive(pid):
            snapshot(folder)
            time.sleep(15)
        for attempt in range(3):
            progress=snapshot(folder)
            if progress['pending']==0 and progress['failures']==0:break
            with (folder/f'monitor_resume_{attempt}.log').open('w') as log:
                child=subprocess.Popen([sys.executable,'-u',str(ROOT/'scripts/run_mcq_sop_visual.py'),'--retry-failures'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                while child.poll() is None:
                    snapshot(folder)
                    time.sleep(15)
        with (folder/'final_audit.log').open('w') as log:
            subprocess.run([sys.executable,str(ROOT/'scripts/run_mcq_sop_visual.py'),'--report-only'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            subprocess.run([sys.executable,str(ROOT/'scripts/audit_mcq_sop_visual.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        progress=snapshot(folder)
        summary=read_json(folder/'summary.json')
        status='completed' if progress['pending']==0 and progress['failures']==0 else 'completed_with_failures' if progress['pending']==0 else 'incomplete'
        save_json(folder/'monitor_status.json',dict(pid=os.getpid(),finished_unix=time.time(),status=status,progress=progress))
        p=ROOT/'experiment_log.md'
        marker='### MCQ SOP视觉核验自动收尾 '+read_json(folder/'generation_frozen.json')['fingerprint'][:12]
        old=p.read_text()
        if marker not in old:
            detail={k:summary[k] for k in ['expected_segments','finished','pending','verdict_counts','anomaly_type_counts','failures','normal_but_gt_anomaly','insufficient_evidence_fraction']}
            p.write_text(old+'\n'+marker+'\n\n'+json.dumps(detail,ensure_ascii=False)+'\n\n结构/区间/无泄漏和源完整性审计见audit/validation.json；模型判断并非人工准确率。没有修改GT或原题。\n')
        if status=='completed':
            p=ROOT/'plan.md';old=p.read_text()
            p.write_text(old.replace('- [ ] 审计试跑后以3服务并发完整核验全部保留片段，断点续跑和失败独立记录。','- [x] Done 3服务并发完成全部保留片段核验，逐段checkpoint、失败重试和原响应保存；结果见mcq_sop_visual_v1/summary.json。'))
        print(json.dumps(dict(status=status,progress=progress),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
