import copy

from .evidence_ids import normalize_evidence


def select_images(case, condition):
    images = case['image_refs']
    if condition == 'transition8':
        wanted = {'context_0', 'context_3'} | {f'target_{i}' for i in [0, 3, 6, 9, 12, 15]}
        images = [im for im in images if im['evidence_id'] in wanted]
        assert len(images) == 8, 'v15:missing_compact_frame'
    elif condition != 'chronological20':
        raise ValueError('v15:unknown_condition:' + condition)
    return sorted(copy.deepcopy(images), key=lambda im: (im['frame_index'], im['evidence_id']))


def validate(raw, images, condition):
    refs = {im['evidence_id']: im for im in images}
    if condition == 'chronological20':
        value, changes = normalize_evidence(raw, images)
        assert value['tool'] in ['screwdriver', 'wrench', 'pliers', 'unknown']
        assert value['answerability'] in ['answerable', 'uncertain']
        assert isinstance(value['pickup_visible'], bool)
        assert len(value['visible_evidence'].split()) <= 40
        answerable = value['answerability'] == 'answerable'
        if answerable:
            assert value['pickup_visible'] and value['tool'] != 'unknown'
    else:
        value = copy.deepcopy(raw)
        changes = []
        assert set(value) == {'tool', 'shape', 'before_image_id', 'before_state', 'after_image_id', 'after_state', 'observation'}
        assert value['tool'] in ['screwdriver', 'wrench', 'pliers', 'unknown']
        assert value['shape'] in ['handled_shaft', 'flat_wrench_body', 'hinged_handles', 'unclear']
        assert value['before_state'] in ['on_surface', 'grasping', 'already_held', 'unclear']
        assert value['after_state'] in ['held_away', 'on_surface', 'unclear']
        assert isinstance(value['observation'], str) and len(value['observation'].split()) <= 40
        for key in ['before_image_id', 'after_image_id']:
            if isinstance(value[key], str) and value[key].startswith('Frame ') and value[key][6:] in refs:
                changes.append({'field': key, 'raw': value[key], 'normalized': value[key][6:]})
                value[key] = value[key][6:]
            assert value[key] is None or value[key] in refs, 'v15:unknown_evidence_id'
        shapes = {'screwdriver': 'handled_shaft', 'wrench': 'flat_wrench_body', 'pliers': 'hinged_handles'}
        answerable = value['tool'] in shapes and value['shape'] == shapes[value['tool']] and value['before_state'] in ['on_surface', 'grasping'] and value['after_state'] == 'held_away'
    if answerable:
        assert value['before_image_id'] in refs and value['after_image_id'] in refs
        assert refs[value['before_image_id']]['frame_index'] < refs[value['after_image_id']]['frame_index'], 'v15:nonchronological_endpoints'
    return value, changes, answerable
