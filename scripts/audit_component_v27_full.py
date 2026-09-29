import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text())


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def normalized(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9.]+', ' ', str(value).lower())).strip()


def contains(text, phrase):
    target = normalized(phrase)
    return bool(target) and target in normalized(text)


def duration_stats(rows):
    values = sorted(float(row['duration_s']) for row in rows)
    return {
        'count': len(values),
        'min_s': values[0] if values else None,
        'median_s': statistics.median(values) if values else None,
        'mean_s': sum(values) / len(values) if values else None,
        'max_s': values[-1] if values else None,
        'below_3s': sum(value < 3 for value in values),
        'below_5s': sum(value < 5 for value in values),
    }


def question_contract_issues(question, plan):
    issues = []
    kind = question.get('kind')
    answer = question.get('answer', '')
    text = question.get('question', '')
    facts = {fact['fact_id']: fact for fact in plan.get('reference_facts', [])} if plan else {}
    if plan and set(question.get('source_fact_ids', [])) != set(facts):
        issues.append('source_fact_coverage')
    if kind == 'detailed_operation':
        for fact in facts.values():
            for term in fact.get('required_phrases', []):
                if not contains(answer, term):
                    issues.append('detailed_missing:' + term)
        if len(re.findall(r"\b[\w'-]+\b", answer)) > 95:
            issues.append('detailed_too_long')
    elif kind == 'step_completion':
        fact = next(iter(facts.values()), {})
        expected = str(fact.get('verdict', ''))
        if expected and not re.match(r'^\s*' + re.escape(expected) + r'\b', answer, re.I):
            issues.append('completion_polarity')
        target = fact.get('queried_component')
        if target and not contains(text, target):
            issues.append('completion_target_missing_from_question')
        if expected == 'no':
            for target in fact.get('completed_components', []):
                if not contains(answer, target):
                    issues.append('negative_completion_missing:' + target)
    elif kind == 'observed_order':
        pair = next(iter(facts.values()), {}).get('order_pair', {})
        before = pair.get('before', {}).get('target')
        after = pair.get('after', {}).get('target')
        if before and after:
            if not contains(text, before) or not contains(text, after):
                issues.append('order_target_missing_from_question')
            if normalized(answer).find(normalized(before)) >= normalized(answer).find(normalized(after)):
                issues.append('order_relation')
    elif kind == 'operation_duration':
        fact = next(iter(facts.values()), {})
        numeric = fact.get('numeric', {})
        target = fact.get('operation_window', {}).get('target')
        if target and not contains(answer, target):
            issues.append('duration_target_missing')
        if numeric.get('mode') == 'duration' and numeric.get('display') not in answer:
            issues.append('duration_value_missing')
        if numeric.get('mode') == 'start_end':
            for field in ['display_start', 'display_end']:
                if numeric.get(field) not in answer:
                    issues.append('duration_bound_missing:' + field)
    elif kind == 'overall_operation':
        operation = next(iter(facts.values()), {}).get('operation')
        if operation == 'assembly' and not re.search(r'\b(assemble|assembly|assembling|assembled)\b', answer, re.I):
            issues.append('overall_operation_missing')
        if operation == 'disassembly' and not re.search(r'\b(disassemble|disassembly|dismantle|dismantling|dismantled)\b', answer, re.I):
            issues.append('overall_operation_missing')
    return issues


