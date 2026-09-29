import asyncio
import hashlib
import math
import subprocess
import threading
from collections import Counter, defaultdict
from pathlib import Path

import av
from transformers.models.qwen3_vl.video_processing_qwen3_vl import smart_resize
from vllm.multimodal.media.image import ImageMediaIO
from vllm.multimodal.media.video import VideoMediaIO

from impact_qa.common import ANNOTATIONS, FFMPEG, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.event_v22 import TEXT, arr, choice, obj
from impact_qa.history_v23 import history_input, schema as history_schema


FOLDER = ROOT / 'outputs/impact_qa/batch_v25'
VIDEOS = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos')
CONFIG = dict(read_json(ROOT / 'configs/impact_qa/history_v23.json'), output_root=str(FOLDER.relative_to(ROOT)), workers=3, batch_size=128, max_interval_seconds=30, version='batch_v25_r1')
KINDS = ['step_completion', 'execution_correctness', 'error_understanding', 'observed_order']
VISUAL = ['supports_visible_outcome', 'cannot_independently_confirm', 'conflicts_with_gt']
_LOCKS = defaultdict(threading.Lock)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source(path, pointer, value, sid):
    return {'source_id': sid, 'source_path': str(path.relative_to(ROOT)), 'sha256': digest(path), 'pointer': pointer, 'value': value}


def fixed_mcq(target):
    if target['family'] != 'atr':
        return []
    labels = target['atr_labels']
    names = ['Temporal', 'Spatial', 'Handling', 'Wrong part', 'Wrong tool', 'Procedural']
    return [{'kind': 'correctness', 'question': 'How is the target-hand operation in this interval annotated?', 'options': ['Correct (no annotated anomaly in this scope)', 'Anomalous'], 'correct_option_indices': [int(any(labels))], 'source_ids': ['atr'], 'target_hand': target['target_hand']}, {'kind': 'anomaly_types', 'question': 'Which anomaly types are annotated for the target-hand operation? Select all that apply.', 'options': names, 'correct_option_indices': [i for i, value in enumerate(labels) if value], 'source_ids': ['atr'], 'target_hand': target['target_hand']}]


