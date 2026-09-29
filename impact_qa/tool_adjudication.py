def route(primary, review=None):
    if primary.get('status') != 'ok':
        return 'hold_run_error'
    if review is None:
        return 'pending_candidate_audit' if primary.get('proposed_retain') else 'needs_direct_evidence_review'
    if review.get('reviewer') not in ['research_agent_direct_evidence', 'human_independent']:
        raise ValueError('adjudication:invalid_reviewer')
    if not review.get('source_record') or not review.get('note'):
        raise ValueError('adjudication:missing_provenance')
    if review.get('decision') == 'hold':
        return 'hold_visual_evidence'
    if review.get('decision') != 'supported':
        raise ValueError('adjudication:invalid_decision')
    return 'reviewed_primary_candidate' if primary.get('proposed_retain') else 'reviewed_exception_candidate'
