from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
import time

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json


def revision(question):
    return fingerprint({k:question[k] for k in ['question_id','question','candidate_option_ids','GT_option_ids','scope','visual_review']})


@contextmanager
def locked(folder):
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'collaboration.lock').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        yield


def ledger(folder):
    path=folder/'collaborative_reviews.jsonl'
    latest={}
    if path.exists():
        for row in read_jsonl(path):latest[(row['question_id'],row['revision'],row['reviewer'])]=row
    by_question=defaultdict(list)
    for row in latest.values():by_question[row['question_id']].append(row)
    return dict(by_question)


def current_reviews(folder,question):
    return [r for r in ledger(folder).get(question['question_id'],[]) if r['revision']==revision(question)]


def review_index(folder,questions):
    entries=ledger(folder)
    return {q['question_id']:[r for r in entries.get(q['question_id'],[]) if r['revision']==revision(q)] for q in questions}


def claim(folder,questions,reviewer,preferred=None):
    reviewer=reviewer.strip()
    if not reviewer:return None,'请先填写审核昵称。'
    with locked(folder):
        path=folder/'claims.json'
        claims=read_json(path) if path.exists() else {}
        now=time.time()
        claims={k:v for k,v in claims.items() if now-v['updated_at']<1800}
        previous=ledger(folder)
        if preferred:
            candidates=[q for q in questions if q['question_id']==preferred]
        else:
            candidates=[q for q in questions if q.get('visual_review')]
        for q in candidates:
            qid=q['question_id'];rev=revision(q)
            active=claims.get(qid)
            if active and (active['reviewer']!=reviewer or not preferred):continue
            decisions=[r for r in previous.get(qid,[]) if r['revision']==rev]
            if not preferred and decisions:continue
            claims={k:v for k,v in claims.items() if v['reviewer']!=reviewer}
            claims[qid]=dict(reviewer=reviewer,updated_at=now,revision=rev)
            save_json(path,claims)
            return qid,'已领取；其他审核员领取下一题时会避开本题。'
        return None,'当前筛选下没有未领取、未审核且已有视觉依据的题目，可刷新或手动选择复核。'


def heartbeat(folder,qid,reviewer):
    with locked(folder):
        path=folder/'claims.json'
        claims=read_json(path) if path.exists() else {}
        if qid in claims and claims[qid]['reviewer']==reviewer:
            claims[qid]['updated_at']=time.time();save_json(path,claims)


def record(folder,question,expected_revision,reviewer,verdict,option_ids,note):
    reviewer=reviewer.strip()
    if not reviewer or len(reviewer)>60:raise ValueError('请填写不超过60字的审核昵称。')
    if revision(question)!=expected_revision:raise ValueError('题目或视觉依据已更新，请刷新后再保存。')
    if verdict not in ['pass','fail','unsure']:raise ValueError('审核结论无效。')
    if not set(option_ids).issubset(set('ABCDEFG')) or len(option_ids)!=len(set(option_ids)):raise ValueError('答案选项无效。')
    if 'A' in option_ids and len(option_ids)>1:raise ValueError('Correct不能和异常类型同时选择。')
    if verdict=='pass' and (not option_ids or not question.get('visual_review')):raise ValueError('通过前须有视觉依据并选择答案。')
    item=dict(question_id=question['question_id'],group_id=question['group_id'],revision=expected_revision,reviewer=reviewer,
              verdict=verdict,option_ids=option_ids,note=note.strip(),updated_at=datetime.now(timezone.utc).isoformat(),
              candidate_answer_changed=verdict=='pass' and sorted(option_ids)!=sorted(question['candidate_option_ids']),
              reviewed_snapshot={k:question[k] for k in ['question','GT_option_ids','candidate_option_ids','scope','visual_review']})
    with locked(folder):
        with (folder/'collaborative_reviews.jsonl').open('a') as handle:
            handle.write(json.dumps(item,ensure_ascii=False)+'\n');handle.flush();os.fsync(handle.fileno())
        path=folder/'claims.json';claims=read_json(path) if path.exists() else {}
        if question['question_id'] in claims and claims[question['question_id']]['reviewer']==reviewer:
            claims.pop(question['question_id']);save_json(path,claims)
    return item


def consensus(rows):
    if not rows:return '未审核'
    answers={(r['verdict'],tuple(sorted(r['option_ids'])) if r['verdict']=='pass' else ()) for r in rows}
    if len(answers)>1:return '意见不一致，待复核'
    verdict=rows[0]['verdict']
    label={'pass':'通过','fail':'不通过','unsure':'证据不足'}[verdict]
    return f'{len(rows)}人{label}'
