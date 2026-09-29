from bisect import bisect_right
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import ANNOTATIONS, read_json, read_jsonl, save_json, save_jsonl


REVIEWS = {
    'temporal': {
        'hand': 'left',
        'observation': '采样图中操作者拆下小件后仍保持夹持姿势，随后伸手到收纳盒区域。小件身份以TAS-B的lever为依据。',
        'supported_sequence': 'detach_lever正常→hold_lever异常14.7秒→store_lever正常；同期另一只手继续处理壳体、螺丝和弹簧。',
        'hypothesis': '可能涉及已拆部件未及时放回、占用手或动作时机，但没有官方逐段原因或规定存放时限。',
        'unknown': '延迟释放、等待、动作同步中哪一点触发Temporal，以及具体允许时长。',
    },
    'spatial': {
        'hand': 'right',
        'observation': '采样图中红黄柄改锥被移到工件旁的中央工作区，随后壳体被翻转。',
        'supported_sequence': 'remove_screw正常→place_phillips_screwdriver异常→flip_gearbox_housing_drive_shaft正常。',
        'hypothesis': '很可能与工具放置位置相关，但缺少允许/禁止放置区域的规则，不能断言位置坐标或危险后果。',
        'unknown': '指定工具区、放置方向或最终释放位置中的具体违规条件。',
    },
    'handling': {
        'hand': 'left',
        'observation': '采样图中一只手用细长金属工具接触壳体，另一只手在壳体/轴端调整；仅这些帧不能明确旋转方向、滑脱或受力。',
        'supported_sequence': 'hand_spin_drive_shaft被标Handling；同期另一只手align_tool和hold_combination_wrench为normal。',
        'hypothesis': '需要核对传动轴与螺母的相对运动、固定方式或转动方式；不能仅凭转轴就称抓握错误。',
        'unknown': '具体是转动方式、固定方式、方向还是其他操控问题。',
    },
    'wrong_part': {
        'hand': 'right',
        'observation': '采样图中双手共同处理黑色壳体及其开口/轴端附近的小件，没有清楚显示用另一个不同零件替换目标件。',
        'supported_sequence': '右手hand_spin_drive_shaft标Wrong part；同期左手tighten_M4_nut标normal。',
        'hypothesis': '可能涉及当前任务应操作的对象；不能把类别自动改写成拿错型号或装入错误零件。',
        'unknown': '哪一个具体部件不合适、应当操作/选用什么，以及GT是否存在局部歧义。',
    },
    'wrong_tool': {
        'hand': 'right',
        'observation': '采样帧1745/1781显示红黄柄改锥在工件处，1816显示移开，1852伸向另一工具，1887及之后改用黑蓝柄长改锥。工具子类由TAS-B解析。',
        'supported_sequence': 'pick_up_phillips_screwdriver→align_tool→loosen_screw均Wrong tool；store_phillips_screwdriver→pick_up_flat_head_screwdriver→align_tool为recovery；随后loosen_screw为normal。',
        'hypothesis': '本例的错误工具是十字改锥，随后换用一字改锥完成恢复并继续松螺丝；这是实例内GT与视觉支持的局部解释，不是所有B型螺丝的统一规则。',
        'unknown': '该螺丝的实例ID、螺钉槽口精确形状及为何十字尖端不适合，没有直接原因字段。',
    },
    'procedural': {
        'hand': 'right',
        'observation': '采样图中将板状总成靠向壳体、取开后再次放回，再伸手取小件并在壳体边缘操作；细小紧固件依赖GT命名。',
        'supported_sequence': 'adjust/seat_bearing_plate标Procedural，extract_bearing_plate为recovery；随后再次seat并pick_up/align/insert/hand_tighten_screw标Procedural，hand_loosen/remove_screw为recovery。',
        'hypothesis': '可确认有安装尝试与撤回纠正过程，尚不能确定违反了哪一个前置条件或遗漏了哪一步。',
        'unknown': '具体流程规则；反复尝试或返工本身不构成独立判据。',
    },
}


def row(document, index, source):
    segment = document['segments'][index]
    fps = document['meta_data']['fps']
    names = {x['id']: x['name'] for x in document['action_labels']}
    categories = document['anomaly_types']
    return {
        'action': names[segment['action_label']],
        'hand': segment['entity'],
        'phase': segment['phase'],
        'labels': [categories[j]['name'] for j, value in enumerate(segment['anomaly_type']) if value],
        'start_frame': segment['start_frame'],
        'end_frame_inclusive': segment['end_frame'],
        'interval_s_half_open': [segment['start_frame'] / fps, (segment['end_frame'] + 1) / fps],
        'source': str(source.relative_to(ROOT)),
        'pointer': f'/segments/{index}',
    }


