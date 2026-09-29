import hashlib
import html
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.visual_ablation import CONDITIONS


WRONG_ORDERS = {
    'uniform_full': {'gt_2f4c67899c117d82da66'},
    'uniform_crop': {'gt_b56948156e2c6ed45898', 'gt_b798864678cad52d8acd', 'gt_2283ec15593bda5e4289', 'gt_85f49f6c206ca7682d97', 'gt_c33f66a67e2fda487eca'},
    'dense_crop': {'gt_b56948156e2c6ed45898', 'gt_b798864678cad52d8acd', 'gt_2283ec15593bda5e4289', 'gt_85f49f6c206ca7682d97', 'gt_c33f66a67e2fda487eca'},
    'dense_crop_manual': {'gt_b56948156e2c6ed45898', 'gt_85f49f6c206ca7682d97', 'gt_c33f66a67e2fda487eca'},
    'dense_crop_action_reference': {'gt_2283ec15593bda5e4289', 'gt_85f49f6c206ca7682d97', 'gt_c33f66a67e2fda487eca'},
    'dense_crop_action_glossary': {'gt_2283ec15593bda5e4289', 'gt_c33f66a67e2fda487eca'},
}


def compare(c, record):
    answer = record['visual_review']
    if answer['answerability'] != 'answerable':
        return 'abstain'
    text = answer['answer'].strip().lower()
    if c['kind'] == 'tool_identity':
        if 'allen' in text or 'hex' in text:
            return 'tool_subtype_conflict'
        target = 'screwdriver' if 'screwdriver' in c['gt_answer'] else 'wrench'
        return 'short_answer_match' if target in text else 'short_answer_conflict'
    if c['answer_polarity'] in ['yes', 'no']:
        assert text.startswith(('yes', 'no')), (c['contract_id'], text)
        return 'short_answer_match' if text.startswith(c['answer_polarity']) else 'short_answer_conflict'
    if c['kind'] == 'observed_order':
        return 'short_answer_conflict' if c['contract_id'] in WRONG_ORDERS[record['condition']] else 'short_answer_match'
    raise ValueError('manual_review_needed:' + c['contract_id'] + ':' + text)


