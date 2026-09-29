import concurrent.futures
import hashlib
import subprocess
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

from .common import ANNOTATIONS, FFMPEG, OUT, ROOT, fingerprint, read_json, save_json
from .gt_qa import reference, state_fact, verify_reference
from .state_qa import FRONT, STEPS


FOLDER = OUT / 'gt_v12_inputs'
ATTRIBUTES = ['timing', 'spatial', 'object-handling', 'wrong-part', 'wrong-tool', 'procedural']


def natural(label):
    return label.replace('_', ' ').replace('anti vibration', 'anti-vibration')


def contracts_for_video(video, procedure, trial_index):
    asr_path = ANNOTATIONS / 'ASR/annotations' / (video + '_asr.json')
    coarse_path = ANNOTATIONS / 'TAS-S/front' / (video + '.json')
    atomic_path = ANNOTATIONS / 'TAS-B/front' / (video + '.json')
    asr, coarse, atomic = map(read_json, [asr_path, coarse_path, atomic_path])
    components = [c['name'] for c in asr['components']]
    names = {r['id']: r['name'] for r in atomic['action_labels']}
    name_indices = {r['id']: i for i, r in enumerate(atomic['action_labels'])}
    total = asr['frame_count']
    rows, skips = [], []

    def add(kind, start, end, facts, refs, q, answer, choices, mcq, polarity='descriptive'):
        start, end = max(0, int(start)), min(total - 1, int(end))
        assert start < end
        assert len(choices) == len(set(choices)) == 3
        c = {'contract_id': 'gt_' + fingerprint([video, kind, facts])[:20], 'video_id': video, 'kind': kind, 'view': 'front', 'fps': 30, 'start_frame': start, 'end_frame_inclusive': end, 'source_video': str(FRONT / (video + '.mp4')), 'public_procedure': procedure, 'facts': facts, 'references': refs, 'question_proposition': q, 'canonical_answer': answer, 'answer_polarity': polarity, 'choice_texts': choices, 'correct_choice_index': 0, 'mcq_question_proposition': mcq, 'forbidden_claims': ['A unique mandatory order inferred from illustration', 'An operator mistake inferred from ASR=-1', 'Unsourced cause, correction, receiver, torque or fine alignment', 'Dropping any GT anomaly attribute from a multi-label answer'], 'human_review_status': 'pending_human_review', 'development_only': True}
        c['contract_hash'] = fingerprint(c)
        rows.append(c)

    stage_actions = {s[0]: s[2][0] for s in STEPS}
    found = {}
    for stage, component in [('adapter', 'adapter_plate'), ('handle', 'anti_vibration_handle')]:
        ci = components.index(component)
        states = [(i, s) for i, s in enumerate(asr['state_sequence']) if s['state'][ci] == 1]
        if not states:
            skips.append({'kind': 'component_installed', 'reason': 'no_state_1:' + component})
            continue
        si, state = states[0]
        end = min(state['frame'] + 15, asr['state_sequence'][si + 1]['frame'] - 1 if si + 1 < len(asr['state_sequence']) else total - 1)
        candidates = [(i, s) for i, s in enumerate(coarse['segments']) if s['label'] == stage_actions[stage] and s['f_start'] <= end]
        if not candidates:
            skips.append({'kind': 'component_installed', 'reason': 'missing_action:' + component})
            continue
        ai, action = candidates[-1]
        start = max(action['f_start'] - 15, end - 600)
        fact = state_fact(video, component, end)
        found[stage] = (start, end)
        add('component_installed', start, end, {'component_state': {k: v for k, v in fact.items() if k != 'references'}, 'scope': 'component state at cutoff; no larger assembly or receiver'}, fact['references'] + [reference(coarse_path, f'/segments/{ai}')], f'Had I correctly installed the {natural(component)} by the end of this clip?', f'Yes, the {natural(component)} was correctly installed by the end of the clip.', ['Correctly installed.', 'Not installed.', 'Incorrectly installed.'], f'What was the installation status of the {natural(component)} at the end of this clip?', 'yes')

    if 'adapter' in found:
        start, end = found['adapter']
        fact = state_fact(video, 'bearing_plate', end)
        if fact['state'] == 0:
            add('component_unassembled', start, end, {'component_state': {k: v for k, v in fact.items() if k != 'references'}}, fact['references'], 'Had I installed the bearing plate by the end of this clip?', 'No, the bearing plate had not been installed by the end of the clip.', ['Not installed.', 'Correctly installed.', 'Incorrectly installed.'], 'What was the installation status of the bearing plate at the end of this clip?', 'no')
        else:
            skips.append({'kind': 'component_unassembled', 'reason': 'bearing_not_state0_at_adapter_endpoint'})

    ci = components.index('bearing_plate')
    for si, s in enumerate(asr['state_sequence']):
        if s['state'][ci] != -1:
            continue
        end = min(s['frame'] + 15, asr['state_sequence'][si + 1]['frame'] - 1 if si + 1 < len(asr['state_sequence']) else total - 1)
        active = [(i, a) for i, a in enumerate(coarse['segments']) if a['label'] == 'insert_bearing_plate_assembly' and a['f_start'] <= end < a['f_end']]
        if not active:
            continue
        ai, action = active[0]
        fact = state_fact(video, 'bearing_plate', end)
        add('ongoing_step', max(action['f_start'], end - 180), end, {'component_state': {k: v for k, v in fact.items() if k != 'references'}, 'action': action['label'], 'endpoint_inside_action_interval': True, 'scope': 'ongoing step; no operator-error inference'}, fact['references'] + [reference(coarse_path, f'/segments/{ai}')], 'Had I finished installing the bearing plate by the end of this clip?', 'No, I was still working on installing the bearing plate when the clip ended.', ['Installation was still in progress.', 'Installation had not started.', 'Installation was complete.'], 'How far had I got with installing the bearing plate when this clip ended?', 'no')
        break
    else:
        skips.append({'kind': 'ongoing_step', 'reason': 'no_state_minus1_inside_bearing_action'})

    pairs = [('rotor', 'adapter'), ('adapter', 'bearing'), ('lever', 'handle')]
    for k, (a, b) in enumerate(pairs):
        first = next(((i, s) for i, s in enumerate(coarse['segments']) if s['label'] == stage_actions[a]), None)
        second = next(((i, s) for i, s in enumerate(coarse['segments']) if s['label'] == stage_actions[b]), None)
        if first is None or second is None:
            skips.append({'kind': 'observed_order', 'reason': 'missing_step:' + a + ':' + b})
            continue
        actual = sorted([first, second], key=lambda item: item[1]['f_start'])
        if actual[0][1]['f_end'] >= actual[1][1]['f_start']:
            skips.append({'kind': 'observed_order', 'reason': 'overlapping_first_action_intervals'})
            continue
        x, y = [natural(item[1]['label']) for item in actual]
        form = (trial_index + k) % 3
        if form == 0:
            q, answer, polarity = f'Did I start the "{x}" step before the "{y}" step?', f'Yes, I started the {x} step first.', 'yes'
        elif form == 1:
            q, answer, polarity = f'Did I start the "{y}" step before the "{x}" step?', f'No, I started the {x} step before the {y} step.', 'no'
        else:
            q, answer, polarity = f'Which step did I start first: "{x}" or "{y}"?', f'I started the {x} step first.', 'descriptive'
        add('observed_order', actual[0][1]['f_start'], min(actual[1][1]['f_end'], actual[1][1]['f_start'] + 90), {'first_action': actual[0][1]['label'], 'second_action': actual[1][1]['label'], 'first_onsets': [item[1]['f_start'] for item in actual], 'scope': 'first observed starts within the clip, not completion or mandatory ordering'}, [reference(coarse_path, f'/segments/{i}') for i, _ in actual], q, answer, [f'The {x} step.', f'The {y} step.', 'Both steps started at the same time.'], f'Which step did I start first: "{x}" or "{y}"?', polarity)

    tools = []
    for i, s in enumerate(atomic['segments']):
        label = names[s['action_label']]
        if s['phase'] == 'normal' and label.startswith('pick_up_') and s['end_frame'] - s['start_frame'] >= 15 and ('screwdriver' in label or 'wrench' in label):
            tool = 'screwdriver' if 'screwdriver' in label else 'wrench'
            tools.append((tool, i, s))
    selected = []
    for tool in ['wrench', 'screwdriver']:
        options = [item for item in tools if item[0] == tool]
        if options:
            selected.append(options[0])
    if len(selected) < 2:
        selected += [item for item in tools if item not in selected][:2 - len(selected)]
    for tool, i, s in selected:
        hand = s['entity']
        q = f'Which tool did I pick up with my {hand} hand in this clip?'
        choices = [f'A {tool}.'] + [x for x in ['A screwdriver.', 'A wrench.', 'A pair of pliers.'] if x != f'A {tool}.']
        add('tool_identity', s['start_frame'] - 15, s['end_frame'] + 15, {'action': names[s['action_label']], 'hand': hand, 'target_interval': [s['start_frame'], s['end_frame']], 'scope': 'generic tool category entailed by GT; not tool-tip subtype or tool appropriateness'}, [reference(atomic_path, f'/segments/{i}'), reference(atomic_path, f'/action_labels/{name_indices[s["action_label"]]}')], q, f'I picked up a {tool} with my {hand} hand.', choices, q)

    anomalies = [(i, s) for i, s in enumerate(atomic['segments']) if s['phase'] == 'anomaly' and s['action_label'] != 0 and any(s['anomaly_type']) and 15 <= s['end_frame'] - s['start_frame'] <= 900]
    anomalies.sort(key=lambda item: (-sum(item[1]['anomaly_type'][3:]), -item[1]['anomaly_type'][2], item[0]))
    used = set()
    for i, s in anomalies:
        signature = tuple(s['anomaly_type'])
        if signature in used:
            continue
        used.add(signature)
        attrs = [name for name, present in zip(ATTRIBUTES, s['anomaly_type']) if present]
        answer = 'The action had ' + ' and '.join(attrs) + (' errors.' if len(attrs) > 1 else ' error.')
        all_sets = [tuple(attrs), ('wrong-tool',), ('wrong-part',), ('timing',), ('spatial',), ('object-handling',), ('procedural',)]
        unique = list(dict.fromkeys(all_sets))[:3]
        choices = [' and '.join(a) + (' errors.' if len(a) > 1 else ' error.') for a in unique]
        action = natural(names[s['action_label']])
        q = f'What type or types of error occurred during my {hand_name(s)} "{action}" action?'
        add('action_error_category', s['start_frame'] - 15, s['end_frame'] + 15, {'action': names[s['action_label']], 'hand': s['entity'], 'phase': s['phase'], 'error_attributes': attrs, 'target_interval': [s['start_frame'], s['end_frame']], 'error_mechanism': None, 'scope': 'all source ATR attributes for this hand/action only; no physical mechanism inferred'}, [reference(atomic_path, f'/segments/{i}'), reference(atomic_path, f'/action_labels/{name_indices[s["action_label"]]}'), reference(atomic_path, '/anomaly_types')], q, answer, choices, q)
        if len(used) >= 2:
            break
    normal = next(((i, s) for i, s in enumerate(atomic['segments']) if s['phase'] == 'normal' and s['action_label'] != 0 and 30 <= s['end_frame'] - s['start_frame'] <= 240 and any(w in names[s['action_label']] for w in ['tighten', 'mount', 'insert'])), None)
    if normal:
        i, s = normal
        action = natural(names[s['action_label']])
        q = f'Did I make an error during my {hand_name(s)} "{action}" action in this clip?'
        add('action_phase', s['start_frame'], s['end_frame'], {'action': names[s['action_label']], 'hand': s['entity'], 'phase': 'normal', 'scope': 'this hand and action only; no whole-step or whole-video correctness'}, [reference(atomic_path, f'/segments/{i}'), reference(atomic_path, f'/action_labels/{name_indices[s["action_label"]]}')], q, 'No, that action was performed normally.', ['The action was normal.', 'The action contained an error.', 'The action was a recovery.'], f'Was my {hand_name(s)} "{action}" action normal, an error, or a recovery?', 'no')
    for c in rows:
        for ref in c['references']:
            verify_reference(ref)
    return rows, skips


