import argparse
import csv
import html
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.validation import qualifies_for_review_pass


PAGE = '''<!doctype html>
<html lang="zh"><meta charset="utf-8"><title>IMPACT QA 人工审阅</title>
<style>body{font:16px system-ui;margin:24px auto;max-width:1400px;background:#f5f6fa;color:#172b4d}header{display:flex;gap:14px;align-items:center;position:sticky;top:0;background:#f5f6fa;padding:12px;z-index:1}button,select{padding:8px}main{display:grid;grid-template-columns:1fr 1fr;gap:24px}section{background:white;padding:20px;border-radius:8px}video{width:100%}textarea{width:98%;min-height:70px;margin:6px 0;font:14px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;background:#eef2f7;padding:10px}.frames{display:flex;overflow:auto;gap:8px}.frames img{width:180px}.qa{border-top:1px solid #ddd;margin-top:20px;padding-top:12px}.badge{padding:5px;background:#ffe9a8}small{color:#52627a}</style>
<header><b>IMPACT QA 人工审阅</b><button id="prev">上一条</button><select id="event"></select><button id="next">下一条</button><button id="export">导出审核 JSON</button><span id="progress"></span></header>
<p>所有记录均为机器候选。请观看目标时间内指定手的操作。接受、修改或拒绝，并填写理由；标注标签与视觉是否一致也需核查。修改自动保存于当前浏览器，点击导出获得独立审阅记录。</p>
<main><section><h2 id="title"></h2><p id="scope"></p><video id="video" controls preload="metadata"></video><p id="origin"></p><div class="frames" id="frames"></div><details><summary>原始事件与标注</summary><pre id="annotation"></pre></details><details><summary>视觉观察与事实</summary><pre id="facts"></pre></details><details><summary>提示词与自动核验</summary><pre id="audit"></pre></details></section><section id="questions"></section></main>
<script id="records" type="application/json">__DATA__</script>
<script>
const records=JSON.parse(document.getElementById('records').textContent);const storeKey='impact-qa-review-__VERSION__';let edits=JSON.parse(localStorage.getItem(storeKey)||'{}');let current=0;
const el=id=>document.getElementById(id);const text=(id,value)=>el(id).textContent=value;const save=()=>{localStorage.setItem(storeKey,JSON.stringify(edits));text('progress',Object.keys(edits).length+' 条已编辑 / '+records.length+' 事件')};
records.forEach((r,i)=>{const o=document.createElement('option');o.value=i;o.textContent=(i+1)+' '+r.event.phase+' '+r.event_id;el('event').append(o)});
function editor(parent,key,qa,label,audit){const box=document.createElement('div');box.className='qa';const h=document.createElement('h3');h.textContent=label;box.append(h);const saved=edits[key]||{};const q=document.createElement('textarea');q.value=saved.question??qa.question;const a=document.createElement('textarea');a.value=saved.answer??(typeof qa.answer==='string'?qa.answer:JSON.stringify(qa.answer));const state=document.createElement('select');['pending_human_review','accept','edit','reject'].forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;state.append(o)});state.value=saved.decision||'pending_human_review';const note=document.createElement('textarea');note.placeholder='审核理由、证据时间点、修改说明';note.value=saved.reason||'';const info=document.createElement('pre');info.textContent=JSON.stringify(audit,null,2);const update=()=>{edits[key]={event_id:records[current].event_id,item_key:key,question:q.value,answer:a.value,decision:state.value,reason:note.value,reviewed_at:new Date().toISOString(),source_run_key:records[current].run_key};save()};[q,a,note].forEach(x=>x.oninput=update);state.onchange=update;box.append(q,a,state,note,info);parent.append(box)}
function render(){const r=records[current],e=r.event;el('event').value=current;text('title',e.action+' / '+e.hand);text('scope','原视频目标 '+e.start_s.toFixed(3)+'–'+e.end_s_exclusive.toFixed(3)+' 秒；片段内目标 '+(e.start_s-e.context_start_s).toFixed(3)+'–'+(e.end_s_exclusive-e.context_start_s).toFixed(3)+' 秒');el('video').src='clips/'+e.event_id+'.mp4';text('origin',e.video_id+' | '+e.phase+' | '+e.anomaly_types.join(', '));el('frames').replaceChildren();(r.evidence||[]).filter(f=>f.media_type!=='video').forEach(f=>{const d=document.createElement('div'),im=document.createElement('img'),caption=document.createElement('small');im.src=f.review_path;im.loading='lazy';caption.textContent=f.evidence_id+' '+f.requested_time_s.toFixed(2)+'s';d.append(im,caption);el('frames').append(d)});text('annotation',JSON.stringify(e,null,2));text('facts',JSON.stringify({observation:r.observation,refined:r.refined_observation,facts:r.facts},null,2));text('audit',JSON.stringify({version:r.prompt_version,structural:r.structural_issues,review:r.review,prompts:r.prompts},null,2));el('questions').replaceChildren();if(r.agent_revision)editor(el('questions'),r.agent_revision.qa_id,r.agent_revision,'研究代理目视修订建议（待真人复核）',{method:r.agent_revision.creation_method,evidence:r.agent_revision.reviewed_artifact,limits:r.agent_revision.limits});(r.generation?.qa_pairs||[]).forEach((q,i)=>editor(el('questions'),r.event_id+'__open_'+i,q,'开放题 '+(i+1),{support:q.supporting_fact_ids,evidence:q.evidence_ids,machine_review:r.review?.reviews?.find(x=>x.qa_index===i),agent_visual_review:r.agent_visual_reviews?.[String(i)]}));if(r.category_qa)editor(el('questions'),r.event_id+'__category',r.category_qa,'类别判断题（原生多标签）',{visibility:r.category_qa.visibility_status,conflicts:r.category_qa.label_conflicts});save()}
el('event').onchange=()=>{current=Number(el('event').value);render()};el('prev').onclick=()=>{current=Math.max(0,current-1);render()};el('next').onclick=()=>{current=Math.min(records.length-1,current+1);render()};el('export').onclick=()=>{const blob=new Blob([JSON.stringify({dataset:'IMPACT-QA-pilot',prompt_version:'__VERSION__',reviews:Object.values(edits)},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='impact_human_reviews.json';a.click();URL.revokeObjectURL(a.href)};if(records.length)render();
</script></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    records = []
    screening_path = REPORTS / 'visual_audit' / f'{args.version}_screening.json'
    screening = {r['qa_id']: r for r in read_json(screening_path)['reviews']} if screening_path.exists() else {}
    prompts = {p.stem: p.read_text() for p in (Path(__file__).resolve().parents[1] / 'prompts/impact_qa' / args.version).glob('*.txt')}
    for path in sorted((OUT / 'runs' / args.version).glob('*/*.json')):
        record = read_json(path)
        if record['status'] == 'ok':
            record['prompts'] = prompts
            for f in record.get('evidence', []):
                f['review_path'] = '../' + str(Path(f['path']).relative_to(OUT))
            records.append(record)
    seed_path = OUT / 'agent_proposed_revisions.jsonl'
    seed_index = {r['event_id']: r for r in read_jsonl(seed_path)} if seed_path.exists() else {}
    revision_rows = []
    for r in records:
        if r['event_id'] in seed_index:
            revision = dict(seed_index[r['event_id']], prompt_version=args.version, source_run_key=r['run_key'])
            r['agent_revision'] = revision
            revision_rows.append(revision)
    save_jsonl(OUT / 'agent_revision_candidates.jsonl', revision_rows)
    open_rows, categories, audit_rows = [], [], []
    for r in records:
        e = r['event']
        common = {'event_id': e['event_id'], 'split': e['split'], 'video_id': e['video_id'], 'hand': e['hand'], 'start_s': e['start_s'], 'end_s': e['end_s_exclusive'], 'prompt_version': args.version, 'review_status': 'pending_human_review'}
        for i, pair in enumerate(r['generation'].get('qa_pairs', [])):
            review = next((x for x in r['review'].get('reviews', []) if x.get('qa_index') == i), {})
            row = dict(common, qa_id=e['event_id'] + f'__open_{i}', **pair, machine_review=review, structural_issues=r.get('pair_structural_issues', {}).get(str(i), r.get('structural_issues', [])))
            row['agent_visual_review'] = screening.get(row['qa_id'])
            r.setdefault('agent_visual_reviews', {})[str(i)] = row['agent_visual_review']
            open_rows.append(row)
            audit_rows.append({'qa_id': row['qa_id'], 'event_id': e['event_id'], 'kind': 'open', 'split': e['split'], 'question': pair['question'], 'answer': pair['answer'], 'machine_decision': review.get('decision', 'missing'), 'human_decision': '', 'human_reason': '', 'edited_question': '', 'edited_answer': ''})
        categories.append(dict(common, **{k: v for k, v in r['category_qa'].items() if k != 'review_status'}))
        audit_rows.append({'qa_id': e['event_id'] + '__category', 'event_id': e['event_id'], 'kind': 'category', 'split': e['split'], 'question': r['category_qa']['question'], 'answer': json.dumps(r['category_qa']['answer']), 'machine_decision': r['category_qa']['visibility_status'], 'human_decision': '', 'human_reason': '', 'edited_question': '', 'edited_answer': ''})
    save_jsonl(OUT / 'open_candidates.jsonl', open_rows)
    save_jsonl(OUT / 'category_candidates.jsonl', categories)
    passed = [r for r in open_rows if qualifies_for_review_pass(r, r['machine_review'], r['structural_issues'])]
    save_jsonl(OUT / 'open_machine_pass_pending_human.jsonl', passed)
    save_jsonl(OUT / 'open_agent_flagged.jsonl', [r for r in open_rows if r.get('agent_visual_review') and r['agent_visual_review']['verdict'] != 'keep_candidate'])
    save_jsonl(OUT / 'open_needs_review.jsonl', [r for r in open_rows if r not in passed])
    public_inputs = [{'qa_id': r.get('qa_id', r['event_id'] + '__category'), 'video_id': r['video_id'], 'hand': r['hand'], 'start_s': r['start_s'], 'end_s': r['end_s'], 'question': r['question'], 'split': r['split']} for r in open_rows + categories]
    save_jsonl(OUT / 'evaluation_inputs.jsonl', public_inputs)
    review_dir = OUT / 'review'
    review_dir.mkdir(exist_ok=True)
    with (review_dir / 'review.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)
    page = PAGE.replace('__DATA__', json.dumps(records, ensure_ascii=False).replace('<', '\\u003c')).replace('__VERSION__', args.version)
    (review_dir / 'index.html').write_text(page)
    summary = {'version': args.version, 'events': len(records), 'open_candidates': len(open_rows), 'category_candidates': len(categories), 'machine_pass_pending_human': len(passed), 'machine_decisions': dict(Counter(r['machine_review'].get('decision') for r in open_rows)), 'human_reviewed': 0, 'agent_revision_candidates': len(revision_rows), 'agent_screening_decisions': dict(Counter(r['verdict'] for r in screening.values())), 'agent_flagged_machine_pass': sum(bool(r.get('agent_visual_review')) and r['agent_visual_review']['verdict'] != 'keep_candidate' for r in passed), 'split_counts': dict(Counter(r['split'] for r in open_rows)), 'dimensions': dict(Counter(r['dimension'] for r in open_rows)), 'machine_metrics_are_not_accuracy': True}
    save_json(REPORTS / 'final_candidate_summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
