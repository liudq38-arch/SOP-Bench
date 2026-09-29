import hashlib
from pathlib import Path

import av
import numpy as np
from PIL import ImageOps

from impact_qa.common import ANNOTATIONS, OUT, ROOT, fingerprint, read_json, save_json


FOLDER = OUT / 'atr_v19'
VIDEOS = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos')
KINDS = ['actual_action', 'actual_tool', 'tool_error', 'anomaly_type', 'observed_correction', 'expected_tool', 'timely_correction']


def interval(row, docs):
    fps = docs[row['video_id']]['meta_data']['fps']
    return row['start_frame'] / fps, (row['end_frame'] + 1) / fps


def iou(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0])) / (max(a[1], b[1]) - min(a[0], b[0]))


def source_ref(path, pointer, value, source_id):
    return {'source_id': source_id, 'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'pointer': pointer, 'value': value}


def context(row, doc):
    fps = doc['meta_data']['fps']
    start, end = row['start_frame'] / fps, (row['end_frame'] + 1) / fps
    path = ANNOTATIONS / 'TAS-B' / row['annotation_path']
    names = {x['id']: x['name'] for x in doc['action_labels']}
    nouns = {x['id']: x['name'] for x in doc['nouns']}
    facts = []
    for index, s in enumerate(doc['segments']):
        a, b = s['start_frame'] / fps, (s['end_frame'] + 1) / fps
        if b <= max(0, start - 3) or a >= end + 20:
            continue
        role = 'target' if min(b, end) > max(a, start) else 'before' if b <= start else 'after'
        if s['entity'] != row['entity'] and role != 'target':
            continue
        facts.append({'source_id': f'{row["view"]}_s{index}', 'role': role, 'hand': s['entity'], 'action': names[s['action_label']], 'noun': nouns.get(s['noun'], 'null'), 'phase': s['phase'], 'anomaly_labels': [x['name'] for x, flag in zip(doc['anomaly_types'], s['anomaly_type']) if flag], 'relative_start_s': round(a-start, 3), 'relative_end_s': round(b-start, 3), 'source': source_ref(path, f'/segments/{index}', s, f'{row["view"]}_s{index}')})
    return facts


def materialize(case):
    path = Path(case['source_video'])
    meta = case['metadata']
    start, end = case['interval_s']
    fps = meta['fps']
    duration = meta['num_frames'] / fps
    pre = np.linspace(max(0, start - 3), max(0, start - 1/fps), 4)
    target = np.linspace(start, max(start, end - 1/fps), 16)
    post = np.linspace(min(duration - 1/fps, end), min(duration - 1/fps, end + 20), 8)
    requested = [('before', float(t)) for t in pre] + [('target', float(t)) for t in target] + [('after', float(t)) for t in post]
    images = []
    with av.open(path) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        for i, (role, seconds) in enumerate(requested):
            dest = FOLDER / 'frames' / (fingerprint([str(path), path.stat().st_size, seconds, 'full_960_v1'])[:24] + '.jpg')
            record_path = dest.with_suffix('.json')
            if dest.exists() and record_path.exists():
                decoded = read_json(record_path)
            else:
                container.seek(max(0, int(seconds / float(stream.time_base))), stream=stream, backward=True)
                selected = None
                for frame in container.decode(stream):
                    pts = float(frame.pts * frame.time_base)
                    if pts >= seconds - .5/fps:
                        selected = frame
                        break
                if selected is None or abs(pts - seconds) > 1.6/fps:
                    raise ValueError('atr_media:pts_mismatch:' + case['case_id'])
                dest.parent.mkdir(parents=True, exist_ok=True)
                ImageOps.contain(selected.to_image(), (960, 540)).save(dest, quality=95)
                decoded = {'decoded_pts_s': pts}
                save_json(record_path, decoded)
            images.append({'evidence_id': f'f{i:02d}', 'path': str(dest), 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'requested_time_s': seconds, 'decoded_pts_s': decoded['decoded_pts_s'], 'relative_time_s': round(decoded['decoded_pts_s'] - start, 3), 'role': role, 'view': case['view'], 'time_scope': f'{role.upper()}; target interval {start:.3f}-{end:.3f}s. After frames are only a bounded follow-up, not proof of successful or timely correction.'})
    case['images'] = images
    case['image_manifest'] = [{k: im[k] for k in ['evidence_id', 'relative_time_s', 'role']} for im in images]
    return case


def validate_generation(result, case):
    if set(result) != {'items'} or not isinstance(result['items'], list) or len(result['items']) != len(KINDS):
        raise ValueError('atr_generate:items_schema')
    ids = {im['evidence_id'] for im in case['images']}
    sources = set(case['shared_gt']['allowed_source_ids'])
    if {q.get('kind') for q in result['items']} != set(KINDS):
        raise ValueError('atr_generate:kind_coverage')
    for q in result['items']:
        required = {'kind','answerable','question','answer','options','correct_option','source_ids','image_ids','evidence','grade','limitation'}
        if set(q) != required or type(q['answerable']) is not bool or type(q['grade']) is not int or q['grade'] not in range(4):
            raise ValueError('atr_generate:item_schema')
        if not all(isinstance(q[k],str) for k in ['question','answer','evidence','limitation']):
            raise ValueError('atr_generate:text_types')
        if not isinstance(q['source_ids'],list) or not isinstance(q['image_ids'],list) or not set(q['source_ids']) <= sources or not set(q['image_ids']) <= ids:
            raise ValueError('atr_generate:invalid_evidence_id')
        if q['answerable']:
            if q['kind'] in ['expected_tool','timely_correction']:
                raise ValueError('atr_generate:unsupported_normative_claim')
            if not q['source_ids'] or not q['image_ids'] or not q['question'] or not q['answer']:
                raise ValueError('atr_generate:missing_evidence')
            if not isinstance(q['options'],list) or len(q['options']) != 3 or not all(isinstance(o,str) and o for o in q['options']) or len(set(q['options']))!=3 or type(q['correct_option']) is not int or q['correct_option'] not in range(3):
                raise ValueError('atr_generate:options')
            if len(q['question'].split())>55 or len(q['answer'].split())>65:
                raise ValueError('atr_generate:public_length')
            if q['kind']=='observed_correction':
                evidence=[im for im in case['images'] if im['evidence_id'] in q['image_ids']]
                if not any(im['role']=='after' for im in evidence) or not any(im['role'] in ['target','before'] for im in evidence):
                    raise ValueError('atr_generate:missing_change_endpoints')
        elif q['options'] or q['correct_option'] is not None:
            raise ValueError('atr_generate:unanswerable_options')
    return result


def validate_reviews(result, expected, case, audit=False):
    if set(result) != {'items'} or not isinstance(result['items'],list) or len(result['items'])!=len(expected):
        raise ValueError('atr_review:items_schema')
    if {r.get('kind') for r in result['items']} != set(expected):
        raise ValueError('atr_review:coverage')
    ids={i['evidence_id'] for i in case['images']}
    for r in result['items']:
        if not isinstance(r.get('image_ids'),list) or not set(r['image_ids'])<=ids or type(r.get('grade')) is not int or r['grade'] not in range(4):
            raise ValueError('atr_review:evidence')
        if r['grade']==3 and not r['image_ids']:
            raise ValueError('atr_review:missing_image')
        if audit:
            for k in ['source_supported','visual_supported','blind_agrees','options_unique','scope_correct']:
                if type(r.get(k)) is not bool:raise ValueError('atr_audit:bool')
        elif not isinstance(r.get('answer'),str):
            raise ValueError('atr_blind:answer')
    return result
