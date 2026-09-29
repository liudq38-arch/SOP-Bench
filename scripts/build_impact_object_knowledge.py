import hashlib
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.common import read_json, save_json
from impact_qa.v26_data import changes

ANNOTATIONS = ROOT / 'annotations/impact/IMPACT-v1.1/annotations'
CONFIG = ROOT / 'configs/impact_qa/object_knowledge_v2.json'
PROMPTS = ROOT / 'prompts/impact_qa'
REPORT = ROOT / 'reports/impact_qa/impact_object_knowledge.md'
AUDIT_DIR = ROOT / 'reports/impact_qa/object_knowledge'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate(payload):
    cochange = Counter()
    model_types = Counter()
    actual_names = Counter()
    vocabulary = Counter()
    tool_picks = defaultdict(Counter)
    marker_counts = Counter()
    b_lever_segments = []
    total_deltas = total_frames = raw_rows = 0
    source_files = []
    asr_ids = set()
    tas_ids = set()
    asr_names = set()
    nouns = set()
    for path in sorted((ANNOTATIONS / 'ASR/annotations').glob('*.json')):
        data = read_json(path)
        source_files.append(path)
        asr_ids.add(path.stem.removesuffix('_asr'))
        names = tuple(c['name'] for c in data['components'])
        vocabulary[names] += 1
        actual_names.update(names)
        asr_names.update(names)
        model_types[data['meta_data'].get('model_type', 'unknown')] += 1
        by_frame = defaultdict(set)
        deltas = changes(data)
        for delta in deltas:
            by_frame[delta['frame']].add(delta['component'])
        for group in by_frame.values():
            cochange.update(combinations(sorted(group), 2))
        total_deltas += len(deltas)
        total_frames += len(by_frame)
        raw_rows += len(data.get('state_changes', []))
    tools = {t['canonical_name'] for t in payload['tools']}
    for path in sorted((ANNOTATIONS / 'TAS-B/front').glob('*.json')):
        data = read_json(path)
        source_files.append(path)
        tas_ids.add(path.stem)
        marker = path.stem.split('_')[2]
        marker_counts[marker] += 1
        noun_map = {x['id']: x['name'] for x in data['nouns']}
        verb_map = {x['id']: x['name'] for x in data['verbs']}
        nouns.update(noun_map.values())
        for segment in data['segments']:
            noun = noun_map.get(segment['noun'])
            if noun in tools and verb_map.get(segment['verb']) == 'pick_up':
                tool_picks[(marker, noun)][segment['phase']] += 1
    for path in sorted((ANNOTATIONS / 'TAS-S/front').glob('*_B_*.json')):
        source_files.append(path)
        for i, segment in enumerate(read_json(path)['segments']):
            if 'locking_lever' in segment['label']:
                b_lever_segments.append({'file': str(path.relative_to(ROOT)), 'pointer': f'/segments/{i}', 'segment': segment})
    canonical = set(read_json(ANNOTATIONS / 'PSR/labels/component_names.json'))
    documented_asr = {x['id'] for g in payload['component_groups'] for x in g['instances']}
    legacy = {x['id'] for x in payload['legacy_asr_labels']}
    documented_nouns = tools | {g['canonical_name'] for g in payload['component_groups']} | {a['id'] for a in payload['annotation_aliases']}
    coverage = {
        'canonical_asr_instances': len(canonical),
        'raw_asr_names': len(asr_names),
        'tas_b_nouns': len(nouns),
        'missing_canonical_asr': sorted(canonical - documented_asr),
        'extra_canonical_asr': sorted(documented_asr - canonical),
        'unexplained_raw_asr': sorted(asr_names - documented_asr - legacy),
        'unexplained_tas_b_nouns': sorted(nouns - documented_nouns),
    }
    for name in ['missing_canonical_asr', 'extra_canonical_asr', 'unexplained_raw_asr', 'unexplained_tas_b_nouns']:
        if coverage[name]:
            raise ValueError(f'object_knowledge.coverage.{name}: {coverage[name]}')
    return {
        'asr_file_count': len(asr_ids),
        'asr_model_type_counts': dict(model_types),
        'tas_b_front_file_count': len(tas_ids),
        'filename_model_counts': dict(marker_counts),
        'a_files_without_asr': sorted(t for t in tas_ids - asr_ids if '_A_' in t),
        'asr_component_label_counts': dict(sorted(actual_names.items())),
        'asr_component_vocabularies': [{'count': count, 'components': list(names)} for names, count in vocabulary.most_common()],
        'state_delta_method': 'impact_qa.v26_data.changes: adjacent state_sequence vectors; initial state excluded',
        'actual_state_delta_count': total_deltas,
        'actual_state_change_frame_count': total_frames,
        'raw_state_changes_row_count_not_used_as_deltas': raw_rows,
        'pairwise_actual_cochange_counts': [{'components': list(pair), 'count': n} for pair, n in sorted(cochange.items())],
        'tool_pick_counts': [{'model_marker': model, 'tool': tool, 'phases': dict(phases), 'total': sum(phases.values())} for (model, tool), phases in sorted(tool_picks.items())],
        'b_locking_lever_step_occurrences': b_lever_segments,
        'coverage': coverage,
    }, source_files


