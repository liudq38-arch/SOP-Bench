from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

from impact_qa.common import ROOT, TYPES, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.front_rule_metrics import rule_masks
from impact_qa.mcq_native import atr_index, native_trial, stable_runs


FOLDER = ROOT / 'outputs/impact_qa/front_mcq_expansion_v1'
OPTIONS = [
    {'id': 'A', 'name': 'Correct', 'definition': '指定时间和指定手的操作没有可确认的异常；不能与异常选项同时选择，不代表整段装配完成。'},
    {'id': 'B', 'name': 'Temporal', 'definition': '已具备推进条件却持续未启动、停滞或反复无效操作，或违反已确认时间要求；正常协作、检查和有效长操作不算。'},
    {'id': 'C', 'name': 'Spatial', 'definition': '部件或工具的位置、朝向、放置目的地违反适用的装配或摆放要求。'},
    {'id': 'D', 'name': 'Handling', 'definition': '当前阶段的操作方法、抓持、控制或施力不当；正常预拧、松后徒手旋出和双手配合不自动算错。'},
    {'id': 'E', 'name': 'Wrong part', 'definition': '实际选取或使用的部件/紧固件身份不适用于当前目标；不把仅方向不对或时机不对直接当错件。'},
    {'id': 'F', 'name': 'Wrong tool', 'definition': '实际使用的工具不适配目标接口或当前操作阶段；单纯持有工具不构成错误。'},
    {'id': 'G', 'name': 'Procedural', 'definition': '动作违反已确认的必要步骤或前置依赖；允许合法换序、试装和错误恢复。'},
]
PROXIES = ['H_hand_spin', 'S_place_prev_loosen', 'T_null_8', 'P_reassembly_dismount',
           'T_assembly_part_hold_quiet_other_8', 'H_tool_carried_finger', 'T_tool_carried_finger']


def duration_bin(seconds):
    return '<1.5s' if seconds < 1.5 else '1.5-5s' if seconds < 5 else '5-20s' if seconds < 20 else '20-60s' if seconds < 60 else '>=60s'


def balanced_order(groups):
    buckets = defaultdict(deque)
    for group in sorted(groups, key=lambda g: fingerprint(g['group_id'])):
        buckets[duration_bin(max(e['duration_s'] for e in group['events']))].append(group)
    output = []
    while any(buckets.values()):
        for key in ['>=60s', '20-60s', '5-20s', '1.5-5s', '<1.5s']:
            if buckets[key]:
                output.append(buckets[key].popleft())
    return output


