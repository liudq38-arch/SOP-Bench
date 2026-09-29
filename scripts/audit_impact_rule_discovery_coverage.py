from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import ANNOTATIONS, read_json, save_json, save_jsonl
from impact_qa.mcq_native import native_trial, stable_runs


NAMES = ['temporal', 'spatial', 'handling', 'wrong_part', 'wrong_tool', 'procedural']


def duration_bin(value):
    if value < 1.5:
        return 'lt1.5s'
    if value < 5:
        return '1.5_to_lt5s'
    return 'ge5s'


def main():
    folder = ROOT / 'reports/impact_qa/anomaly_taxonomy_audit'
    paths = sorted((ANNOTATIONS / 'TAS-B/front').glob('*.json'))
    assert len(paths) == 112, 'rule_coverage:unexpected_trial_count'
    print({'preflight': 'CPU annotation coverage only', 'front_files': len(paths), 'model_requests': 0}, flush=True)
    normal_index = defaultdict(list)
    atomic = defaultdict(list)
    runs = []
    for path in paths:
        trial_id = path.stem.removesuffix('_front')
        trial = native_trial(trial_id, 'front')
        participant, operation, model, _ = trial_id.split('_')
        for action in trial['actions']:
            for category, flag in zip(NAMES, action['labels']):
                if flag:
                    atomic[category].append(action | {'duration_s': (action['end_frame_exclusive'] - action['start_frame']) / trial['fps']})
            if action['phase'] == 'normal' and not any(action['labels']) and action['action'] != 'null':
                key = (model, operation, action['hand'], action['action'])
                normal_index[key].append({'trial_id': trial_id, 'participant': participant, 'source': action['source'], 'start_frame': action['start_frame'], 'end_frame_exclusive': action['end_frame_exclusive'], 'action': action['action']})
        for run in stable_runs(trial):
            if any(run['labels']):
                runs.append(run | {'trial_id': trial_id, 'participant': participant, 'model_filename_cue': model, 'operation': operation, 'fps': trial['fps']})
    summaries = []
    candidates = []
    for run in runs:
        comparable = {}
        for action in run['action_names']:
            key = (run['model_filename_cue'], run['operation'], run['hand'], action)
            matches = normal_index.get(key, [])
            different = [m for m in matches if m['participant'] != run['participant']]
            same_trial = [m for m in matches if m['trial_id'] == run['trial_id']]
            comparable[action] = {'same_model_operation_hand_normal_segments': len(matches), 'same_trial_segments': len(same_trial), 'different_participant_segments': len(different), 'example_same_trial': same_trial[:1], 'example_different_participant': different[:1]}
        candidates.append({
            'run_id': run['run_id'],
            'trial_id': run['trial_id'],
            'participant': run['participant'],
            'view': 'front',
            'model_filename_cue': run['model_filename_cue'],
            'operation': run['operation'],
            'hand': run['hand'],
            'start_frame': run['start_frame'],
            'end_frame_exclusive': run['end_frame_exclusive'],
            'fps': run['fps'],
            'duration_s': run['duration_s'],
            'labels': [name for name, flag in zip(NAMES, run['labels']) if flag],
            'action_names': run['action_names'],
            'atomic_action_sources': [a['source'] for a in run['actions']],
            'normal_comparison_availability': comparable,
            'matching_is_not_semantic_equivalence': True,
            'reason_status': 'unreviewed',
        })
    for name in NAMES:
        selected = [r for r in candidates if name in r['labels']]
        single = [r for r in selected if len(r['labels']) == 1 and r['action_names']]
        atom = atomic[name]
        single_atom = [a for a in atom if sum(a['labels']) == 1 and a['action'] != 'null']
        summaries.append({
            'category': name,
            'atomic_count': len(atom),
            'atomic_single_named_count': len(single_atom),
            'atomic_single_named_ge5s': sum(a['duration_s'] >= 5 for a in single_atom),
            'stable_run_count': len(selected),
            'stable_duration_bins': dict(Counter(duration_bin(r['duration_s']) for r in selected)),
            'single_named_stable_count': len(single),
            'single_named_stable_duration_bins': dict(Counter(duration_bin(r['duration_s']) for r in single)),
            'trials': len({r['trial_id'] for r in selected}),
            'participants': len({r['participant'] for r in selected}),
            'model_filename_cues': dict(Counter(r['model_filename_cue'] for r in selected)),
            'operations': dict(Counter(r['operation'] for r in selected)),
            'named_runs_with_any_same_trial_normal_comparison': sum(any(v['same_trial_segments'] for v in r['normal_comparison_availability'].values()) for r in selected),
            'named_runs_with_any_other_participant_normal_comparison': sum(any(v['different_participant_segments'] for v in r['normal_comparison_availability'].values()) for r in selected),
        })
    previous = read_json(folder / 'annotation_audit.json')
    for row, known in zip(summaries, previous['classes']):
        assert row['atomic_count'] == known['front_TASB_action_segments'], f'rule_coverage:count_mismatch:{row["category"]}'
    assert len({r['run_id'] for r in candidates}) == len(candidates), 'rule_coverage:duplicate_runs'
    report = {
        'date': '2026-09-28',
        'view': 'front',
        'front_trials': len(paths),
        'unique_stable_anomaly_runs': len(candidates),
        'unit_note': 'Same-hand adjacent TAS-B segments with identical phase and anomaly labels; no duration filtering. Counts across categories overlap. Normal matches only screen metadata, not causal equivalence.',
        'classes': summaries,
        'validation': 'atomic count crosscheck and unique run IDs passed',
    }
    save_json(folder / 'followup_coverage.json', report)
    save_jsonl(folder / 'rule_discovery_pool.jsonl', candidates)
    save_jsonl(folder / 'rule_discovery_pool_first10.jsonl', candidates[:10])
    for row in summaries:
        print(row, flush=True)
    print({'unique_stable_runs': len(candidates), 'validation': 'passed'}, flush=True)


if __name__ == '__main__':
    main()