def render_prompt(payload, model=None):
    lines = ['<impact_domain_reference>', 'PURPOSE', payload['purpose'], '', 'TOOLS']
    for tool in payload['tools']:
        lines.append(f"- {tool['canonical_name']} ({tool['name_en']}): {tool['appearance_en']} {tool['role_en']}")
    lines.extend(['', 'PARTS'])
    for group in payload['component_groups']:
        name = group['canonical_name']
        if model == 'B' and name in {'lever', 'spring', 'washer', 'M4_nut'}:
            continue
        ids = [x['id'] for x in group['instances']]
        identity = name if ids == [name] else f"{name}: {', '.join(ids)}"
        appearance, role = group['appearance_en'], group['role_en']
        if model == 'B' and name == 'screw':
            identity = 'screw'
            appearance = 'Threaded fasteners in the B housing/bearing-plate assembly.'
            role = 'Use B clip evidence to identify their receiver, tool and number. Do not import the five A ASR screw identities.'
        elif model == 'B' and name == 'adapter_plate':
            role = 'A locating/adapting ring shown at the other end of the B rotor assembly. Its exact retention must come from B-specific evidence.'
        elif model == 'B' and name == 'bearing_plate':
            role = 'Supports/locates the output spindle and closes the gear cavity. A checked B removal uses a flat-head screwdriver on its screws.'
        lines.append(f'- {identity}: {appearance} {role}')
    lines.extend(['', 'CONFIGURATION'])
    for variant in payload['model_variants']:
        if model is None or variant['marker'] == model:
            lines.append(f"- Model {variant['marker']} = {variant['product']}. {variant['reference_en']}")
    lines.extend(['', 'ANNOTATION NAMING'])
    for alias in payload['annotation_aliases']:
        if model == 'B' and alias['id'] == 'M4_nut':
            continue
        lines.append(f"- {alias['id']}: {alias['meaning_en']}")
    if model != 'B':
        lines.append('- Legacy screw_plate_* and screw_bevel_* ASR names occur in one file. Preserve their raw IDs and do not silently normalize them.')
    lines.extend(['', 'RULES'])
    lines.extend(f'{i}. {rule}' for i, rule in enumerate(payload['rules_en'], 1))
    lines.append('</impact_domain_reference>')
    return '\n'.join(lines) + '\n'


