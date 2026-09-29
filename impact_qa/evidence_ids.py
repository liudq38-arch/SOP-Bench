import copy


def normalize_evidence(raw, refs):
    result = copy.deepcopy(raw)
    valid = {r['evidence_id'] for r in refs}
    changes = []

    def canonical(value):
        if value is None:
            return None
        if value in valid:
            return value
        normalized = value.removeprefix('Frame ') if isinstance(value, str) else value
        if normalized in valid:
            changes.append({'raw': value, 'canonical': normalized, 'rule': 'strip_literal_transport_prefix'})
            return normalized
        raise ValueError('evidence_ids:unknown:' + str(value))

    result['evidence_image_ids'] = [canonical(v) for v in raw['evidence_image_ids']]
    for key in ['before_image_id', 'after_image_id']:
        result[key] = canonical(raw.get(key))
        if result[key] is not None and result[key] not in result['evidence_image_ids']:
            changes.append({'field': key, 'canonical': result[key], 'rule': 'include_explicit_endpoint_in_evidence_union'})
            result['evidence_image_ids'].append(result[key])
    return result, changes