def make_manifest():
    candidates, deferred = [], []
    asr_train = set((ANNOTATIONS / 'ASR/splits/train.split1.bundle').read_text().split())
    for path in sorted((ANNOTATIONS / 'ASR/annotations').glob('*_asr.json')):
        doc = read_json(path)
        vid = path.name.removesuffix('_asr.json')
        if vid not in asr_train or doc['workflow'] != 'assemble':
            continue
        for ci, component in enumerate(doc['components']):
            previous = doc['state_sequence'][0]['state'][ci]
            for si, row in enumerate(doc['state_sequence'][1:], 1):
                value = row['state'][ci]
                if value == previous:
                    continue
                previous = value
                if value not in [-1, 1]:
                    continue
                frame = row['frame']
                next_frame = next((r['frame'] for r in doc['state_sequence'][si + 1:] if r['state'][ci] != value), doc['frame_count'])
                end = min(frame + round(doc['fps'] * 1.5), next_frame - 1, doc['frame_count'] - 1)
                start = max(0, frame - round(doc['fps'] * 8))
                if end - frame < round(doc['fps'] * .4):
                    deferred.append({'family': 'completion', 'video_id': vid, 'reason': 'end_state_too_short', 'frame': frame, 'component': component['name']})
                    continue
                sid = 'v25_asr_' + fingerprint([vid, component['name'], frame])[:16]
                candidates.append({'case_id': sid, 'family': 'completion', 'view': 'front', 'video_id': vid, 'fps': doc['fps'], 'annotation_frame_count': doc['frame_count'], 'start_frame': start, 'end_frame': end, 'component': component['name'], 'state_at_end': value, 'state_effective_frame': frame, 'source_catalog': [source(path, f'/state_sequence/{si}/state/{ci}', {'component': component['name'], 'state': value, 'effective_from_frame': frame, 'queried_frame': end}, 'asr_end')], 'split': 'ASR_train_split1'})
    for hand in ['L', 'R']:
        path = ANNOTATIONS / f'ATR/atr_segments_{hand}/train.split1.jsonl'
        for i, row in enumerate(read_jsonl(path)):
            if row['view'] not in ['ego', 'front']:
                continue
            doc = read_json(ANNOTATIONS / 'TAS-B' / row['annotation_path'])
            duration = row['num_frames'] / doc['meta_data']['fps']
            if not .5 <= duration <= CONFIG['max_interval_seconds']:
                deferred.append({'family': 'atr', 'video_id': row['video_id'], 'sample_id': row['sample_id'], 'reason': 'duration_outside_batch_scope', 'duration_s': duration})
                continue
            candidates.append({'case_id': 'v25_atr_' + fingerprint([hand, row['sample_id']])[:16], 'family': 'atr', 'view': row['view'], 'video_id': row['video_id'], 'fps': doc['meta_data']['fps'], 'annotation_frame_count': doc['meta_data']['num_frames'], 'start_frame': row['start_frame'], 'end_frame': row['end_frame'], 'target_hand': row['entity'], 'atr_labels': row['labels'], 'atr_label_names': row['label_names'], 'source_catalog': [source(path, f'/jsonl/{i}', row, 'atr')], 'split': 'ATR_train_split1'})
    groups = defaultdict(list)
    for target in candidates:
        video = VIDEOS / target['view'] / (target['video_id'] + '.mp4')
        if not video.exists():
            deferred.append({'case_id': target['case_id'], 'reason': 'missing_media', 'source_video': str(video)})
            continue
        target.update(source_video=str(video), source_stat={'size': video.stat().st_size, 'mtime_ns': video.stat().st_mtime_ns})
        key = (target['family'], target['view'], str(target.get('state_at_end', target.get('atr_label_names'))))
        groups[key].append(target)
    for values in groups.values():
        values.sort(key=lambda t: fingerprint(t['case_id']))
    by_family = defaultdict(list)
    while any(groups.values()):
        for key in sorted(groups):
            if groups[key]:
                by_family[key[0]].append(groups[key].pop())
    ordered = []
    for index in range(max(map(len, by_family.values()), default=0)):
        for family in ['completion', 'atr']:
            if index < len(by_family[family]):
                ordered.append(by_family[family][index])
    selected = ordered[:CONFIG['batch_size']]
    save_jsonl(FOLDER / 'all_eligible.jsonl', ordered)
    save_jsonl(FOLDER / 'manifest.jsonl', selected)
    save_jsonl(FOLDER / 'deferred.jsonl', deferred)
    save_jsonl(FOLDER / 'first10_inputs.jsonl', selected[:10])
    save_json(FOLDER / 'selection_summary.json', {'eligible': len(ordered), 'selected': len(selected), 'selected_families': dict(Counter(t['family'] for t in selected)), 'selected_views': dict(Counter(t['view'] for t in selected)), 'deferred': dict(Counter(t['reason'] for t in deferred)), 'train_only': True, 'batch_rule': 'round robin family/view/state or error-label combination, deterministic hash within groups'})
    return selected


def profile(target):
    key = fingerprint([target['source_video'], target['source_stat']])
    path = FOLDER / 'profiles' / (key + '.json')
    with _LOCKS[key]:
        if path.exists():
            return read_json(path)
        native = []
        with av.open(target['source_video']) as container:
            stream = container.streams.video[0]
            stream.thread_count = 2
            for frame in container.decode(stream):
                native.append(float(frame.pts * frame.time_base))
        if len(native) != target['annotation_frame_count'] or any(b <= a for a, b in zip(native, native[1:])):
            raise ValueError('batch_v25:source_frame_pts_mismatch')
        if target['family'] == 'completion' and max(abs(t - i / target['fps']) for i, t in enumerate(native)) > .002:
            raise ValueError('batch_v25:asr_frame_clock_mismatch')
        value = {'source_video': target['source_video'], 'source_stat': target['source_stat'], 'pts': native}
        save_json(path, value)
        return value


