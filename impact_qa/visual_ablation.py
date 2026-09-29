from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from .common import OUT, REPORTS, fingerprint, read_jsonl, save_json


FOLDER = OUT / 'gt_v13_inputs'
ROI = (300, 180, 1000, 710)
CONDITIONS = ['uniform_full', 'uniform_crop', 'dense_crop', 'dense_crop_manual']


def indices(c, dense=False):
    start, end = c['start_frame'], c['end_frame_inclusive']
    if not dense:
        return np.linspace(start, end, 16).round().astype(int).tolist()
    if c['kind'] == 'observed_order':
        numbers = [n + offset for n in c['facts']['first_onsets'] for offset in [0, 8, 15, 30, 45, 60, 75, 90]]
        return sorted(int(np.clip(n, start, end)) for n in numbers)
    if c['kind'] in ['component_installed', 'component_unassembled', 'ongoing_step']:
        start = max(start, end - 90)
    else:
        start, end = c['facts'].get('target_interval', [start, end])
        start, end = max(start, c['start_frame']), min(end, c['end_frame_inclusive'])
    return np.linspace(start, end, 16).round().astype(int).tolist()


def select():
    contracts = read_jsonl(OUT / 'gt_v12_2_inputs/contracts.jsonl')
    ids = {r['contract_id'] for r in read_jsonl(OUT / 'gt_v12_final/gt_visual_disagreements.jsonl')}
    selected = {c['contract_id']: dict(c, selection_reason='v12_gt_visual_disagreement') for c in contracts if c['contract_id'] in ids}
    for kind in sorted({c['kind'] for c in contracts}):
        available = sorted([c for c in contracts if c['kind'] == kind and c['contract_id'] not in selected], key=lambda c: fingerprint(c['contract_id']))
        for c in available[:2]:
            selected[c['contract_id']] = dict(c, selection_reason='fixed_hash_stratified_control')
    for attr in ['timing', 'spatial', 'object-handling', 'wrong-part', 'wrong-tool', 'procedural']:
        if not any(attr in c['facts'].get('error_attributes', []) for c in selected.values()):
            c = next(c for c in contracts if attr in c['facts'].get('error_attributes', []) and c['contract_id'] not in selected)
            selected[c['contract_id']] = dict(c, selection_reason='anomaly_attribute_coverage')
    for kind, count in [('action_error_category', 6), ('action_phase', 4)]:
        for c in contracts:
            if sum(x['kind'] == kind for x in selected.values()) >= count:
                break
            if c['kind'] == kind and c['contract_id'] not in selected:
                selected[c['contract_id']] = dict(c, selection_reason='additional_action_visibility_diagnostic')
    drivers = sorted([c for c in contracts if c['kind'] == 'tool_identity' and 'screwdriver' in c['facts']['action']], key=lambda c: fingerprint(c['contract_id']))
    for c in drivers[:2]:
        if c['contract_id'] not in selected:
            selected[c['contract_id']] = dict(c, selection_reason='screwdriver_control_against_wrench_only_bias')
    return sorted(selected.values(), key=lambda c: (c['video_id'], c['start_frame'], c['contract_id']))


def render(frame, crop):
    if crop:
        frame = frame.crop(ROI)
    return ImageOps.pad(frame, (640, 448), color='white')


def frame_path(video, number, variant):
    return FOLDER / 'frames' / (fingerprint([video, number, variant, ROI if variant == 'crop' else None])[:24] + '.jpg')


def manual_refs():
    refs = []
    source_ids = [0, 17, 19, 21, 23, 24]
    for index in range(2):
        board = Image.new('RGB', (1200, 448), 'white')
        draw = ImageDraw.Draw(board)
        for j, number in enumerate(source_ids[index * 3:index * 3 + 3]):
            source = REPORTS / f'manual_book_embedded_{number}.png'
            im = Image.open(source).convert('RGBA')
            bg = Image.new('RGBA', im.size, 'white')
            bg.alpha_composite(im)
            im = bg.convert('RGB')
            from PIL import ImageChops
            bbox = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).getbbox()
            if bbox:
                im = im.crop(bbox)
            im = ImageOps.contain(im, (390, 410))
            board.paste(im, (j * 400 + (400 - im.width) // 2, 28 + (410 - im.height) // 2))
            draw.text((j * 400 + 8, 5), f'Official manual image {number}; reference only', fill='black')
        path = FOLDER / f'manual_reference_{index}.jpg'
        path.parent.mkdir(parents=True, exist_ok=True)
        board.save(path, quality=95)
        refs.append({'evidence_id': f'generic_manual_reference_{index}', 'path': str(path), 'requested_time_s': 0, 'time_scope': 'REFERENCE ONLY. Not this execution. Timestamp is a placeholder, not an event time. No assigned component-name mapping.', 'view': 'official_manual_reference'})
    save_json(FOLDER / 'manual_provenance.json', {'source_svg': 'sources/impact_docs/Manual_Book.svg', 'embedded_image_indices': source_ids, 'names_assigned': False, 'same_references_for_every_case': True, 'mapping_limitation': 'No authoritative image-to-component name labels established; do not invent them.'})
    return refs


def evidence(c, condition, references):
    dense = condition.startswith('dense')
    crop = condition != 'uniform_full'
    context = np.linspace(c['start_frame'], c['end_frame_inclusive'], 4).round().astype(int).tolist()
    refs = []
    for i, n in enumerate(context):
        refs.append({'evidence_id': f'context_{i}', 'path': str(frame_path(c['video_id'], n, 'context')), 'requested_time_s': n / 30, 'frame_index': n, 'time_scope': 'Original recording time. Full-frame context; not a second execution.', 'view': 'front'})
    for i, n in enumerate(indices(c, dense)):
        refs.append({'evidence_id': f'target_{i}', 'path': str(frame_path(c['video_id'], n, 'crop' if crop else 'full')), 'requested_time_s': n / 30, 'frame_index': n, 'time_scope': 'Original recording time. Target evidence. ' + ('Fixed spatial crop of same recording.' if crop else 'Full frame.'), 'view': 'front'})
    if condition.endswith('manual'):
        refs += references
    return refs