def render_report(payload):
    stats = payload['aggregation']
    lines = [
        '# IMPACT 工具、部件及 A/B 配置知识块', '',
        '已对照官方型号爆炸图、装配手册、全部 front TAS-B 词表、92 份 ASR，以及 34 张 GT 选取或型号核对视频帧。此文件用于背景识别和功能解释；本次没有开展加入知识块前后的 VLM 效果对照实验。', '',
        '## 主要结论与计数', '',
        '- 官方图为 12 类部件、4 类工具；Model-A 的 ASR 将其中五颗螺丝和两颗 M4 螺母区分位置，因此是 17 个组件实例。这两个计数口径一致。',
        '- 用户所说“小帮手”若指桌上银色短工具，对应小扳手，即 combination wrench；三个改锥分别是一字、十字、Torx 六瓣梅花。',
        '- 模型 A/B 是两种角磨机配置。图中的蓝色 A/B/C/D 则是四种工具编号，黑色字母又用于局部视图；三者不要混淆。',
        '- 所有精确物料、螺纹规格、扭矩、内部啮合和装配完成性，仍需逐 clip 证据；本文把功能解释与直接 GT 分开。', '',
        '![官方两型号与工具对比](object_knowledge/model_comparison.png)', '',
        '## 两种型号的差异', '',
        '| 项目 | Model A | Model B |', '|---|---|---|',
        '| 论文型号 | Fein CG15-125BL | Fein WSG7-115A |',
        '| 参考外观 | 黑色齿轮箱，较粗纹理手柄；转子中段较平整 | 银灰齿轮箱，较细手柄；可见转子及铜色换向器 |',
        '| 适配板位置 | 齿轮箱与转子进入端附近 | 官方图中位于转子另一端；视频中也可见在轴组件远端拿放 |',
        '| 适配板紧固关系 | 两颗长螺丝配两颗 M4 螺母，手册使用十字改锥 | 不能复制 A 的连接关系；官方图未单列这一对 M4 螺母 |',
        '| 拨杆组件 | 单列拨杆、弹簧、垫圈、拨杆螺丝 | 官方爆炸图未单列这组部件；不等于证明所有样本绝无相关机构 |',
        '| 轴承板工具 | 手册展示 Torx | 已核对 B 拆卸样例展示一字改锥 |',
        f"| 数据覆盖 | 论文 92；本地文件名 {stats['filename_model_counts']['A']}；ASR 92 | 论文 20；本地文件名 {stats['filename_model_counts']['B']}；ASR 0 |", '',
        '型号依据论文 §3.1；几何、颜色和配置差异依据官方爆炸图与保存的视频帧。没有引入未经核实的电机功率、砂轮直径或制造商零件号。', '',
        '## 工具名称、外观和用途', '',
        '| GT 名称／中文 | 外观线索 | 功能与已核对操作 |', '|---|---|---|'
    ]
    for item in payload['tools']:
        lines.append(f"| `{item['canonical_name']}` / {item['name_zh']} | {item['appearance_zh']} | {item['role_zh']} |")
    lines.extend(['', '工具颜色由官方图例明确对应，并以样例视频核对。颜色用于辅助定位；光照、遮挡或工具替换时，不能以颜色代替 GT 和批头判断。', '', '## 12 类部件：外观与功能', '', '| 编号／名称 | 外观 | 功能与边界 |', '|---|---|---|'])
    for item in sorted(payload['component_groups'], key=lambda x: x['figure_number']):
        lines.append(f"| {item['figure_number']} / `{item['canonical_name']}` / {item['name_zh']} | {item['appearance_zh']} | {item['role_zh']} |")
    lines.extend(['', '上述“定位、支撑、传递旋转、回位”等机械功能是基于图示结构的保守解释；每项在 JSON 中通过 role_evidence_kind 标明。未把这些功能当作额外 GT 标签。', '', '## 17 个 ASR 名称与紧固关系（A）', '', '| ASR ID | 中文名称 | 对应关系 |', '|---|---|---|'])
    for component in payload['components']:
        details = []
        if component.get('fastens'):
            details.append('涉及 ' + ', '.join(component['fastens']))
        if component.get('paired_nut_A'):
            details.append('配 ' + component['paired_nut_A'])
        if component.get('reference_tool_A'):
            details.append('A 手册工具 ' + component['reference_tool_A'])
        lines.append(f"| `{component['canonical_name']}` | {component['name_zh']} | {'；'.join(details) or component['group_name_zh']} |")
    lines.extend(['', '关键修正：M4_nut_plate_* 应读作“适配板相应位置的 M4 螺母”，不是另有两块“螺母板”；drive_shaft 与 bearing_plate 上的输出轴也不是同一身份。适配板是深色环形件，不能笼统写成金属平板。', '', '## 标注中的泛称、组合名与旧名', ''])
    for alias in payload['annotation_aliases']:
        lines.append(f"- `{alias['id']}`：{alias['meaning_zh']}")
    lines.append('- `screw_plate_topleft/lowright`、`screw_bevel_topleft/lowright` 仅见于 MA07LF04_Reassembly_A_001_front_asr.json；与规范索引 7–10 对应，但本次仅记录候选映射，不自动改名。')
    lines.extend(['', '## 核对样例与异常项', '', '| 样例 | 时间／GT 引用 | 可支持结论 |', '|---|---|---|',
        '| AL07EJ17_Reassembly_A_002 front/top | 30.53s；TAS-B /segments/66 为拿扳手，/segments/67 为随后拧螺母 | 扳手外观与实际使用；M4/M6 名称冲突需另审 |',
        '| 同一 A 视频 | 53.77s；front /segments/79 拿十字，/segments/80 拧螺丝 | 红黄十字工具及适配板阶段 |',
        '| 同一 A 视频 | 90.83s；front /segments/90 拿 Torx 后的上下文 | 绿黑工具识别；该帧本身不证明已拧紧 |',
        '| AL07EJ17_Disassembly_B_005 front/top | 26.97s；front /segments/38 拿一字，/segments/40 旋松螺丝；TAS-S extract_bearing_plate_assembly | B 的一字改锥及轴承板拆卸 |',
        '| MA07LF04_Reassembly_B_005 front/top | 139.97s、457.17s | B 轴承板、轴组件与适配板外观／位置；不是完成性证据 |',
        '| KE03ER16_Disassembly_A_001 front/top | 0s | 文件虽无 ASR，但黑壳外观符合参考 A；不能以计数差额改归 B |', ''])
    for issue in payload['known_issues']:
        lines.append(f"- `{issue['id']}`（{issue['status']}）：{issue['detail_zh']}")
    lines.extend(['', '## 全量离线核对', '',
        f"- 覆盖 {stats['tas_b_front_file_count']} 份 TAS-B/front、{stats['asr_file_count']} 份 ASR；19 个 TAS-B 名词、17 个规范 ASR 名称及 4 个旧名均有解释，未覆盖名称为 0。",
        f"- ASR 原始 state_changes 有 {stats['raw_state_changes_row_count_not_used_as_deltas']} 行；真实相邻向量差分为 {stats['actual_state_delta_count']} 个组件变化，分布于 {stats['actual_state_change_frame_count']} 个帧时刻。不能把原始行数直接当变化次数。",
        '- 同时变更是关联佐证，不是机械连接或顺序因果证明。精确频数和源文件 SHA256 保存在 object_knowledge/audit.json、source_manifest.json。', '',
        '工具 pick_up 次数（包括正常、异常、恢复；只描述标注分布，不能据频率判定正确工具）：', '',
        '| 模型 | 一字 | 十字 | Torx | 扳手 |', '|---|---|---|---|---|'
    ])
    pick = {(x['model_marker'], x['tool']): x['total'] for x in stats['tool_pick_counts']}
    for model in ['A', 'B']:
        lines.append('| ' + model + ' | ' + ' | '.join(str(pick.get((model, t), 0)) for t in ['flat_head_screwdriver', 'phillips_screwdriver', 'torx_screwdriver', 'combination_wrench']) + ' |')
    lines.extend(['', '## Prompt 文件与建议嵌入位置', '',
        '- `prompts/impact_qa/v28r_object_knowledge.txt`：完整可审阅知识块。',
        '- `prompts/impact_qa/v28r_object_knowledge_A.txt`、`_B.txt`：按型号裁剪的版本；B 不注入 A 的五颗 ASR 螺丝实例及拨杆/M4 组件组。',
        '- `prompts/impact_qa/v28r_object_knowledge.json`：逐部件、逐工具、证据来源、型号差异、未解决问题及汇总。',
        '- 推荐位置：任务说明与片段型号之后、逐 clip GT 和视频证据之前。来源/冲突记录保留在旁路元数据，模型只读取适用的知识块与当前 clip 证据。',
        '- 适用于选题、生成与复查共同的命名参考；异常分类仍需要 GT 时间区间和视觉证据，不能把空拿工具或放回部件时持工具直接定义为异常。',
        '- 此任务输出的是可复用资料；现有批量生成配置没有自动加入本知识块，也没有据此重生成已有 QA。效果提升尚未测量。', '',
        '## 一手来源与原文短摘', ''
    ])
    paper = payload['sources']['paper']
    for quote in paper['excerpts']:
        lines.append(f'- 论文原文：“{quote}”。[§3.1]({paper["url"]})')
    for key in ['official_figure', 'manual', 'psr_names']:
        source = payload['sources'][key]
        lines.append(f'- [{key}]({source["url"]})；本地 `{source["local_path"]}`。')
    lines.extend(['', '官方图以固定 commit 的 Git blob SHA1 验证，SHA256 写入知识 JSON；网络镜像只负责传输，图示内容来自官方仓库。视频样例的视角、时间戳、原始 GT 引用及图像 SHA256 保存在 visual_evidence.json。', ''])
    return '\n'.join(lines)