def encode(source_video, destination, start, end):
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix('.tmp.mp4')
    subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-threads', '2', '-i', str(source_video), '-vf', f'select=between(n\\,{start}\\,{end}),setpts=PTS-STARTPTS,scale=960:-2', '-frames:v', str(end - start + 1), '-an', '-fps_mode', 'vfr', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(temp)], check=True, capture_output=True, timeout=240)
    temp.replace(destination)


def media(path, pts, first_index):
    with av.open(path) as container:
        local = [float(f.pts * f.time_base) for f in container.decode(video=0)]
    if len(local) != len(pts) or max(abs(t - (p - pts[0])) for t, p in zip(local, pts)) > .002:
        raise ValueError('batch_v25:crop_frame_pts_mismatch:' + str(path))
    io = {'video_backend': 'opencv', 'fps': 8, 'num_frames': 64}
    images, meta = VideoMediaIO(ImageMediaIO(), **io).load_file(path)
    h, w = smart_resize(len(images), *images.shape[1:3], min_pixels=4096, max_pixels=16777216)
    frames = [{'frame_id': f'f{first_index + i:07d}', 'source_frame_index': first_index + i, 'source_pts_s': pts[i]} for i in meta['frames_indices']]
    return {'path': str(path), 'sha256': digest(path), 'sampled_frames': frames, 'media_io_kwargs': {'video': io}, 'mm_processor_kwargs': {'do_sample_frames': False, 'size': {'shortest_edge': 4096, 'longest_edge': 16777216}}, 'estimated_visual_tokens': math.ceil(len(images) / 2) * (h // 32) * (w // 32), 'processor_shape': [h, w]}


def prepare(target):
    folder = FOLDER / 'media' / target['case_id']
    cached = FOLDER / 'inputs' / (target['case_id'] + '.json')
    stat = Path(target['source_video']).stat()
    if {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns} != target['source_stat']:
        raise ValueError('batch_v25:source_changed')
    for item in target['source_catalog']:
        if digest(ROOT / item['source_path']) != item['sha256']:
            raise ValueError('batch_v25:annotation_changed')
    if cached.exists():
        old = read_json(cached)
        if old['target_hash'] != fingerprint(target) or any(digest(v['path']) != v['sha256'] for v in [old['video']] + [c['video'] for c in old['clips']]):
            raise ValueError('batch_v25:cached_media_changed')
        return old
    all_pts = profile(target)['pts']
    start, end = target['start_frame'], target['end_frame']
    pts = all_pts[start:end + 1]
    full = folder / 'full.mp4'
    encode(target['source_video'], full, start, end)
    video = media(full, pts, start)
    if target['family'] == 'completion' and video['sampled_frames'][-1]['source_frame_index'] < target['state_effective_frame']:
        raise ValueError('batch_v25:state_endpoint_not_sampled')
    clips = []
    lo = 0
    while lo < len(pts):
        hi = lo + 1
        while hi < len(pts) and pts[hi] - pts[lo] < 2:
            hi += 1
        a, b = lo, hi - 1
        while a and pts[lo] - pts[a - 1] <= .25:
            a -= 1
        while b + 1 < len(pts) and pts[b + 1] - pts[hi - 1] <= .25:
            b += 1
        path = folder / f'c{len(clips):03d}.mp4'
        encode(full, path, a, b)
        clips.append({'clip_id': target['case_id'] + f'_c{len(clips):03d}', 'core_interval_s': [pts[lo], pts[hi - 1]], 'video_start_source_pts_s': pts[a], 'video': media(path, pts[a:b + 1], start + a)})
        lo = hi
    sources = list(target['source_catalog'])
    tas_path = ANNOTATIONS / 'TAS-B' / target['view'] / (target['video_id'] + '.json')
    tas = read_json(tas_path)
    actions = {r['id']: r['name'] for r in tas['action_labels']}
    for i, row in enumerate(tas['segments']):
        if row['start_frame'] <= end and row['end_frame'] >= start and actions[row['action_label']] != 'null':
            value = dict(row, action_name=actions[row['action_label']], anomaly_names=[a['name'] for a, flag in zip(tas['anomaly_types'], row['anomaly_type']) if flag])
            sources.append(source(tas_path, f'/segments/{i}', value, f'atomic_{i}'))
    step_path = ANNOTATIONS / 'TAS-S' / target['view'] / (target['video_id'] + '.json')
    if step_path.exists():
        for i, row in enumerate(read_json(step_path)['segments']):
            if row['f_start'] <= end and row['f_end'] >= start and row['label'] != 'null':
                sources.append(source(step_path, f'/segments/{i}', {k: row[k] for k in ['label', 'f_start', 'f_end']}, f'step_{i}'))
    result = {'target_hash': fingerprint(target), 'target': dict(target, source_interval_s=[pts[0], pts[-1]], source_catalog=sources), 'video': video, 'clips': clips, 'fixed_mcq': fixed_mcq(target)}
    save_json(cached, result)
    return result


def qa_schema(packet, events):
    target = packet['target']
    kinds = ['step_completion'] if target['family'] == 'completion' else KINDS[1:]
    item = obj({'kind': choice(kinds), 'question': TEXT, 'answer': TEXT, 'verdict': choice(['yes', 'no', 'descriptive', 'unknown']), 'eligibility': choice(['candidate', 'needs_more_evidence']), 'source_ids': arr(choice([s['source_id'] for s in target['source_catalog']]), 1, 8), 'event_ids': arr(choice([e['event_id'] for e in events]), 1, 8), 'evidence_basis': TEXT, 'visual_support': choice(VISUAL), 'visual_limitation': TEXT})
    return obj({'items': arr(item, 1, 1 if target['family'] == 'completion' else 2)})


def validate(value, target):
    kinds = []
    for q in value['items']:
        kinds.append(q['kind'])
        public = (q['question'] + ' ' + q['answer']).lower()
        if any(s in public for s in ['annotat', 'ground truth', 'asr', 'error_wrong_', 'source_id', 'state label']) or any(s in q['question'].lower() for s in ['describe', 'summarize']):
            raise ValueError('batch_v25:public_prose_contract')
        if q['eligibility'] == 'candidate' and (q['verdict'] == 'unknown' or q['visual_support'] == 'conflicts_with_gt'):
            raise ValueError('batch_v25:eligibility_conflict')
        if target['family'] == 'completion':
            if q['kind'] != 'step_completion' or 'asr_end' not in q['source_ids'] or q['verdict'] != ('yes' if target['state_at_end'] == 1 else 'no'):
                raise ValueError('batch_v25:completion_gt_mismatch')
            if 'end' not in q['question'].lower():
                raise ValueError('batch_v25:completion_time_scope')
        elif q['kind'] in ['execution_correctness', 'error_understanding']:
            if 'atr' not in q['source_ids'] or not any(s.startswith('atomic_') for s in q['source_ids']):
                raise ValueError('batch_v25:missing_operation_source')
            if q['kind'] == 'execution_correctness' and q['verdict'] != 'no':
                raise ValueError('batch_v25:atr_polarity')
    if len(kinds) != len(set(kinds)):
        raise ValueError('batch_v25:duplicate_kind')


async def process(pool, target):
    case_id = target['case_id']
    path = FOLDER / 'results' / (case_id + '.json')
    output = {'case_id': case_id, 'family': target['family'], 'generation_revision': CONFIG['version'], 'status': 'running', 'formal_release': False, 'human_review': 'unreviewed', 'ledger': []}
    if path.exists():
        existing = read_json(path)
        if existing['status'] in ['completed', 'held']:
            stat = Path(target['source_video']).stat()
            if {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns} != target['source_stat'] or any(digest(ROOT / s['source_path']) != s['sha256'] for s in target['source_catalog']):
                raise ValueError('batch_v25:completed_source_changed')
            return existing
    save_json(path, output)
    try:
        packet = await asyncio.to_thread(prepare, target)
        output.update(video=packet['video']['path'], target=packet['target'], fixed_mcq=packet['fixed_mcq'])
        ledger = output['ledger']
        for clip in packet['clips']:
            previous = [e for row in ledger[-2:] for e in row['events']]
            payload = {'case_id': case_id, 'view': target['view'], 'clip_id': clip['clip_id'], 'core_source_interval_s': clip['core_interval_s'], 'video_start_source_pts_s': clip['video_start_source_pts_s'], 'sampling_source_pts_s': [f['source_pts_s'] for f in clip['video']['sampled_frames']], **history_input(ledger)}
            result = await pool.call('describe', (ROOT / 'prompts/impact_qa/v23/describe.txt').read_text(), payload, history_schema('describe', previous), 1536, video=clip['video'])
            value = result['result']
            events = [dict(e, event_id=clip['clip_id'] + f'_e{i}', source_interval_s=clip['core_interval_s']) for i, e in enumerate(value['events'])]
            ledger.append(dict(value, events=events, clip_id=clip['clip_id'], source_interval_s=clip['core_interval_s'], cache_key=result['cache_key']))
            save_json(path, output)
        events = [e for row in ledger for e in row['events']]
        payload = dict(packet['target'], clip_ledger=[{k: row[k] for k in ['clip_id', 'source_interval_s', 'description', 'events', 'uncertainties']} for row in ledger], sampling_source_pts_s=[f['source_pts_s'] for f in packet['video']['sampled_frames']])
        prompt = (ROOT / 'prompts/impact_qa/v25_generate.txt').read_text()
        try:
            result = await pool.call('generate', prompt, payload, qa_schema(packet, events), 3072, video=packet['video'], validator=lambda v: validate(v, packet['target']))
        except ValueError as exc:
            if 'batch_v25:' not in str(exc):
                raise
            output['repair_reason'] = str(exc)
            repair = prompt + '\nThe prior attempt failed the machine contract: ' + str(exc) + '. Generate a corrected answer. Preserve exact GT scope, cite the operation source, and place all annotation terminology only in evidence_basis. This is the only allowed repair attempt.'
            result = await pool.call('generate_repair', repair, payload, qa_schema(packet, events), 3072, video=packet['video'], validator=lambda v: validate(v, packet['target']))
        output['generated'] = result['result']
        output['generation_cache_key'] = result['cache_key']
        items = result['result']['items']
        review_schema = obj({'items': arr(obj({'item_index': {'type': 'integer', 'minimum': 0, 'maximum': len(items) - 1}, 'verdict': choice(['keep', 'hold']), 'reason': TEXT, 'visual_support': choice(VISUAL), 'evidence_ids': arr(choice([s['source_id'] for s in packet['target']['source_catalog']]), 1, 8)}), len(items), len(items))})
        def check_review(value):
            if sorted(r['item_index'] for r in value['items']) != list(range(len(items))):
                raise ValueError('batch_v25:review_coverage')
        reviewed = await pool.call('review', (ROOT / 'prompts/impact_qa/v25_review.txt').read_text(), dict(payload, candidates=items), review_schema, 2048, video=packet['video'], validator=check_review)
        output['review'] = reviewed['result']
        output['review_cache_key'] = reviewed['cache_key']
        decisions = {r['item_index']: r for r in reviewed['result']['items']}
        output['qa'] = {'items': [dict(q, review=decisions[i]) for i, q in enumerate(items) if q['eligibility'] == 'candidate' and decisions[i]['verdict'] == 'keep' and decisions[i]['visual_support'] != 'conflicts_with_gt']}
        output['held_items'] = [dict(q, review=decisions[i]) for i, q in enumerate(items) if not (q['eligibility'] == 'candidate' and decisions[i]['verdict'] == 'keep' and decisions[i]['visual_support'] != 'conflicts_with_gt')]
        output['status'] = 'completed' if output['qa']['items'] else 'held'
    except Exception as exc:
        output.update(status='error', error=f'{type(exc).__name__}:{exc}')
    save_json(path, output)
    print({'case_id': case_id, 'status': output['status'], 'qa': len(output.get('qa', {}).get('items', [])), 'error': output.get('error')}, flush=True)
    return output