def hand_name(segment):
    return segment['entity'] + '-hand'


def prepare_media_for_video(video, contracts):
    asr = read_json(ANNOTATIONS / 'ASR/annotations' / (video + '_asr.json'))
    source = FRONT / (video + '.mp4')
    wanted = {}
    for c in contracts:
        indices = np.linspace(c['start_frame'], c['end_frame_inclusive'], 8).round().astype(int).tolist()
        c['frame_indices'] = sorted(set(indices))
        for n in indices:
            wanted[n] = FOLDER / 'frames' / (fingerprint([video, n])[:24] + '.jpg')
    profile_path = FOLDER / 'profiles' / (video + '.json')
    missing = {n: path for n, path in wanted.items() if not path.exists()}
    if missing or not profile_path.exists():
        count, max_error = 0, 0.0
        with av.open(str(source)) as container:
            stream = container.streams.video[0]
            stream.thread_type = 'AUTO'
            codec, width, height, fps = stream.codec_context.name, stream.width, stream.height, float(stream.average_rate)
            for n, frame in enumerate(container.decode(video=0)):
                count += 1
                max_error = max(max_error, abs(float(frame.pts * frame.time_base) - n / 30))
                if n in missing:
                    missing[n].parent.mkdir(parents=True, exist_ok=True)
                    frame.to_image().save(missing[n], quality=94)
        assert count == asr['frame_count'] and max_error < 1e-5
        save_json(profile_path, {'video': video, 'codec': codec, 'width': width, 'height': height, 'fps': fps, 'frames': count, 'max_pts_error': max_error, 'file_bytes': source.stat().st_size})
    for c in contracts:
        refs = [{'evidence_id': f'frame_{n}', 'path': str(wanted[n]), 'requested_time_s': n / 30, 'frame_index': n, 'view': 'front', 'time_scope': 'within target cutoff'} for n in c['frame_indices']]
        c['audit_frame_refs'] = refs
        board = Image.new('RGB', (1600, 500), 'white')
        draw = ImageDraw.Draw(board)
        for j, ref in enumerate(refs):
            im = Image.open(ref['path']).convert('RGB')
            im.thumbnail((400, 225))
            x, y = j % 4 * 400, j // 4 * 250
            board.paste(im, (x, y + 22))
            draw.text((x + 3, y + 3), f'{ref["frame_index"]} | {ref["requested_time_s"]:.3f}s', fill='black')
        c['contact_sheet'] = str(FOLDER / (c['contract_id'] + '.jpg'))
        board.save(c['contact_sheet'], quality=94)

    def make_clip(c):
        path = FOLDER / 'clips' / (fingerprint([video, c['start_frame'], c['end_frame_inclusive']])[:24] + '.mp4')
        path.parent.mkdir(parents=True, exist_ok=True)
        config = {'source_size': source.stat().st_size, 'source_mtime_ns': source.stat().st_mtime_ns, 'start': c['start_frame'], 'end': c['end_frame_inclusive'], 'crf': 20, 'width': 1024}
        manifest = path.with_suffix('.json')
        if not path.exists() or not manifest.exists() or read_json(manifest) != config:
            temporary = path.with_suffix('.partial.mp4')
            subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-threads', '1', '-ss', str(c['start_frame'] / 30), '-i', str(source), '-frames:v', str(c['end_frame_inclusive'] - c['start_frame'] + 1), '-vf', 'scale=1024:-2', '-an', '-c:v', 'libx264', '-threads', '1', '-preset', 'fast', '-crf', '20', '-movflags', '+faststart', '-y', str(temporary)], capture_output=True, check=True)
            temporary.replace(path)
            save_json(manifest, config)
        c['clip_path'] = str(path)
        anchors = [c['audit_frame_refs'][i] for i in [0, 2, 5, 7]]
        c['image_refs'] = [{'evidence_id': 'video:' + c['contract_id'], 'media_type': 'video', 'path': str(path), 'source_start_s': c['start_frame'] / 30, 'source_end_s': (c['end_frame_inclusive'] + 1) / 30, 'decoder_num_frames': 16, 'view': 'front'}] + anchors
        c['input_hash'] = fingerprint({k: v for k, v in c.items() if k != 'input_hash'})
        return c
    unique = {}
    for c in contracts:
        unique.setdefault((c['start_frame'], c['end_frame_inclusive']), c)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(make_clip, unique.values()))
    for c in contracts:
        if 'image_refs' not in c:
            make_clip(c)
    return contracts
