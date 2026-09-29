import html
import hashlib
import json
import os
from pathlib import Path


def write_review_page(path, cases):
    path = Path(path)
    cards = []
    for case in cases:
        identifier = html.escape(case['contract_id'], quote=True)
        clip = html.escape(os.path.relpath(case['clip_path'], path.parent), quote=True)
        sheet = html.escape(os.path.relpath(case['contact_sheet'], path.parent), quote=True)
        options = ''.join('<li>' + html.escape(k + ': ' + v) + '</li>' for k, v in case['options'].items())
        ratings = ''.join('<label>' + key + ' <select data-field="' + key + '"><option value="">待评</option><option>pass</option><option>uncertain</option><option>fail</option></select></label> ' for key in ['S', 'V', 'T', 'Q', 'M', 'D'])
        cards.append('<article data-id="' + identifier + '"><h2>' + identifier + '</h2><p>' + html.escape(case['question']) + '</p><video controls preload="none" src="' + clip + '"></video><p>原时间：' + html.escape(case['time_range']) + '</p><label>独立答案与证据时刻<textarea data-field="independent_answer"></textarea></label><label>可见性<select data-field="initial_visibility"><option value="">待评</option><option>answerable</option><option>uncertain</option><option>unanswerable</option></select></label><details><summary>查看时间抽帧（不是连续观察）</summary><img loading="lazy" src="' + sheet + '"></details><p>' + html.escape(case['mcq_question']) + '</p><ol>' + options + '</ol><label>独立MCQ选择<select data-field="independent_mcq"><option value="">待评</option><option>A</option><option>B</option><option>C</option><option>uncertain</option></select></label><details class="gt"><summary>揭示GT与生成答案（记录首次揭示时间）</summary><p>生成答案：' + html.escape(case['answer']) + '</p><p>GT参考答案：' + html.escape(case['gt_reference_answer']) + '</p><p>MCQ答案：' + html.escape(case['correct_answer']) + '</p><pre>' + html.escape(json.dumps(case['references'], ensure_ascii=False, indent=2)) + '</pre></details><div>' + ratings + '</div><label>处置<select data-field="decision"><option value="">待评</option><option>pass</option><option>revise</option><option>hold</option><option>reject</option></select></label><label>理由/修订建议<textarea data-field="reason"></textarea></label></article>')
    script = '''
const storageKey='impact-gt-v12-review-v1';
let records={};
try{records=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch(e){document.getElementById('status').textContent='本地缓存不可用，请及时导出。'}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(records));document.getElementById('status').textContent='已保存到本浏览器；请导出JSON留档。'}catch(e){document.getElementById('status').textContent='缓存失败，请立即导出JSON。'}}
document.querySelectorAll('article').forEach(article=>{
 const id=article.dataset.id;
 records[id]=records[id]||{contract_id:id,reviewer_kind:'human_or_agent_to_be_specified',human_review_status:'pending_human_review'};
 article.querySelectorAll('[data-field]').forEach(el=>{
  el.value=records[id][el.dataset.field]||'';
  el.addEventListener('input',()=>{records[id][el.dataset.field]=el.value;records[id].updated_at=new Date().toISOString();persist()});
 });
 article.querySelector('.gt').addEventListener('toggle',event=>{
  if(event.target.open&&!records[id].gt_first_revealed_at){records[id].gt_first_revealed_at=new Date().toISOString();records[id].answer_before_gt=records[id].independent_answer||'';records[id].mcq_before_gt=records[id].independent_mcq||'';persist()}
 });
});
document.getElementById('export').addEventListener('click',()=>{
 const reviewer=document.getElementById('reviewer').value.trim();
 const kind=document.getElementById('kind').value;
 const payload=Object.values(records).map(r=>({...r,reviewer,reviewer_kind:kind}));
 const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
 const link=document.createElement('a');link.href=url;link.download='impact-review-records.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
'''
    signature = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()[:20]
    script = script.replace("impact-gt-v12-review-v1", 'impact-review-' + signature)
    cards = [card.replace('<p>' + html.escape(case['mcq_question']) + '</p><ol>', '<details class="mcq"><summary>记录开放题答案后查看多选题</summary><p>' + html.escape(case['mcq_question']) + '</p><ol>').replace('</select></label><details class="gt">', '</select></label></details><details class="gt">') for card, case in zip(cards, cases)]
    script = script.replace("article.querySelector('.gt').addEventListener", "article.querySelector('.mcq').addEventListener('toggle',event=>{if(event.target.open&&!records[id].options_first_revealed_at){records[id].options_first_revealed_at=new Date().toISOString();records[id].answer_before_options=records[id].independent_answer||'';persist()}});\n article.querySelector('.gt').addEventListener")
    page = '<!doctype html><html lang="zh"><meta charset="utf-8"><title>IMPACT QA复查</title><style>body{font:16px sans-serif;max-width:1100px;margin:auto}article{border-top:1px solid #999;padding:24px 0}video,img{max-width:100%}textarea{display:block;width:95%;min-height:65px}pre{white-space:pre-wrap}label{margin:8px;display:inline-block}details{margin:12px 0}</style><h1>先独立回答，再揭示GT</h1><p>S源支持 / V视觉 / T时间 / Q问答 / M多选唯一性 / D数据隔离。先连续看片段，再记录答案与证据；程序不自动签署真人通过。</p><label>审核者<input id="reviewer"></label><label>身份<select id="kind"><option>human</option><option>research_agent</option></select></label><button id="export">导出审核JSON</button><p id="status"></p>' + '\n'.join(cards) + '<script>' + script + '</script></html>'
    path.write_text(page)
