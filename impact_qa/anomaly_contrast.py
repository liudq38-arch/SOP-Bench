from collections import Counter, defaultdict
from pathlib import Path

from impact_qa.common import ANNOTATIONS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_native import native_trial


HELD_PARTICIPANTS = ('KJ03JM25', 'LE07UF17')
CATEGORIES = ('wrong_tool', 'spatial')
FOLDER = ROOT / 'outputs/impact_qa/anomaly_contrast_v1'


def context(trial, a, b, radius=10):
    start = max(0, a - round(radius * trial['fps']))
    end = min(trial['frame_count'], b + round(radius * trial['fps']))
    return [x for x in trial['actions'] if x['start_frame'] < end and x['end_frame_exclusive'] > start]


def action_family(row):
    names = row['action_names']
    if any('screwdriver' in name for name in names):
        return next(name.split('_screwdriver')[0].split('_')[-1] + '_screwdriver' for name in names if 'screwdriver' in name)
    if any('wrench' in name for name in names):
        return 'wrench'
    if any('screw' in name for name in names):
        return 'screw'
    if any('nut' in name for name in names):
        return 'nut'
    if any('shaft' in name for name in names):
        return 'shaft'
    return names[0] if names else 'null'


def choose(rows, number):
    pool = sorted(rows, key=lambda r: r['run_id'])
    chosen = []
    trials, people, families, models, operations, lengths = [Counter() for _ in range(6)]
    while pool and len(chosen) < number:
        def score(r):
            duration = 'short' if r['duration_s'] < 1.5 else 'medium' if r['duration_s'] < 5 else 'long'
            return (trials[r['trial_id']], people[r['participant']], len(r['labels']) != 1, families[action_family(r)], models[r['model_filename_cue']], operations[r['operation']], lengths[duration], -min(r['duration_s'], 10), r['run_id'])
        selected = min(pool, key=score)
        pool.remove(selected)
        chosen.append(selected)
        trials[selected['trial_id']] += 1
        people[selected['participant']] += 1
        families[action_family(selected)] += 1
        models[selected['model_filename_cue']] += 1
        operations[selected['operation']] += 1
        lengths['short' if selected['duration_s'] < 1.5 else 'medium' if selected['duration_s'] < 5 else 'long'] += 1
    return chosen


def normal_index():
    result = defaultdict(list)
    for path in sorted((ANNOTATIONS / 'TAS-B/front').glob('*.json')):
        trial_id = path.stem.removesuffix('_front')
        person, operation, model, _ = trial_id.split('_')
        trial = native_trial(trial_id, 'front')
        for action in trial['actions']:
            if action['phase'] == 'normal' and not any(action['labels']) and action['action'] != 'null':
                result[(model, operation, action['hand'], action['action'])].append(dict(action, trial_id=trial_id, participant=person, fps=trial['fps']))
    return result


def make_case(row, split, category, role, pair_id):
    trial = native_trial(row['trial_id'], 'front')
    a, b = row['start_frame'], row['end_frame_exclusive']
    case_id = 'ac_' + fingerprint([row['trial_id'], row['hand'], a, b, role, pair_id])[:16]
    target = [x for x in trial['actions'] if x['hand'] == row['hand'] and x['start_frame'] < b and x['end_frame_exclusive'] > a]
    labels = [int(any(x['labels'][j] for x in target)) for j in range(6)]
    if role == 'normal' and (any(labels) or any(x['phase'] != 'normal' for x in target)):
        raise ValueError('anomaly_contrast:normal_GT_conflict:' + case_id)
    return {
        'case_id': case_id,
        'pair_id': pair_id,
        'split': split,
        'research_category': category,
        'role': role,
        'participant': row['trial_id'].split('_')[0],
        'trial_id': row['trial_id'],
        'target_hand': row['hand'],
        'start_frame': a,
        'end_frame_exclusive': b,
        'gt_labels': labels,
        'target_actions': target,
        'context_actions': context(trial, a, b),
        'duration_s': (b - a) / trial['fps'],
        'clip': {'clip_id': case_id, 'source_video': trial['source_video'], 'start_frame': 0, 'fps': trial['fps'], 'video_id': trial['video_id'], 'view': 'front', 'frame_count': trial['frame_count']},
        'human_review': 'unreviewed',
        'reason_status': 'unreviewed',
        'formal_release': False,
    }