def prepare():
    rows = read_jsonl(ROOT / 'outputs/impact_qa/front_rule_coverage_v1/rows.jsonl')
    rules = rule_masks(rows)
    hits = defaultdict(list)
    for key in PROXIES:
        for row, match in zip(rows, rules[key]['mask']):
            if match:
                hits[(row['action']['source']['path'], row['action']['source']['pointer'])].append(key)
    events = []
    for trial_id in sorted({r['trial_id'] for r in rows}):
        trial = native_trial(trial_id, 'front')
        for run in stable_runs(trial):
            if not any(run['labels']):
                continue
            rule_ids = sorted({key for a in run['actions'] for key in hits[(a['source']['path'], a['source']['pointer'])]})
            events.append(dict(run, event_id='fx_' + run['run_id'][3:], trial_id=trial_id,
                               origin='GT_anomaly', rule_ids=rule_ids,
                               proposed_categories=[t for t, flag in zip(TYPES, run['labels']) if flag]))
    for row in rows:
        action = row['action']
        rule_ids = hits[(action['source']['path'], action['source']['pointer'])]
        if any(action['labels']) or not rule_ids:
            continue
        categories = sorted({rules[key]['category'] for key in rule_ids}, key=TYPES.index)
        events.append(dict(event_id='fx_proxy_' + row['row_id'], trial_id=row['trial_id'], hand=action['hand'],
                           start_frame=action['start_frame'], end_frame_exclusive=action['end_frame_exclusive'],
                           duration_s=row['duration_s'], actions=[action], action_names=[action['action']],
                           labels=action['labels'], phase=action['phase'], origin='rule_candidate_without_GT_anomaly',
                           rule_ids=rule_ids, proposed_categories=categories))
    by_trial = defaultdict(list)
    for event in events:
        trial = native_trial(event['trial_id'], 'front')
        event['gt_option_ids'] = [chr(66 + i) for i, flag in enumerate(event['labels']) if flag]
        event['candidate_option_ids'] = [chr(66 + TYPES.index(t)) for t in event['proposed_categories']]
        event['atr_sources'] = [r for r in atr_index().get((trial['video_id'], event['hand']), []) if r['start_frame'] < event['end_frame_exclusive'] and r['end_frame'] + 1 > event['start_frame']]
        by_trial[event['trial_id']].append(event)
    groups = []
    for trial_id, items in sorted(by_trial.items()):
        trial = native_trial(trial_id, 'front')
        fps, total = trial['fps'], trial['frame_count']
        packs = []
        for event in sorted(items, key=lambda e: (e['start_frame'], e['end_frame_exclusive'], e['hand'])):
            if packs and len(packs[-1]) < 6 and (max(event['end_frame_exclusive'], max(e['end_frame_exclusive'] for e in packs[-1])) - packs[-1][0]['start_frame']) / fps <= 120 and (event['start_frame'] - max(e['end_frame_exclusive'] for e in packs[-1])) / fps <= 25:
                packs[-1].append(event)
            else:
                packs.append([event])
        for pack in packs:
            a = max(0, min(e['start_frame'] for e in pack) - round(15 * fps))
            b = min(total, max(e['end_frame_exclusive'] for e in pack) + round(15 * fps))
            desired = min(total, round(45 * fps))
            if b - a < desired:
                a = max(0, a - (desired - (b - a)) // 2)
                b = min(total, max(b, a + desired))
                a = max(0, min(a, b - desired))
            group_id = 'fg_' + fingerprint([trial_id, [e['event_id'] for e in pack], a, b])[:20]
            context = [dict(start_s=round(x['start_frame'] / fps, 3), end_s=round(x['end_frame_exclusive'] / fps, 3), hand=x['hand'], action=x['action']) for x in trial['actions'] if x['start_frame'] < b and x['end_frame_exclusive'] > a]
            step_path = ROOT / 'annotations/impact/IMPACT-v1.1/annotations/TAS-S/front' / (trial['video_id'] + '.json')
            steps = [dict(start_s=round(x['f_start'] / fps, 3), end_s=round((x['f_end'] + 1) / fps, 3), action=x['label']) for x in read_json(step_path)['segments'] if x['f_start'] < b and x['f_end'] + 1 > a]
            groups.append(dict(group_id=group_id, trial_id=trial_id, view='front', model=trial_id.split('_')[-2],
                               workflow='assemble' if '_Reassembly_' in trial_id else 'disassemble',
                               fps=fps, source_video=trial['source_video'], frame_count=total,
                               start_frame=a, end_frame_exclusive=b, duration_s=(b-a)/fps,
                               events=pack, action_context=context, step_context=steps))
    groups = balanced_order(groups)
    selection = dict(events=len(events), groups=len(groups), GT_events=sum(e['origin']=='GT_anomaly' for e in events),
                     proxy_events=sum(e['origin']!='GT_anomaly' for e in events), videos=len(by_trial),
                     event_duration_bins=dict(Counter(duration_bin(e['duration_s']) for e in events)),
                     GT_duration_bins=dict(Counter(duration_bin(e['duration_s']) for e in events if e['origin']=='GT_anomaly')),
                     candidate_type_counts=dict(Counter(t for e in events for t in e['proposed_categories'])),
                     GT_type_counts={t:sum(bool(e['labels'][i]) for e in events) for i,t in enumerate(TYPES)},
                     playback_duration_quantiles={str(q):float(np.quantile([g['duration_s'] for g in groups],q)) for q in [0,.25,.5,.75,.9,1]},
                     event_max_duration_s=max(e['duration_s'] for e in events), sampling='all native GT anomaly runs plus prespecified proxy hits; no length exclusion',
                     order='duration-bin round robin, hashed within bin; no shortest-first', formal_release=False)
    version = fingerprint(groups)
    frozen_path = FOLDER / 'selection_frozen.json'
    if frozen_path.exists() and read_json(frozen_path)['fingerprint'] != version:
        raise ValueError('front_expansion:selection_changed')
    if selection['GT_events'] != 1809 or len({e['event_id'] for e in events}) != len(events):
        raise ValueError('front_expansion:population_or_duplicate')
    save_jsonl(FOLDER / 'groups.jsonl', groups)
    save_jsonl(FOLDER / 'events.jsonl', events)
    save_jsonl(FOLDER / 'first10_groups.jsonl', groups[:10])
    save_jsonl(FOLDER / 'first10_events.jsonl', events[:10])
    save_json(FOLDER / 'selection.json', selection)
    save_json(FOLDER / 'selection_frozen.json', dict(fingerprint=version, **selection))
    save_json(FOLDER / 'options.json', OPTIONS)
    return groups


def export(groups):
    questions, statuses = [], Counter()
    for group in groups:
        path = FOLDER / 'results' / (group['group_id'] + '.json')
        result = read_json(path) if path.exists() else {'status':'queued'}
        statuses[result['status']] += 1
        by_event = {item['event_id']:item for item in result.get('items', [])}
        frame_map = {f['frame_id']:f for f in result.get('media', {}).get('sampled_frames', [])}
        for event in group['events']:
            a, b = event['start_frame'] / group['fps'], event['end_frame_exclusive'] / group['fps']
            local = [a - group['start_frame'] / group['fps'], b - group['start_frame'] / group['fps']]
            visual = by_event.get(event['event_id'])
            supported = [c['category'] for c in visual['checks'] if c['verdict']=='supported'] if visual else []
            contradicted = [c['category'] for c in visual['checks'] if c['verdict']=='contradicted'] if visual else []
            status = 'visual_supported_pending_human' if supported else 'visual_conflict_pending_human' if contradicted else 'visual_uncertain_pending_human' if visual else 'visual_pending' if result['status']!='error' else 'visual_error_pending_retry'
            evidence=[]
            if visual:
                for check in visual['checks']:
                    evidence.append(dict(check, frames=[dict(frame_id=fid,source_s=frame_map[fid]['source_pts_s'],playback_s=frame_map[fid]['source_pts_s']-group['start_frame']/group['fps']) for fid in check['evidence_frame_ids']]))
            questions.append(dict(question_id=event['event_id'], group_id=group['group_id'], trial_id=group['trial_id'],
                                  view='front', kind='mcq_anomaly_front_review',
                                  question=f"During {local[0]:.2f}–{local[1]:.2f} seconds of this video, does the person's {event['hand']} hand perform an anomalous operation? Select all applicable anomaly types, or Correct if none applies.",
                                  question_zh=f"播放视频的{local[0]:.2f}–{local[1]:.2f}秒，操作者的{'左' if event['hand']=='left' else '右'}手操作是否存在异常？如有，选择所有适用异常类型；如无，选择Correct。",
                                  options=OPTIONS, GT_option_ids=event['gt_option_ids'], candidate_option_ids=event['candidate_option_ids'],
                                  model_supported_option_ids=[chr(66+TYPES.index(t)) for t in supported],
                                  final_option_ids=None, answer_status='candidate_only_human_decision_required',
                                  GT_phase=event['phase'], origin=event['origin'], rule_ids=event['rule_ids'],
                                  scope=dict(hand=event['hand'],source_interval_s=[a,b],playback_interval_s=local,target_duration_s=b-a,
                                             playback_source_interval_s=[group['start_frame']/group['fps'],group['end_frame_exclusive']/group['fps']]),
                                  visual_review=visual,visual_evidence=evidence, automatic_status=status,
                                  source_actions=event['actions'],atr_sources=event['atr_sources'],
                                  human_review='unreviewed',formal_release=False))
    target = FOLDER / 'questions.jsonl'
    temporary = target.with_suffix('.pending.jsonl')
    save_jsonl(temporary, questions)
    temporary.replace(target)
    progress = dict(total_groups=len(groups),group_status=dict(statuses),questions=len(questions),
                    visual_completed_questions=sum(q['visual_review'] is not None for q in questions),
                    question_status=dict(Counter(q['automatic_status'] for q in questions)),
                    candidate_type_counts=dict(Counter(OPTIONS[ord(k)-65]['name'] for q in questions for k in q['candidate_option_ids'])),
                    model_supported_type_counts=dict(Counter(OPTIONS[ord(k)-65]['name'] for q in questions for k in q['model_supported_option_ids'])),
                    formal_release=False)
    save_json(FOLDER / 'progress.json', progress)
    save_jsonl(FOLDER / 'first10_questions.jsonl', questions[:10])
    return progress
