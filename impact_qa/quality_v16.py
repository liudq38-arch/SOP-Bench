import hashlib
import math
from pathlib import Path

from .common import fingerprint
from .gt_qa import verify_reference


SCHEMAS = {
    'generate': {'open_question', 'answer', 'mcq_question', 'visual_grade', 'limitation', 'claims'},
    'blind': {'answer', 'visual_grade', 'tool', 'before_id', 'after_id', 'image_ids', 'observation', 'limitation'},
    'visual_audit': {'visual_grade', 'answer_supported', 'blind_agrees', 'question_unambiguous', 'evidence_valid', 'claim_checks', 'supported_option_indices', 'option_checks', 'counterevidence', 'before_id', 'after_id'},
    'source_audit': {'source_entails_answer', 'claims_entailed', 'question_preserves_scope', 'open_mcq_equivalent', 'no_answer_leakage', 'unique_correct_option', 'correct_option_index', 'blind_matches_gt', 'unsupported_claims', 'reason'},
}
BOOLEANS = {
    'visual_audit': ['answer_supported', 'blind_agrees', 'question_unambiguous', 'evidence_valid'],
    'source_audit': ['source_entails_answer', 'claims_entailed', 'question_preserves_scope', 'open_mcq_equivalent', 'no_answer_leakage', 'unique_correct_option', 'blind_matches_gt'],
}


def require(condition, reason):
    if not condition:
        raise ValueError('quality_v16:' + reason)


def short(value, limit):
    require(isinstance(value, str) and len(value.split()) <= limit, 'invalid_text')


def ids(values, allowed, empty=True):
    require(isinstance(values, list) and all(isinstance(v, str) for v in values), 'invalid_ids')
    require(len(values) == len(set(values)) and set(values) <= set(allowed), 'unknown_or_duplicate_ids')
    require(empty or bool(values), 'missing_evidence')


def ordered_pair(value, c):
    refs = {im['evidence_id']: im for im in c['image_refs']}
    a, b = value['before_id'], value['after_id']
    require(a in refs and b in refs, 'missing_transition')
    require(refs[a]['frame_index'] < refs[b]['frame_index'], 'nonchronological_transition')


def check_integrity(c):
    for ref in c['references']:
        verify_reference(ref)
    require(len(c['options']) == 3 and len(set(c['options'])) == 3, 'duplicate_options')
    require(type(c['correct_option']) is int and 0 <= c['correct_option'] < 3, 'invalid_gt_index')
    require(c['references'] and c['image_refs'], 'empty_contract')
    image_ids = [im['evidence_id'] for im in c['image_refs']]
    require(len(image_ids) == len(set(image_ids)), 'duplicate_frame_id')
    require(2 <= len(image_ids) <= 32, 'image_budget')
    times = []
    for im in c['image_refs']:
        require(im.get('media_type', 'image') == 'image', 'explicit_frames_required')
        n = im['frame_index']
        require(c['start_frame'] <= n <= c['end_frame_inclusive'], 'frame_out_of_scope')
        require(math.isclose(im['requested_time_s'], n / 30, abs_tol=1e-5), 'clock_mismatch')
        require(hashlib.sha256(Path(im['path']).read_bytes()).hexdigest() == im['sha256'], 'media_hash_mismatch')
        times.append(n)
    require(times == sorted(times), 'nonchronological_input')
    if c['kind'] == 'tool_identity':
        seg = c['references'][0]['value']
        require(seg['phase'] == 'normal' and not any(seg['anomaly_type']), 'tool_source_anomaly')
        require(c['hand'] in ['left', 'right'], 'invalid_hand')
        label = c['references'][1]['value']['name']
        expected = 'wrench' if 'wrench' in label else 'screwdriver' if 'screwdriver' in label else None
        require(label.startswith('pick_up_') and c['tool'] == expected, 'tool_source_mismatch')
        require(c['options'][c['correct_option']] == f'A {expected}.', 'tool_option_mismatch')


def public_payload(c, question):
    return {'kind': c['kind'], 'question': question, 'clip_start_s': c['start_frame'] / 30, 'clip_end_s_exclusive': (c['end_frame_inclusive'] + 1) / 30, 'allowed_image_ids': [im['evidence_id'] for im in c['image_refs']]}


def source_payload(c):
    return {'kind': c['kind'], 'question_proposition': c['question'], 'mcq_question_proposition': c['mcq_question'], 'canonical_answer': c['canonical_answer'], 'options': c['options'], 'correct_option_index': c['correct_option'], 'facts': c['facts'], 'sources': [{'source_id': 's' + str(i), 'value': ref['value'], 'pointer': ref['pointer']} for i, ref in enumerate(c['references'])], 'allowed_image_ids': [im['evidence_id'] for im in c['image_refs']], 'forbidden_claims': c.get('forbidden_claims', [])}


