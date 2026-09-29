import argparse
import asyncio
from collections import Counter, defaultdict
import fcntl
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.mcq_grouped import build_units, make_windows, normal_controls, option_ids, question_record, save_preparation, select_pilot
from impact_qa.mcq_grouped_media import prepare_window_media
from impact_qa.mcq_grouped_review import adjudication_schema, assess_event, check_ids, observation_schema
from impact_qa.structured_video_client import StructuredVideoPool


async def run(args, config, folder, units, trials):
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('mcq_grouped_preflight:cuda_unavailable')
    run_folder = folder / args.round
    excluded = read_json(folder / args.exclude_round / 'selection.json')['unit_ids'] if args.exclude_round else []
    selected = select_pilot(units, args.limit, excluded) + normal_controls(trials, args.controls)
    save_json(run_folder / 'selection.json', {'unit_ids': [u['unit_id'] for u in selected], 'config': config, 'torch': torch.__version__, 'cuda': torch.version.cuda, 'gpus': torch.cuda.device_count()})
    prompt_dir = ROOT / 'prompts/impact_qa/mcq_grouped_v1'
    observation_prompt = (prompt_dir / (args.prompt_version + '_observe.txt' if args.prompt_version != 'r1' else 'observe.txt')).read_text()
    review_prompt = (prompt_dir / (args.prompt_version + '_adjudicate.txt' if args.prompt_version != 'r1' else 'adjudicate.txt')).read_text()
    options = read_json(ROOT / config['parent_root'] / 'mcq_options.json')
    if isinstance(options, dict):
        options = options.get('options', options)
    pool = StructuredVideoPool(config, run_folder)
    semaphore = asyncio.Semaphore(config['workers'])
    version = fingerprint([config, observation_prompt, review_prompt, {p: (ROOT/p).read_text() for p in ['impact_qa/mcq_grouped.py', 'impact_qa/mcq_grouped_media.py', 'impact_qa/mcq_grouped_review.py', 'scripts/run_mcq_grouped_v1.py']}])
    save_json(run_folder / 'frozen.json', {'version': version, 'observation_prompt': observation_prompt, 'review_prompt': review_prompt})
    for name in ['impact_qa/mcq_grouped.py','impact_qa/mcq_grouped_media.py','impact_qa/mcq_grouped_review.py','scripts/run_mcq_grouped_v1.py']:
        target=run_folder/'source_snapshot'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)

    async def process(unit):
        path = run_folder / 'results' / (unit['unit_id'] + '.json')
        if path.exists():
            cached = read_json(path)
            if cached.get('version') == version and cached['status'] == 'ok':
                return cached
        async with semaphore:
            record = {'unit_id': unit['unit_id'], 'version': version, 'status': 'error', 'packaging': unit['packaging'], 'scope': unit['scope'], 'windows': []}
            try:
                reviews = defaultdict(list)
                for window in make_windows(unit, config):
                    media = await asyncio.to_thread(prepare_window_media, unit, window, config, folder)
                    targets = [{'event_id': e['event_id'], 'hand': e['hand'], 'parent_clip_interval_s': [(e[k]-unit['clip']['start_frame'])/unit['clip']['fps'] for k in ['start_frame','end_frame_exclusive']], 'in_interval_frame_ids': [f['frame_id'] for f in media['sampled_frames'] if e['start_frame'] <= f['source_frame_index'] < e['end_frame_exclusive']]} for e in window['events']]
                    payload = {'case_id': unit['unit_id'] + '_' + window['window_id'], 'workflow': unit['clip']['workflow'], 'video_sampling': media['sampled_frames'], 'hand_intervals': targets, 'spatial_view': 'Enlarged work area; upper-right inset shows the same original frame, not another camera or time.' if media.get('detail_crop') else 'Original full frame.'}
                    observed = await pool.call('grouped_observe', observation_prompt, payload, observation_schema(window['events'], media), config['generation_tokens'], video=media, validator=lambda r: check_ids(r, window['events']))
                    observation_by_id = {r['event_id']: r for r in observed['result']['items']}
                    if unit['packaging'] != 'control' or config.get('contextual_review'):
                        review_events = window['events'] if unit['packaging'] != 'control' else [dict(e, labels=[1,0,1,0,0,0]) for e in window['events']]
                        adjudication_payload = dict(payload, prior_observation=observed['result'], gt_targets=[{'event_id': e['event_id'], 'labels': [o for o in options if o['id'] in option_ids([e])], 'annotated_action_names': e.get('action_names', []), 'type_subintervals_in_source_frames': e.get('type_intervals',{})} for e in review_events])
                        if config.get('contextual_review'):
                            trial = trials[unit['clip']['video_id']]
                            model = 'B' if '_B_' in trial['video_id'] else 'A'
                            reference_path = ROOT / 'prompts/impact_qa' / ('v28r_object_knowledge_' + model + '.txt')
                            action_context = [{'source_ids': e['source_ids'], 'hand': e['hand'], 'action': e['action'], 'interval_s': [(e[k]-unit['clip']['start_frame'])/trial['fps'] for k in ['start_frame','end_frame_exclusive']]} for e in trial['events'] if e['start_frame'] < window['end_frame_exclusive'] and e['end_frame_exclusive'] > window['start_frame'] and e['action'] != 'null']
                            adjudication_payload.update(domain_reference=reference_path.read_text(), domain_reference_path=str(reference_path.relative_to(ROOT)), annotated_actions=action_context, annotation_is_not_visual_proof=True)
                        adjudicated = await pool.call('grouped_adjudicate', review_prompt, adjudication_payload, adjudication_schema(review_events, media, config.get('contextual_review'), config.get('grounding_review')), config['generation_tokens'], video=media, validator=lambda r: check_ids(r, review_events))
                        for row in adjudicated['result']['items']:
                            event = next(e for e in review_events if e['event_id'] == row['event_id'])
                            reviews[row['event_id']].append(assess_event(event, observation_by_id[row['event_id']], row, media, config))
                    else:
                        adjudicated = None
                    record['windows'].append({'window': window, 'media': media, 'observation': observed['result'], 'adjudication': adjudicated['result'] if adjudicated else None})
                if unit['packaging'] == 'control':
                    record['false_positive'] = any(r['abnormality'] == 'visible' for w in record['windows'] for r in w['observation']['items'])
                    record['injected_labels_for_audit_only'] = ['B','D'] if config.get('contextual_review') else []
                    record['label_anchoring_false_positive'] = any(row['verdict'] == 'supported' for w in record['windows'] if w['adjudication'] for item in w['adjudication']['items'] for row in item['labels'])
                    record['question'] = None
                else:
                    selected_reviews = {eid: next((r for r in values if r['accepted']), next((r for r in values if r.get('annotation_backed_eligible')),values[0])) for eid, values in reviews.items()}
                    record['event_reviews'] = selected_reviews
                    record['question'], record['held'] = question_record(unit, selected_reviews, options)
                    if config.get('grounding_review'):
                        candidate,_=question_record(unit,selected_reviews,options,'annotation_backed_eligible')
                        if candidate:
                            candidate.update(answer_basis='ATR_GT',verification_tier='action_grounded_GT_candidate',visual_type_verification='confirmed' if record['question'] else 'unconfirmed',status='needs_review')
                        record['annotation_backed_candidate']=candidate
                record['status'] = 'ok'
            except Exception as exc:
                record['error'] = f'{type(exc).__name__}:{exc}'
            save_json(path, record)
            print(json.dumps({k: record.get(k) for k in ['unit_id','status','packaging','error']}), flush=True)
            return record
    try:
        records = await asyncio.gather(*(process(u) for u in selected))
    finally:
        await pool.close()
    questions = [r['question'] for r in records if r.get('question')]
    held = [r['held'] for r in records if r.get('held')]
    save_jsonl(run_folder / 'questions.jsonl', questions)
    save_jsonl(run_folder / 'held.jsonl', held)
    save_jsonl(run_folder / 'annotation_backed_candidates.jsonl', [r['annotation_backed_candidate'] for r in records if r.get('annotation_backed_candidate')])
    save_jsonl(run_folder / 'first10_outputs.jsonl', questions[:10])
    save_jsonl(run_folder / 'api_calls.jsonl', pool.calls)
    reviews = [v for r in records for v in r.get('event_reviews', {}).values()]
    summary = {'selected': len(selected), 'anomaly_units': sum(u['packaging'] != 'control' for u in selected), 'controls': sum(u['packaging'] == 'control' for u in selected), 'completed': sum(r['status'] == 'ok' for r in records), 'errors': [r for r in records if r['status'] != 'ok'], 'automatically_retained_mcq': len(questions), 'held_units': len(held), 'events_checked': len(reviews), 'events_supported': sum(v['accepted'] for v in reviews), 'hold_reasons': dict(Counter(x for v in reviews for x in v['hold_reasons'])), 'control_false_positives': sum(r.get('false_positive', False) for r in records), 'new_api_calls': len(pool.calls), 'formal_release': False, 'human_review': 'unreviewed'}
    summary['label_anchoring_false_positives'] = sum(r.get('label_anchoring_false_positive',False) for r in records)
    summary['action_grounded_GT_candidates'] = sum(bool(r.get('annotation_backed_candidate')) for r in records)
    save_json(run_folder / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--limit', type=int, default=12)
    parser.add_argument('--controls', type=int, default=4)
    parser.add_argument('--round', default='r1')
    parser.add_argument('--prompt-version', default='r1')
    parser.add_argument('--exclude-round')
    args = parser.parse_args()
    config = read_json(ROOT / 'configs/impact_qa/mcq_grouped_v1.json')
    if args.prompt_version != 'r1':
        config.update(contextual_review=True, require_blind_abnormality=False)
    if args.prompt_version == 'r3':
        config.update(grounding_review=True, per_type_evidence=True, sample_fps=4, window_seconds=20, detail_crop=[0.2,0.3,0.8,0.95],target_overlay=True)
    folder = ROOT / config['output_root']
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        units, parents, trials, report = build_units(ROOT / config['parent_root'], config)
        save_preparation(folder, units, parents, report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        print(json.dumps([{'unit_id': u['unit_id'], 'scope': u['scope'], 'labels': u['correct_option_ids']} for u in units[:10]]), flush=True)
        if not args.prepare_only:
            asyncio.run(run(args, config, folder, units, trials))


if __name__ == '__main__':
    main()
