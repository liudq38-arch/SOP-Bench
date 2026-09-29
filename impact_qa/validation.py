def validate_evidence_graph(observation, facts, images):
    issues = []
    frame_ids = {x['evidence_id'] for x in images}
    observation_ids = set()
    for item in observation.get('observations', []):
        oid = item.get('id')
        if not oid or oid in observation_ids:
            issues.append('observation_id_missing_or_duplicate')
        observation_ids.add(oid)
        if not item.get('evidence_ids') or any(e not in frame_ids for e in item.get('evidence_ids', [])):
            issues.append(f'observation:{oid}:invalid_evidence')
    fact_ids = set()
    for fact in facts.get('facts', []):
        fid = fact.get('id')
        if not fid or fid in fact_ids:
            issues.append('fact_id_missing_or_duplicate')
        fact_ids.add(fid)
        if any(o not in observation_ids for o in fact.get('observation_ids', [])):
            issues.append(f'fact:{fid}:unknown_observation')
        if fact.get('support') in ['visual', 'both'] and not fact.get('observation_ids'):
            issues.append(f'fact:{fid}:visual_without_observation')
        if fact.get('support') in ['annotation', 'both'] and not fact.get('annotation_fields'):
            issues.append(f'fact:{fid}:annotation_without_field')
    return issues


def qualifies_for_review_pass(pair, review, issues):
    return review.get('decision') == 'pass' and review.get('supported') is True and review.get('visually_answerable') is True and review.get('relevant_to_procedure') is True and review.get('answer_leakage') is False and review.get('duplicate') is False and pair.get('answerability') == 'visible' and not issues


def select_visual_facts(observation, facts, images):
    valid_frames = {f['evidence_id'] for f in images}
    observed = {o['id']: o for o in observation.get('observations', []) if o.get('id') and o.get('evidence_ids') and all(e in valid_frames for e in o['evidence_ids'])}
    selected, withheld = [], []
    for fact in facts.get('facts', []):
        refs = fact.get('observation_ids', [])
        if fact.get('support') not in ['visual', 'both'] or not fact.get('usable_for_qa'):
            withheld.append({'fact_id': fact.get('id'), 'reason': 'not_usable_visual_fact'})
        elif not refs or any(o not in observed for o in refs):
            withheld.append({'fact_id': fact.get('id'), 'reason': 'missing_valid_observation'})
        elif fact.get('support') == 'both' and not fact.get('annotation_fields'):
            withheld.append({'fact_id': fact.get('id'), 'reason': 'missing_annotation_reference'})
        else:
            evidence = list(dict.fromkeys(e for oid in refs for e in observed[oid]['evidence_ids']))
            selected.append(dict(fact, evidence_ids=evidence))
    return selected, withheld


def derive_pair_evidence(generation, facts):
    index = {f['id']: f for f in facts}
    pairs = []
    for pair in generation.get('qa_pairs', []):
        refs = pair.get('supporting_fact_ids', [])
        evidence = list(dict.fromkeys(e for fid in refs if fid in index for e in index[fid]['evidence_ids']))
        pairs.append(dict(pair, evidence_ids=evidence, evidence_link_method='deterministic_fact_observation_frame_chain'))
    return dict(generation, qa_pairs=pairs)
