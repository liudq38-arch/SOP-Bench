import math

from .common import fingerprint


def evaluate(evidence, policy):
    missing = []
    if evidence.get('policy_hash') != fingerprint(policy):
        missing.append('policy_hash_missing_or_mismatched')
    for name in policy['require']:
        if evidence.get('requirements', {}).get(name) is not True:
            missing.append(name)
    values = evidence.get('metrics', {})
    minimums = {'hard_check_pass_rate', 'overall_quality_pass_rate', 'per_kind_quality_pass_rate', 'visual_evidence_pass_rate', 'completion_rate', 'min_independent_events_per_kind', 'min_validation_trials', 'min_validation_participants'}
    for name, bound in policy['thresholds'].items():
        value = values.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            missing.append('missing_metric:' + name)
        elif name.endswith('_rate') and not 0 <= value <= 1:
            missing.append('invalid_rate:' + name)
        elif (name in minimums and value < bound) or (name == 'severe_defects' and value != 0):
            missing.append('failed_metric:' + name)
    if evidence.get('review_source') not in ['research_agent_direct_evidence', 'human_independent']:
        missing.append('review_source_not_independent_evidence')
    if not evidence.get('pipeline_hash') or evidence.get('reviewed_pipeline_hash') != evidence.get('pipeline_hash'):
        missing.append('unfrozen_or_mismatched_review_version')
    return {'kind': evidence.get('kind'), 'release': not missing, 'blocked_by': missing, 'policy_hash': fingerprint(policy), 'scope': policy['scope']}