def prepare():
    plan_path = FOLDER / 'selection_frozen.json'
    if plan_path.exists():
        return read_jsonl(FOLDER / 'cases.jsonl')
    pool = read_jsonl(ROOT / 'reports/impact_qa/anomaly_taxonomy_audit/rule_discovery_pool.jsonl')
    normal = normal_index()
    cases, pairs = [], []
    reused = Counter()
    for split in ['discovery', 'validation']:
        for category in CATEGORIES:
            candidates = [r for r in pool if category in r['labels'] and r['action_names'] and (r['participant'] in HELD_PARTICIPANTS) == (split == 'validation')]
            target_count = 12 if split == 'discovery' or category == 'spatial' else 10
            selected = choose(candidates, target_count)
            for row in selected:
                pair_id = 'pair_' + fingerprint([split, category, row['run_id']])[:12]
                case = make_case(row, split, category, 'anomaly', pair_id)
                cases.append(case)
                matches = []
                for action in row['action_names']:
                    key = (row['model_filename_cue'], row['operation'], row['hand'], action)
                    matches.extend(r for r in normal.get(key, []) if (r['participant'] in HELD_PARTICIPANTS) == (split == 'validation'))
                def match_score(r):
                    same = r['trial_id'] == row['trial_id']
                    distance = abs(r['start_frame'] - row['start_frame']) / r['fps'] if same else 1e6
                    identity = (r['trial_id'], r['source']['pointer'])
                    return (not same, reused[identity], distance, abs((r['end_frame_exclusive'] - r['start_frame']) / r['fps'] - row['duration_s']), r['trial_id'], r['start_frame'])
                match = min(matches, key=match_score) if matches else None
                normal_case = None
                if match:
                    reused[(match['trial_id'], match['source']['pointer'])] += 1
                    normal_case = make_case(match, split, category, 'normal', pair_id)
                    cases.append(normal_case)
                pairs.append({'pair_id': pair_id, 'split': split, 'category': category, 'anomaly_case': case['case_id'], 'normal_case': normal_case['case_id'] if normal_case else None, 'match_basis': 'same_filename_model_workflow_hand_action', 'same_trial': bool(match and match['trial_id'] == row['trial_id']), 'semantic_comparability': 'requires_video_and_component_state_review'})
    assert all((r['participant'] in HELD_PARTICIPANTS) == (r['split'] == 'validation') for r in cases), 'anomaly_contrast:participant_leakage'
    assert len({r['case_id'] for r in cases}) == len(cases), 'anomaly_contrast:duplicate_IDs'
    source_paths = {a['source']['path'] for r in cases for a in r['target_actions']}
    assert all((ROOT / p).exists() for p in source_paths), 'anomaly_contrast:missing_annotation'
    assert all(Path(r['clip']['source_video']).exists() for r in cases), 'anomaly_contrast:missing_media'
    summary = {'held_participants': list(HELD_PARTICIPANTS), 'split_case_counts': dict(Counter(r['split'] for r in cases)), 'pair_counts': dict(Counter(r['split'] + ':' + r['category'] for r in pairs)), 'missing_normal_comparison': sum(p['normal_case'] is None for p in pairs), 'same_trial_comparison': sum(p['same_trial'] for p in pairs), 'cases_fingerprint': fingerprint(cases), 'prior_global_QA_exposure': True, 'not_official_train_test_split': True}
    FOLDER.mkdir(parents=True, exist_ok=True)
    save_jsonl(FOLDER / 'cases.jsonl', cases)
    save_jsonl(FOLDER / 'pairs.jsonl', pairs)
    save_jsonl(FOLDER / 'first10_cases.jsonl', cases[:10])
    save_json(plan_path, summary)
    return cases