def main():
    payload = read_json(CONFIG)
    for source in payload['sources'].values():
        path = ROOT / source['local_path']
        source['sha256'] = digest(path)
        if source.get('git_blob_sha1'):
            data = path.read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if actual != source['git_blob_sha1']:
                raise ValueError(f'object_knowledge.source_checksum: {path}')
    payload['aggregation'], annotation_files = aggregate(payload)
    component_order = read_json(ANNOTATIONS / 'PSR/labels/component_names.json')
    components = {}
    for group in payload['component_groups']:
        for instance in group['instances']:
            record = dict(instance)
            record['canonical_name'] = record.pop('id')
            record['group'] = group['canonical_name']
            record['group_name_zh'] = group['name_zh']
            record.setdefault('name_en', group['name_en'])
            record['source_ids'] = group['source_ids']
            components[record['canonical_name']] = record
    payload['components'] = [dict(components[name], index=index) for index, name in enumerate(component_order)]
    payload['prompt_files'] = {}
    for model in [None, 'A', 'B']:
        suffix = '' if model is None else f'_{model}'
        path = PROMPTS / f'v28r_object_knowledge{suffix}.txt'
        text = render_prompt(payload, model)
        path.write_text(text)
        payload['prompt_files'][model or 'full'] = {'path': str(path.relative_to(ROOT)), 'words': len(text.split()), 'sha256': digest(path)}
    evidence = read_json(ROOT / payload['sources']['visual_samples']['local_path'])
    for frame in evidence:
        path = AUDIT_DIR / frame['image']
        if digest(path) != frame['sha256'] or not Path(frame['video']).exists():
            raise ValueError(f'object_knowledge.visual_evidence: {frame["image"]}')
        if frame.get('annotation'):
            document = read_json(ROOT / frame['annotation'])
            index = int(frame['annotation_pointer'].rsplit('/', 1)[1])
            if document['segments'][index] != frame['annotation_segment']:
                raise ValueError(f'object_knowledge.annotation_evidence: {frame["image"]}')
    payload['validation'] = {'status': 'passed', 'visual_frames': len(evidence), 'missing_vocab_items': 0, 'source_hashes_checked': True, 'vlm_effectiveness_tested': False}
    source_paths = sorted(set(annotation_files + [CONFIG] + [ROOT / s['local_path'] for s in payload['sources'].values()]))
    save_json(AUDIT_DIR / 'source_manifest.json', [{'path': str(p.relative_to(ROOT)), 'sha256': digest(p)} for p in source_paths])
    save_json(AUDIT_DIR / 'audit.json', {'validation': payload['validation'], 'aggregation': payload['aggregation'], 'prompt_files': payload['prompt_files']})
    save_json(PROMPTS / 'v28r_object_knowledge.json', payload)
    REPORT.write_text(render_report(payload))
    print(json.dumps({'report': str(REPORT), 'validation': payload['validation'], 'prompt_files': payload['prompt_files']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