def validate(stage, value, c, generation=None):
    require(isinstance(value, dict) and set(value) == SCHEMAS[stage], 'schema_' + stage)
    allowed = [im['evidence_id'] for im in c['image_refs']]
    if 'visual_grade' in value:
        require(type(value['visual_grade']) is int and 0 <= value['visual_grade'] <= 3, 'invalid_grade')
    for key in BOOLEANS.get(stage, []):
        require(type(value[key]) is bool, 'invalid_boolean_' + key)
    if stage == 'generate':
        for key in ['open_question', 'mcq_question']:
            short(value[key], 40)
            require(value[key].strip().endswith('?'), 'invalid_question')
            require(not any(t in value[key].lower() for t in ['annotation', 'ground truth', 'tas-', 'asr', '_']), 'metadata_leak')
        short(value['answer'], 45)
        require(bool(value['answer'].strip()), 'empty_answer')
        short(value['limitation'], 45)
        claims = value['claims']
        require(isinstance(claims, list) and 1 <= len(claims) <= 3, 'invalid_claims')
        for claim in claims:
            require(isinstance(claim, dict) and set(claim) == {'claim', 'source_ids', 'image_ids'}, 'invalid_claim')
            short(claim['claim'], 35)
            ids(claim['source_ids'], ['s' + str(i) for i in range(len(c['references']))], False)
            ids(claim['image_ids'], allowed, value['visual_grade'] < 3)
    elif stage == 'blind':
        for key in ['answer', 'observation', 'limitation']:
            short(value[key], 45)
        require(value['tool'] in ['screwdriver', 'wrench', 'pliers', 'unknown', 'not_applicable'], 'invalid_tool')
        ids(value['image_ids'], allowed, value['visual_grade'] < 3)
    elif stage == 'visual_audit':
        short(value['counterevidence'], 45)
        checks = value['claim_checks']
        require(isinstance(checks, list) and len(checks) == len(generation['claims']), 'claim_check_count')
        require(all(type(ch.get('claim_index')) is int for ch in checks), 'claim_index_type')
        require(sorted(ch['claim_index'] for ch in checks) == list(range(len(checks))), 'claim_check_indices')
        for ch in checks:
            require(set(ch) == {'claim_index', 'supported', 'image_ids', 'observation'} and type(ch['supported']) is bool, 'claim_check_schema')
            ids(ch['image_ids'], allowed, not ch['supported'])
            short(ch['observation'], 25)
        options = value['option_checks']
        require(isinstance(options, list) and len(options) == 3, 'option_count')
        require(all(type(o.get('index')) is int for o in options), 'option_index_type')
        require(sorted(o['index'] for o in options) == [0, 1, 2], 'option_indices')
        for o in options:
            require(set(o) == {'index', 'verdict', 'reason'} and o['verdict'] in ['supported', 'contradicted', 'uncertain'], 'option_schema')
            short(o['reason'], 25)
        indices = value['supported_option_indices']
        require(isinstance(indices, list) and all(type(i) is int and i in [0, 1, 2] for i in indices), 'supported_indices')
        require(sorted(indices) == sorted(o['index'] for o in options if o['verdict'] == 'supported'), 'option_verdict_inconsistent')
    else:
        require(type(value['correct_option_index']) is int and value['correct_option_index'] in [0, 1, 2], 'source_index')
        require(isinstance(value['unsupported_claims'], list), 'unsupported_schema')
        for text in value['unsupported_claims']:
            short(text, 60)
        short(value['reason'], 60)
    if stage in ['blind', 'visual_audit']:
        for key in ['before_id', 'after_id']:
            require(value[key] is None or isinstance(value[key], str) and value[key] in allowed, 'invalid_endpoint')
        if c['kind'] == 'tool_identity' and value['visual_grade'] == 3:
            ordered_pair(value, c)
            if stage == 'blind':
                require({value['before_id'], value['after_id']} <= set(value['image_ids']), 'endpoint_not_cited')
    return value


def decide(c, stages, grade=3):
    g, b, v, s = [stages[k] for k in ['generate', 'blind', 'visual_audit', 'source_audit']]
    reasons = []
    for stage, value in [('generate', g), ('blind', b), ('visual_audit', v)]:
        if value['visual_grade'] < grade:
            reasons.append(stage + ':insufficient_visual_evidence')
    for stage, value in [('visual_audit', v), ('source_audit', s)]:
        reasons.extend(stage + ':' + key for key in BOOLEANS[stage] if not value[key])
    if s['correct_option_index'] != c['correct_option'] or v['supported_option_indices'] != [c['correct_option']]:
        reasons.append('answer_option_disagreement')
    if any(o['verdict'] == 'uncertain' for o in v['option_checks']):
        reasons.append('unresolved_distractor')
    if any(not ch['supported'] for ch in v['claim_checks']):
        reasons.append('unsupported_visual_claim')
    if s['unsupported_claims']:
        reasons.append('unsupported_source_claim')
    if c['kind'] == 'tool_identity' and b['tool'] != c['tool']:
        reasons.append('typed_blind_tool_conflict')
    return {'disposition': 'quarantine' if reasons else 'model_passed_unvalidated', 'reasons': reasons, 'evidence_grade_min': min(g['visual_grade'], b['visual_grade'], v['visual_grade']), 'calibrated_probability': None, 'formal_release': False}
