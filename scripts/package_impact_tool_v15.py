import hashlib
import html
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import verify_reference
from impact_qa.tool_adjudication import route
from impact_qa.tool_review_v15 import select_images


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    folder = OUT / 'gt_v15_reviewed'
    old_gate_hash = digest(REPORTS / 'gt_v14_release_gate.json')
    frozen_counts = {}
    for name in ['frozen_v7.json', 'gt_v12_code_snapshot.json', 'gt_v14_tool_pipeline_frozen.json']:
        frozen = read_json(REPORTS / name)
        files = frozen.get('files', frozen)
        for path, value in files.items():
            assert digest(ROOT / path) == value, 'frozen:' + path
        frozen_counts[name] = len(files)
    review_sources = ['outputs/impact_qa/gt_v14_1_tools/agent_development_review.jsonl', 'outputs/impact_qa/gt_v14_frozen_acceptance/agent_adjudication.jsonl', 'outputs/impact_qa/gt_v15_tools/agent_development_delta_review.jsonl', 'outputs/impact_qa/gt_v15_tools/agent_endpoint_adjudication.json']
    reviews = {}
    for r in read_jsonl(ROOT / review_sources[0]):
        reviews[r['contract_id']] = {'decision': 'supported' if r['qa_assessment'] == 'supported_candidate' else 'hold', 'note': r['notes'], 'source_record': review_sources[0]}
    for r in read_jsonl(ROOT / review_sources[1]):
        reviews[r['contract_id']] = {'decision': 'supported' if r['quality_pass'] else 'hold', 'note': r['review_note'], 'source_record': review_sources[1]}
    for r in read_jsonl(ROOT / review_sources[2]):
        reviews[r['contract_id']] = {'decision': r['decision'], 'note': r['note'], 'source_record': review_sources[2]}
    endpoint_review = read_json(ROOT / review_sources[3])
    for r in endpoint_review['changes']:
        reviews[r['contract_id']] = {**r, 'source_record': review_sources[3]}
    for cid in endpoint_review['confirmed_holds']:
        assert reviews[cid]['decision'] == 'hold'
    candidates, evaluation, disposition, all_cases = [], [], [], []
    media, phase_counts, cards = {}, {}, []
    source_references = 0
    for phase, source in [('development', 'gt_v14_1_tools'), ('exposed_regression', 'gt_v14_acceptance_inputs')]:
        cases = read_jsonl(OUT / source / 'contracts.jsonl')
        endpoint = {c['contract_id']: c for c in read_jsonl(OUT / 'gt_v15_endpoint_inputs' / phase / 'contracts.jsonl')}
        primary = {r['contract_id']: r for r in read_jsonl(OUT / 'gt_v15_tools/chronological20' / phase / 'full_results.jsonl')}
        assert len(cases) == len(primary)
        states = []
        for c in cases:
            cid = c['contract_id']
            r = primary[cid]
            assert r['status'] == 'ok'
            assert r['image_refs'] == select_images(c, 'chronological20')
            for ref in c['references']:
                verify_reference(ref)
                source_references += 1
            assert r['generation'] == {'question': c['question'], 'answer': c['canonical_answer']}
            assert len(set(c['options'])) == 3 and c['options'][c['correct_option']] == 'A ' + c['tool'] + '.'
            cached = read_json(OUT / 'api_cache' / (r['cache_key'] + '.json'))
            assert set(cached['request_metadata']['payload']) == {'question', 'clip_start_original_s', 'clip_end_original_s_exclusive'}
            assert cached['request_metadata']['image_refs'] == r['image_refs']
            images = r['image_refs'] + [{**im, 'evidence_id': 'detail_' + im['evidence_id']} for im in endpoint[cid]['image_refs'] if im['evidence_id'].startswith('context_')]
            images = sorted(images, key=lambda im: (im['frame_index'], im['evidence_id']))
            assert len(images) == len({im['evidence_id'] for im in images}) == 22
            for im in images:
                assert c['start_frame'] <= im['frame_index'] <= c['end_frame_inclusive']
                assert abs(im['requested_time_s'] - im['frame_index'] / 30) < 1e-8
                media[im['path']] = im['sha256']
            review = reviews[cid] | {'reviewer': 'research_agent_direct_evidence', 'human_review': False, 'independent_acceptance': False}
            status = route(r, review)
            disposition.append({'contract_id': cid, 'phase': phase, 'primary_comparison': r['comparison'], 'routing_without_review': route(r), 'status': status, 'review': review})
            states.append(status)
            all_cases.append(c | {'image_refs': images, 'phase': phase})
            if status.startswith('hold'):
                continue
            candidate = {'contract_id': cid, 'phase': phase, 'video_id': c['video_id'], 'question': c['question'], 'answer': c['canonical_answer'], 'options': c['options'], 'correct_option': c['correct_option'], 'references': c['references'], 'status': status, 'review_source': 'research_agent_direct_evidence', 'human_review': False, 'independent_acceptance': False, 'release_status': 'not_released_pending_new_independent_acceptance', 'image_refs': images, 'annotation_assisted_sampling': True, 'model_narrative_is_gold': False}
            candidates.append(candidate)
            for form in ['open', 'mcq']:
                evaluation.append({'qa_id': fingerprint([cid, form, 'v15_reviewed'])[:24], 'format': form, 'question': c['question'], 'image_paths': [im['path'] for im in images], 'original_times_s': [im['requested_time_s'] for im in images], 'annotation_assisted_sampling': True, **({'options': c['options']} if form == 'mcq' else {})})
            figures = ''.join('<figure><img loading="lazy" src="' + html.escape(os.path.relpath(im['path'], folder)) + '"><figcaption>' + html.escape(im['evidence_id'] + ' / ' + str(im['requested_time_s'])) + '</figcaption></figure>' for im in images)
            cards.append('<article><h2>' + html.escape(cid) + '</h2><p>' + html.escape(c['question']) + '</p><p>' + html.escape(status + ' / ' + phase) + '</p><details><summary>查看GT答案与选项</summary><p>' + html.escape(c['canonical_answer']) + '</p><p>' + html.escape(str(c['options'])) + '</p></details><div>' + figures + '</div></article>')
        phase_counts[phase] = dict(Counter(states))
    for path, value in media.items():
        assert digest(path) == value, 'media:' + path
    assert len(disposition) == len({c['contract_id'] for c in disposition}) == 79
    for r in evaluation:
        assert not {'answer', 'correct_option', 'references', 'canonical_answer', 'review'}.intersection(r)
    save_jsonl(folder / 'reviewed_candidates.jsonl', candidates)
    save_jsonl(folder / 'evaluation_inputs.jsonl', evaluation)
    save_jsonl(folder / 'disposition.jsonl', disposition)
    save_jsonl(folder / 'exception_review_queue.jsonl', [r for r in disposition if r['routing_without_review'] == 'needs_direct_evidence_review'])
    save_jsonl(folder / 'hold.jsonl', [r for r in disposition if r['status'].startswith('hold')])
    save_jsonl(folder / 'first10.jsonl', candidates[:10])
    save_json(folder / 'media_hashes.json', media)
    (folder / 'review.html').write_text('<!doctype html><meta charset="utf-8"><title>v15 reviewed candidates</title><style>body{max-width:1400px;margin:auto}article div{display:flex;flex-wrap:wrap}figure{width:45%;margin:8px}img{width:100%}</style><h1>研究代理复查候选：非真人金标准，未通过新独立验收</h1><p>公开输入含20张按时序排列的原图和2张端点细节图；GT辅助取窗。模型私有解释不是答案。</p>' + ''.join(cards))
    snapshot = lambda: {str(p): (p.stat().st_mtime_ns, digest(p)) for phase in ['development', 'exposed_regression'] for sub in ['runs', 'request_audit'] for p in (OUT / 'gt_v15_tools/chronological20' / phase / sub).glob('*.json')}
    before = snapshot()
    for phase in ['development', 'exposed_regression']:
        subprocess.run([sys.executable, str(ROOT / 'scripts/run_impact_tool_v15.py'), '--phase', phase, '--condition', 'chronological20'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    assert snapshot() == before, 'resume:new_or_modified_call'
    assert digest(REPORTS / 'gt_v14_release_gate.json') == old_gate_hash
    summary = {'events': len(disposition), 'primary_proposed': sum(r['primary_comparison'] == 'short_answer_match' for r in disposition), 'reviewed_candidates': len(candidates), 'open_qa': len(candidates), 'mcq_qa': len(candidates), 'holds': sum(r['status'].startswith('hold') for r in disposition), 'reviewed_exceptions': sum(r['status'] == 'reviewed_exception_candidate' for r in disposition), 'phase_status_counts': phase_counts, 'source_references_checked': source_references, 'unique_media_hashes_checked': len(media), 'export_images_per_event': 22, 'primary_model_images_per_event': 20, 'candidate_tool_distribution': dict(Counter(c['answer'] for c in candidates)), 'option_positions': dict(Counter(c['correct_option'] for c in candidates)), 'review_source_hashes': {p: digest(ROOT / p) for p in review_sources}, 'frozen_files_checked': frozen_counts, 'resume_new_requests': 0, 'old_v14_gate_unchanged': True, 'full_scale_release': False, 'independent_acceptance': False, 'reason': 'Routing changed after old reserve was exposed; reviewed candidates and manual exception handling do not constitute a fresh frozen acceptance.'}
    save_json(REPORTS / 'gt_v15_final_summary.json', summary)
    save_json(REPORTS / 'gt_v15_final_strategy.json', {'primary': 'chronological20 Qwen3.5-27B', 'review_rule': 'Model agreement creates a pending candidate; abstention/conflict enters direct evidence review. Only recorded source-backed evidence review may retain exceptions; unresolved evidence stays hold.', 'public_media': '20 original chronological images plus 2 high-resolution context detail images, with distinct IDs and original times', 'default_reviewer': 'research_agent_direct_evidence', 'not_human_gold': True, 'full_scale_release': False, 'supersedes': 'gt_v15_strategy_selection.json for provisional model-only selection', 'independent_validation_required': True})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