def main():
    cases = read_jsonl(OUT / 'gt_v13_inputs/cases.jsonl')
    results = read_jsonl(OUT / 'gt_v13/results.jsonl')
    lookup = {(c['contract_id'], c['condition']): c for c in cases}
    contracts = {c['contract_id']: c for c in cases if c['condition'] == 'dense_crop'}
    extra = []
    for filename in ['top_results.jsonl', 'action_reference_results.jsonl', 'action_glossary_results.jsonl', 'install_compact_results.jsonl', 'install_state_strict_results.jsonl']:
        extra += read_jsonl(OUT / 'gt_v13' / filename)
    initial_install = [read_json(p) for p in sorted((OUT / 'gt_v13/component_installed_action_reference_runs').glob('*.json'))]
    extra += initial_install
    records = []
    counts = defaultdict(Counter)
    by_kind = defaultdict(lambda: defaultdict(Counter))
    for r in results + extra:
        c = lookup.get((r['contract_id'], r['condition']), contracts[r['contract_id']])
        verdict = compare(c, r)
        flags = []
        evidence = r['visual_review'].get('visible_evidence', '')
        if not isinstance(evidence, str):
            evidence = json.dumps(evidence, ensure_ascii=False)
        if len(evidence.split()) > 120:
            flags.append('excessive_evidence_length')
        if r['condition'] == 'dense_crop_component_installed_action_reference' and r['contract_id'] == 'gt_28c1f0948d9196a8d772':
            flags.append('answer_evidence_contradiction_agent_observed')
        if r['condition'] == 'dense_crop_install_reference_compact':
            flags.append('attachment_overstatement_requires_edit_agent_observed')
        if r['condition'] == 'dense_crop_install_state_strict':
            if r['contract_id'] in {'gt_a447a69e4fd87eeb4454', 'gt_28c1f0948d9196a8d772', 'gt_736d6aa567b506dccc52'}:
                flags.append('precise_attachment_surface_unverified')
            if r['contract_id'] == 'gt_233db8f2ab7c5bc5ff27':
                flags.append('cutoff_action_claim_mismatch_agent_observed')
        if r['condition'] == 'dense_crop_action_glossary' and r['contract_id'] == 'gt_85f49f6c206ca7682d97':
            flags.append('coarse_correct_answer_fine_object_identity_not_verified')
        record = dict(r, kind=c['kind'], question=c['question'], gt_answer=c['gt_answer'], short_answer_comparison=verdict, response_quality_flags=flags, comparison_scope='source-aware research-agent reading; not independent visual evidence approval', human_review_status='pending_human_review')
        records.append(record)
        counts[r['condition']][verdict] += 1
        by_kind[r['condition']][c['kind']][verdict] += 1
    save_jsonl(OUT / 'gt_v13/compared_results.jsonl', records)
    summary = {'target_cases': len(contracts), 'main_calls': len(results), 'main_conditions': CONDITIONS, 'condition_counts': dict(counts), 'by_kind': {k: dict(v) for k, v in by_kind.items()}, 'comparison_not_accuracy': True, 'holdout_used': False, 'full_scale_release': False, 'tool_subtype_rule': 'Allen/hex wrench or key is a conflicting added subtype relative to combination-wrench source; count separately rather than accepting substring wrench.'}
    summary['initial_installation_reference'] = {'attempted_cases': 4, 'valid_responses': len(initial_install), 'failed_cases': 4 - len(initial_install), 'failure': 'JSON truncation after three automatic attempts; retained in denominator', 'valid_responses_in_condition_counts': True}
    save_json(REPORTS / 'gt_v13_comparison_summary.json', summary)
    cards = []
    for identifier, c in contracts.items():
        rendered = []
        for r in records:
            if r['contract_id'] != identifier:
                continue
            condition = r['condition']
            sheet = lookup.get((identifier, condition), c)['contact_sheet']
            rel = os.path.relpath(sheet, OUT / 'gt_v13')
            v = r['visual_review']
            rendered.append('<section><h3>' + html.escape(condition) + '</h3><p>' + html.escape(r['short_answer_comparison'] + ' | ' + v['answerability'] + ' | ' + v['answer']) + '</p><details><summary>输入图板与模型证据</summary><img loading="lazy" src="' + html.escape(rel, quote=True) + '"><pre>' + html.escape(json.dumps(v, ensure_ascii=False, indent=2)) + '</pre></details></section>')
        cards.append('<article><h2>' + html.escape(identifier + ' / ' + c['kind']) + '</h2><p>' + html.escape(c['question']) + '</p><details><summary>GT参考答案</summary><p>' + html.escape(c['gt_answer']) + '</p></details>' + ''.join(rendered) + '</article>')
    page = '<!doctype html><html lang="zh"><meta charset="utf-8"><title>IMPACT视觉输入对照</title><style>body{font:16px sans-serif;max-width:1200px;margin:auto}article{border-top:2px solid #666;padding:20px 0}section{border-left:3px solid #aaa;padding-left:15px;margin:16px 0}img{max-width:100%}pre{white-space:pre-wrap}</style><h1>固定问答的视觉输入对照</h1><p>这是知情开发诊断，不是盲验收。短答案一致不等于视觉解释通过。前三条件等图数/目标画布；手册、训练示例与top补测增加参考信息与预算。补测图板默认展示原dense目标输入，额外参考媒体见各输入目录。</p><pre>' + html.escape(json.dumps(summary, ensure_ascii=False, indent=2)) + '</pre>' + ''.join(cards) + '</html>'
    (OUT / 'gt_v13/review.html').write_text(page)
    api = [read_json(OUT / 'api_cache' / (key + '.json')) for key in sorted({r['cache_key'] for r in results + extra})]
    metrics = {'successful_unique_cache_keys': len(api), 'successful_response_records': len(results + extra), 'actual_http_request_count': None, 'cache_collision_note': 'Four normal cases have identical B/C inputs and shared keys; concurrent calls retained different explanation text. Per-run records are preserved; cache metrics describe unique final entries, not exact HTTP request count.', 'prompt_tokens_by_stage': {}, 'request_seconds_median': statistics.median(r['seconds'] for r in api)}
    failed = [read_json(p) for p in (OUT / 'api_cache').glob('*.json')]
    failed = [r for r in failed if r.get('stage', '').startswith('gt_v13_') and r.get('status') == 'error']
    metrics['failed_cache_records'] = failed
    for stage in sorted({r['stage'] for r in api}):
        rows = [r for r in api if r['stage'] == stage]
        tokens = [r['usage']['prompt_tokens'] for r in rows]
        metrics['prompt_tokens_by_stage'][stage] = {'calls': len(rows), 'min': min(tokens), 'median': statistics.median(tokens), 'max': max(tokens)}
    save_json(REPORTS / 'gt_v13_api_stats.json', metrics)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
