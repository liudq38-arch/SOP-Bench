from impact_qa.mcq_grouped import option_ids


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def enum(values):
    return {'type': 'string', 'enum': list(values)}


def array(items, minimum, maximum):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum}


def observation_schema(events, media):
    item = obj({'event_id': enum(e['event_id'] for e in events), 'abnormality': enum(['visible', 'uncertain', 'not_visible']), 'confidence': enum(['high', 'medium', 'low']), 'evidence_frame_ids': array(enum(f['frame_id'] for f in media['sampled_frames']), 0, 4), 'description': {'type': 'string'}})
    return obj({'items': array(item, len(events), len(events))})


def adjudication_schema(events, media, contextual=False, grounding=False):
    properties = {'option_id': enum('BCDEFG'), 'verdict': enum(['supported', 'uncertain', 'contradicted']), 'confidence': enum(['high', 'medium', 'low']), 'evidence_frame_ids': array(enum(f['frame_id'] for f in media['sampled_frames']), 0, 4), 'reason': {'type': 'string'}}
    if contextual:
        properties.update(observation_consistency=enum(['supports_facts', 'missing_facts', 'contradiction']), reference_basis=enum(['visible_geometry','visible_interference','observed_timing','provided_domain_reference','missing_reference']))
    label = obj(properties)
    fields = {'event_id': enum(e['event_id'] for e in events), 'labels': array(label, 1, 6)}
    if grounding:
        fields['action_grounding'] = obj({'verdict':enum(['matches','uncertain','conflicts']), 'confidence':enum(['high','medium','low']), 'observation_consistency':enum(['supports_facts','missing_facts','contradiction']), 'evidence_frame_ids':array(enum(f['frame_id'] for f in media['sampled_frames']),0,4), 'description':{'type':'string'}})
    item = obj(fields)
    return obj({'items': array(item, len(events), len(events))})


def check_ids(result, events):
    got = [r['event_id'] for r in result['items']]
    expected = [e['event_id'] for e in events]
    if sorted(got) != sorted(expected):
        raise ValueError('mcq_grouped_review:event_set_mismatch')


def evidence_errors(ids, event, media, minimum_span=1.0):
    by_id = {f['frame_id']: f for f in media['sampled_frames']}
    if len(ids) < 2 or len(ids) != len(set(ids)) or any(i not in by_id for i in ids):
        return ['insufficient_or_invalid_evidence_frames']
    frames = [by_id[i] for i in ids]
    if any(not event['start_frame'] <= f['source_frame_index'] < event['end_frame_exclusive'] for f in frames):
        return ['evidence_outside_event']
    if max(f['source_pts_s'] for f in frames) - min(f['source_pts_s'] for f in frames) < minimum_span:
        return ['evidence_time_span_below_minimum']
    return []


def assess_event(event, observation, adjudication, media, config):
    reasons = []
    if config.get('require_blind_abnormality', True) and (observation['abnormality'] != 'visible' or observation['confidence'] != 'high'):
        reasons.append('blind_observation_not_high_confidence_visible')
    if observation['confidence'] != 'high':
        reasons.append('low_confidence_observation')
    reasons.extend(evidence_errors(observation['evidence_frame_ids'], event, media, config['minimum_evidence_span_seconds']))
    if not observation['description'].strip():
        reasons.append('empty_visual_description')
    expected = option_ids([event])
    labels = adjudication.get('labels', [])
    if sorted(r['option_id'] for r in labels) != expected:
        reasons.append('gt_label_set_mismatch')
    for row in labels:
        if config.get('minimum_type_support_seconds') and event.get('type_support_seconds',{}).get(row['option_id'],float('inf')) < config['minimum_type_support_seconds']:
            reasons.append('type_support_below_minimum:' + row['option_id'])
        if config.get('contextual_review') and (row.get('observation_consistency') != 'supports_facts' or row.get('reference_basis') == 'missing_reference'):
            reasons.append('missing_or_conflicting_factual_reference:' + row['option_id'])
        if row['verdict'] != 'supported' or row['confidence'] != 'high':
            reasons.append('gt_type_not_supported:' + row['option_id'])
        reasons.extend(evidence_errors(row['evidence_frame_ids'], event, media, config['minimum_evidence_span_seconds']))
        if not row['reason'].strip():
            reasons.append('empty_label_reason')
        if config.get('per_type_evidence') and row['verdict'] == 'supported':
            by_id = {f['frame_id']:f for f in media['sampled_frames']}
            ranges = event.get('type_intervals',{}).get(row['option_id'],[])
            if not ranges or any(not any(s['interval_frames'][0] <= by_id[fid]['source_frame_index'] < s['interval_frames'][1] for s in ranges) for fid in row['evidence_frame_ids'] if fid in by_id):
                reasons.append('evidence_outside_type_subinterval:' + row['option_id'])
    grounding=adjudication.get('action_grounding',{})
    grounded=bool(grounding and event.get('action_names') and grounding['verdict']=='matches' and grounding['confidence']=='high' and grounding['observation_consistency']=='supports_facts' and observation['confidence']=='high' and not evidence_errors(grounding['evidence_frame_ids'],event,media,config['minimum_evidence_span_seconds']) and not any(r['verdict']=='contradicted' for r in labels))
    if any(reason.startswith('type_support_below_minimum:') for reason in reasons):
        grounded=False
    return {'accepted': not reasons, 'annotation_backed_eligible':grounded, 'hold_reasons': sorted(set(reasons)), 'observation': observation, 'type_review': adjudication, 'media_path': media['path'], 'media_sha256': media['sha256']}