def run(config_path):
    config = read_json(ROOT / config_path)
    folder = ROOT / config['output_root']
    manifest = read_jsonl(folder / 'manifest.jsonl')
    clips = read_jsonl(folder / 'clips.jsonl')
    raw = read_jsonl(folder / 'raw_clips.jsonl')
    questions = read_jsonl(folder / 'questions.jsonl')
    reviews = read_jsonl(folder / 'reviews.jsonl')
    fixed_mcq = read_jsonl(folder / 'fixed_mcq.jsonl')
    progress = read_json(folder / 'progress.json')
    reuse_manifest_path = folder / 'reuse_manifest.json'
    reuse_manifest = read_json(reuse_manifest_path) if reuse_manifest_path.exists() else None
    results = [read_json(path) for path in (folder / 'results').glob('*_V.json')]
    result_by_clip = {row.get('clip_id'): row for row in results}
    manifest_by_clip = {row['clip_id']: row for row in manifest}
    plan_by_id = {}
    for path in (folder / 'plans').glob('*.json'):
        for row in read_json(path).get('open_qa_candidates', []):
            plan_by_id[row['candidate_id']] = row
    frame_ids_by_clip = {}
    missing_media = []
    for path in (folder / 'inputs').glob('*.json'):
        value = read_json(path)
        clip_id = value.get('clip', {}).get('clip_id')
        frame_ids_by_clip[clip_id] = {row['frame_id'] for row in value.get('media', {}).get('sampled_frames', [])}
        media_path = value.get('media', {}).get('path')
        if media_path and not Path(media_path).exists():
            missing_media.append({'clip_id': clip_id, 'path': media_path})
    issues = []
    if progress.get('state') != 'full_finished':
        issues.append('progress_not_full_finished')
    if progress.get('pending_clip_count') != 0:
        issues.append('pending_clips')
    if progress.get('preparation_error_count') != 0:
        issues.append('preparation_errors')
    if len(manifest) != len(result_by_clip):
        issues.append('manifest_result_count')
    if set(manifest_by_clip) != set(result_by_clip):
        issues.append('manifest_result_clip_ids')
    duplicate_question_ids = len(questions) - len({row.get('question_id') for row in questions})
    if duplicate_question_ids:
        issues.append('duplicate_question_ids')
    unknown_clip_questions = [row.get('question_id') for row in questions if row.get('clip_id') not in manifest_by_clip]
    unknown_evidence = []
    contract = []
    status_mismatch = []
    for row in questions:
        clip_id = row.get('clip_id')
        allowed = frame_ids_by_clip.get(clip_id, set())
        for frame_id in row.get('evidence_frame_ids', []):
            if frame_id not in allowed:
                unknown_evidence.append({'question_id': row.get('question_id'), 'frame_id': frame_id})
        plan = plan_by_id.get(row.get('question_id'))
        current = question_contract_issues(row, plan)
        if current:
            contract.append({'question_id': row.get('question_id'), 'issues': current})
        review = row.get('automatic_review', {})
        expected_status = 'candidate' if review.get('verdict') == 'keep' and row.get('visual_support') != 'conflicts_with_gt' else 'held'
        if row.get('status') != expected_status:
            status_mismatch.append({'question_id': row.get('question_id'), 'status': row.get('status'), 'expected': expected_status})
    if unknown_clip_questions:
        issues.append('unknown_question_clip')
    if unknown_evidence:
        issues.append('unknown_evidence_frame')
    if status_mismatch:
        issues.append('question_status_mismatch')
    run_files = sorted((folder / 'runs').glob('*.json'), key=lambda path: path.stat().st_mtime)
    run_requests = []
    for path in run_files:
        run_requests.extend(read_json(path).get('requests', []))
    latest_requests = read_json(run_files[-1]).get('requests', []) if run_files else []
    request_stats = lambda rows: dict(Counter(row.get('status') for row in rows))
    current_request_stats = {'ok': 0, 'error': 0} if reuse_manifest else request_stats(latest_requests)
    report = {
        'version': config.get('version'),
        'output_root': config.get('output_root'),
        'progress': progress,
        'counts': {
            'raw_clips': len(raw),
            'repaired_clips': len(clips),
            'manifest_clips': len(manifest),
            'result_files': len(results),
            'inputs': len(frame_ids_by_clip),
            'questions': len(questions),
            'reviews': len(reviews),
            'fixed_mcq_candidates': len(fixed_mcq),
        },
        'clip_duration': {
            'raw': duration_stats(raw),
            'repaired': duration_stats(clips),
            'manifest': duration_stats(manifest),
        },
        'question_kinds': dict(Counter(row.get('kind') for row in questions)),
        'question_status': dict(Counter(row.get('status') for row in questions)),
        'human_review': dict(Counter(row.get('human_review') for row in questions)),
        'automatic_review': dict(Counter(row.get('automatic_review', {}).get('verdict') for row in questions)),
        'visual_support': dict(Counter(row.get('visual_support') for row in questions)),
        'held_kinds': dict(Counter(row.get('kind') for row in questions if row.get('status') == 'held')),
        'mcq': {
            'fixed_candidates': len(fixed_mcq),
            'exported': sum(row.get('kind') == 'mcq_anomaly_clip' for row in questions),
            'visual_selected_but_rejected': sum(
                any(item.endswith('_mcq_clip_anomaly') for item in row.get('selected_question_ids', []))
                and any(entry.get('reason') == 'blind_visual_check_did_not_support_abnormal_operation' for entry in row.get('selection_exclusions', []))
                for row in results
            ),
        },
        'api_requests': {
            'new_requests_for_this_manifest': current_request_stats,
            'inherited_run_file': run_files[-1].name if reuse_manifest and run_files else None,
            'inherited_run': request_stats(latest_requests) if reuse_manifest else None,
            'latest_run_file': run_files[-1].name if not reuse_manifest and run_files else None,
            'latest_run': request_stats(latest_requests) if not reuse_manifest else None,
            'all_run_records': request_stats(run_requests),
        },
        'reuse': reuse_manifest,
        'integrity': {
            'duplicate_question_ids': duplicate_question_ids,
            'unknown_question_clip_count': len(unknown_clip_questions),
            'unknown_evidence_count': len(unknown_evidence),
            'missing_media_count': len(missing_media),
            'status_mismatch_count': len(status_mismatch),
            'contract_issue_count': len(contract),
            'hard_issues': issues,
        },
        'contract_issues': contract,
        'status_mismatches': status_mismatch,
        'unknown_evidence': unknown_evidence,
        'missing_media': missing_media,
    }
    (folder / 'full_run_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = [
        f"# Full generation audit: {config.get('version')}",
        '',
        f"State: **{progress.get('state')}**; manifest: **{len(manifest)}**; questions: **{len(questions)}**; hard issues: **{len(issues)}**.",
        '',
        '| item | value |',
        '|---|---:|',
        f"| raw/repaired/manifest clips | {len(raw)} / {len(clips)} / {len(manifest)} |",
        f"| questions | {len(questions)} |",
        f"| candidate / held | {sum(row.get('status') == 'candidate' for row in questions)} / {sum(row.get('status') == 'held' for row in questions)} |",
        f"| fixed MCQ candidates / exported | {len(fixed_mcq)} / {sum(row.get('kind') == 'mcq_anomaly_clip' for row in questions)} |",
        f"| API requests for this manifest | {sum(current_request_stats.values())} new requests; results reused: {bool(reuse_manifest)} |",
        f"| minimum manifest duration | {duration_stats(manifest)['min_s']:.3f}s |",
        '',
        '## QA types',
        '',
        '```json',
        json.dumps(report['question_kinds'], ensure_ascii=False, indent=2),
        '```',
        '',
        '## Integrity',
        '',
        '```json',
        json.dumps(report['integrity'], ensure_ascii=False, indent=2),
        '```',
        '',
        'Automatic holds remain in `questions.jsonl` with `human_review=unreviewed`; this report does not mark them as human-approved.',
    ]
    (folder / 'full_run_audit.md').write_text('\n'.join(lines) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    value = run(args.config)
    print(json.dumps(value, ensure_ascii=False, indent=2))