def state_context(trial, a, b):
    source = ANNOTATIONS / 'ASR/annotations' / f'{trial}_front_asr.json'
    if not source.exists():
        return {'available': False}
    data = read_json(source)
    fps = data['fps']
    sequence = data['state_sequence']
    frames = [r['frame'] for r in sequence]
    names = [r['name'] for r in data['components']]
    start = bisect_right(frames, a * fps) - 1
    changes = []
    for i in range(max(1, start + 1), len(sequence)):
        current = sequence[i]
        if current['frame'] > b * fps:
            break
        previous = sequence[i - 1]['state']
        changes.append({
            'source_frame': current['frame'],
            'time_s': current['frame'] / fps,
            'pointer': f'/state_sequence/{i}',
            'actual_changes': [{'component': names[j], 'previous': previous[j], 'current': value} for j, value in enumerate(current['state']) if value != previous[j]],
        })
    return {
        'available': True,
        'source': str(source.relative_to(ROOT)),
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'state_at_context_start': dict(zip(names, sequence[start]['state'])) if start >= 0 else None,
        'changes_in_context': changes,
        'causal_annotation': False,
    }


def main():
    output = ROOT / 'reports/impact_qa/anomaly_taxonomy_audit'
    manifest = read_json(output / 'visual/manifest.json')
    assert len(manifest) == len(REVIEWS), 'anomaly_dossier:missing_visual_cases'
    print({'preflight': 'CPU annotation and sampled-frame provenance audit', 'cases': len(manifest)}, flush=True)
    dossiers = []
    for case in manifest:
        category = case['category']
        review = REVIEWS[category]
        source = ROOT / case['annotation']
        document = read_json(source)
        a, b = case['context_window_s']
        fps = document['meta_data']['fps']
        all_rows = [row(document, i, source) for i in range(len(document['segments']))]
        hand_rows = sorted([r for r in all_rows if r['hand'] == review['hand']], key=lambda r: r['start_frame'])
        selected = [i for i, r in enumerate(hand_rows) if f'error_{category}' in r['labels'] and r['start_frame'] < b * fps and r['end_frame_inclusive'] >= a * fps]
        assert selected, f'anomaly_dossier:no_target:{category}'
        targets = [hand_rows[i] for i in selected]
        context = hand_rows[max(0, selected[0] - 3):selected[-1] + 4]
        other_hand = [r for r in all_rows if r['hand'] != review['hand'] and r['start_frame'] < b * fps and r['end_frame_inclusive'] >= a * fps]
        for frame in case['source_frame_rows']:
            assert (ROOT / frame['original_frame']).is_file(), f'anomaly_dossier:missing_frame:{category}'
        dossiers.append({
            'category': f'error_{category}',
            'trial_id': case['trial_id'],
            'view': 'front',
            'target_hand': review['hand'],
            'context_window_s': [a, b],
            'TASB_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'target_actions': targets,
            'same_hand_context': context,
            'concurrent_other_hand': other_hand,
            'ASR_context': state_context(case['trial_id'], a, b),
            'sampled_frames': case['source_frame_rows'],
            'contact_sheet': case['sheet'],
            'reviewer': 'Codex direct sampled-frame inspection',
            'human_review': 'unreviewed',
            'review': review,
            'reason_status': 'case_specific_tool_switch_supported' if category == 'wrong_tool' else 'exact_cause_unconfirmed',
            'official_per_segment_reason': None,
            'formal_release': False,
        })
    save_jsonl(output / 'case_dossiers.jsonl', dossiers)
    audit = read_json(output / 'annotation_audit.json')
    action_rows = read_jsonl(output / 'front_anomaly_actions.jsonl')
    assert len(action_rows) == audit['totals']['anomalous_action_segments_front'], 'anomaly_dossier:count_mismatch'
    for cls in audit['classes']:
        assert cls['front_TASB_action_segments'] == sum(cls['name'] in r['labels'] for r in action_rows), f'anomaly_dossier:class_count:{cls["name"]}'
        assert cls['all_nonnull_actions_have_normal_examples'], f'anomaly_dossier:normal_comparison:{cls["name"]}'
    save_json(output / 'dossier_audit.json', {'cases': len(dossiers), 'sampled_frames_reviewed': sum(len(r['sampled_frames']) for r in dossiers), 'target_actions': sum(len(r['target_actions']) for r in dossiers), 'annotation_count_assertions': 'passed', 'human_review': 'unreviewed', 'model_requests': 0, 'formal_release': False})
    print({'cases': len(dossiers), 'output': str(output / 'case_dossiers.jsonl'), 'validation': 'passed'}, flush=True)


if __name__ == '__main__':
    main()
