# IMPACT 六类异常：判定依据核查

核查日期：2026-09-27。数据：本地 IMPACT v1.1；官方仓库固定提交 `4fed5faa5f05f7aece55712e458defa1f372b248`。本轮是资料、标注与采样帧审计，未运行新的VLM生成。帧图审查者为Codex，未冒充真人审核。

## 1. 可以确认的结论

**公开资料提供六类异常标签，但在本轮检查的论文、官方文档、ATR实现、图示、发布清单和已有issue中，没有找到六类异常的逐类操作判定手册，也没有每个异常片段的原因文字。** 因此，可以准确回答“哪个动作、哪只手、哪一时间段被标了什么类别”，但并非每条都能仅凭ATR恢复“为什么错、正确应怎么做”。这不是证明作者内部没有规则，而是公开可用证据的边界。

论文 §3.2 明确：**“Anomalies carry six non-exclusive type labels”**。分类可共存，不能把六类强制改成互斥单选。[论文](https://arxiv.org/html/2604.10409v1)；[本地正文源文件](../../../sources/impact_anomaly_audit_20260927/paper_source_text/sec/dataset.tex)。论文源包含 `\\iffalse` 旧稿块，本报告依据正式渲染正文，不使用旧稿统计。

官方ATR说明写出 **“All assets are generated from the canonical v1.1 bimanual annotations.”**；ATR不是独立撰写的错误原因说明，而是由双手原子动作标注派生的标签资产。[官方ATR说明](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/dataset/ATR/README.md)；[本地副本](../../../sources/impact_anomaly_audit_20260927/official/dataset__ATR__README.md)。

官方类别ID为0–5，顺序：Temporal、Spatial、Handling、Wrong part、Wrong tool、Procedural。我们QA里的A=Correct、B–G=六类，是本项目的选项映射；Correct不是官方第七个ATR标签。[官方mapping](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/dataset/ATR/mapping_ATR.txt)。

## 2. 原始标注包含和缺少什么

扫描560份TAS-B文件、67,492个原子动作段，另扫描Split1的ATR-L/R train/val/test共7,797条记录。五视角来自相同112次执行，不能当作560个独立实验。

| 层级 | 实际字段 | 没有的直接信息 |
|---|---|---|
| TAS-B segment | action_label、verb、noun、start_frame、end_frame、phase、anomaly_type、entity | 自然语言原因、违反规则ID、正确替代工具/部件、预期动作 |
| ATR segment | 时间帧、entity、六维labels及label_names、source_segment_count、source_action_labels/verbs/nouns、源文件及split/view信息 | 原因解释、错误与纠正动作的显式配对、正确操作规范 |
| ASR | 部件状态及变化；可作安装/拆卸状态依据 | 六种异常的逐段原因；状态为-1不自动指向某一种ATR类型 |
| PPR phase | normal、anomaly、recovery | recovery不是第七类异常；其动作与此前错误的因果配对仍需上下文 |

TAS-B的end_frame按闭区间保存，本报告秒区间使用 `[start_frame/fps, (end_frame+1)/fps)`。`null` 只表示没有有效动作类别，可能涉及不可见、背景或词表外行为，不能解释成“没有错误”。相邻ATR大区间的类别并集，也不表示每一类别持续覆盖整个区间。

## 3. 六类究竟对应哪些动作

以下“理解范围”是本项目的保守工作解释，**不是官方发布的逐类定义**。真实实例的标签与时间可核验；原因未确认的地方明确保留未知。

| 类别 | 建议理解范围及判定所需证据 | 本地真实单类GT实例 | 能确认到哪一步 |
|---|---|---|---|
| Temporal 时间/时机异常 | 操作发生时机、持续/等待或协调方面的问题。需要任务时机约束或完整前后文；没有公开“超过n秒即异常”的阈值，不能把所有顺序问题统一归入此类。 | TO08CO25_Disassembly_A_003，左手28.900–43.600s：`hold_lever`；前面正常拆下拨杆，后面正常存放。 | GT确认持续持有拨杆这一段为Temporal。可能是未及时放回/占用手，但具体触发条件未公开。同期右手持壳体35.6秒仍为normal，证明不能按时长一刀切。 |
| Spatial 空间异常 | 位置、朝向、摆放或几何关系不合适；需要知道应该放在哪里/朝哪边。 | NA07GE21_Disassembly_A_001，右手216.800–221.100s：`place_phillips_screwdriver`。 | 帧图可见将改锥移到中央工作区、工件旁；GT为Spatial。未取得指定工具区域规则，不能编造必须放入哪格或偏离多少厘米。 |
| Handling 操控异常 | 拿持、转动、固定、移动或操纵对象的方式存在问题；需要具体异常操控证据，不能把“徒手”“换抓握”视作充分条件。 | KI03AR28_Disassembly_B_005，左手130.867–146.633s：`hand_spin_drive_shaft`；右手同时对准/持有组合扳手为normal。 | 可确认异常落在左手转轴动作上；未确认是固定方式、转动方向、受力还是其他问题。不能无证据写“打滑/抓不稳”。 |
| Wrong part 错误部件/对象 | 当前操作涉及不合适的部件或对象；需要辨认实际对象与所需对象。**不能限定成拿错零件这一种表现。** | KI05KO01_Reassembly_A_003，右手32.967–39.867s：`hand_spin_drive_shaft`；左手同时`tighten_M4_nut`为normal。 | 标签落在转轴上，并非pick_up某个错误件。具体应操作哪个部件不明，需进一步确认，不能生成“拿错了某型号零件”的答案。 |
| Wrong tool 错误工具 | 对当前操作选用/使用不合适工具；需要实际工具、目标操作，以及替代工具或适配规则。 | KI03AR28_Disassembly_B_005，右手57.467–60.533s：拿十字改锥→对准→松螺丝；60.533–64.733s收回十字、拿一字、对准标recovery；64.733s起松螺丝标normal。 | **本例可以作明确局部解释：先选用十字改锥，随后改用一字改锥继续松螺丝。** GT工具名与帧图换工具行为一致；螺丝具体实例和槽口形状未确认，不向其他螺丝推广。 |
| Procedural 流程异常 | 当前步骤与适用前置条件/流程要求不符；需要可查验规范。是否遗漏、额外或顺序错误不能仅从类名决定。 | SS07EL13_Reassembly_A_001，右手127.967–130.967s调整/装入轴承板标异常，接着取出为recovery；137.067–147.467s再装板异常；149.000–155.300s取/对准/插入/手拧螺丝异常，接着松开取出为recovery。 | 可确认安装尝试与撤回纠正序列；不能仅凭这些动作断言漏装哪个部件。检查同期ASR也未找到足以直接指定唯一原因的状态变化。 |

六例各查看12张有源时间的采样帧，共72张；不是逐帧全视频人工审核。所有目标段、左右手上下文、ASR状态、GT pointer、SHA256和观察备注在 [case_dossiers.jsonl](case_dossiers.jsonl)，帧图在 [visual/manifest.json](visual/manifest.json)。Wrong tool实例的目标段3.067秒，只用于分类语义核查，不符合先前≥5秒的生产优先门槛。

### 数据分布对解释的限制

统计单位是front视角TAS-B原子动作段；多标签重复计入各类别。

| 类别 | 含该类的动作段 | 仅该类 | null动作段 | 常见非null动作（段数） |
|---|---:|---:|---:|---|
| Temporal | 939 | 634 | 424 | hold_gearbox_housing_drive_shaft 62；hold_gearbox_housing 18 |
| Spatial | 689 | 478 | 240 | place_torx_screwdriver 68；place_phillips_screwdriver 65；place_screw 45 |
| Handling | 332 | 212 | 76 | hand_spin_drive_shaft 96；hold_gearbox_housing_drive_shaft 27 |
| Wrong part | 44 | 9 | 0 | hand_spin_drive_shaft 10；hold_gearbox_housing_drive_shaft 4 |
| Wrong tool | 77 | 49 | 20 | align_tool 10；pick_up_phillips_screwdriver 9；pick_up_combination_wrench 7 |
| Procedural | 311 | 171 | 71 | extract_drive_shaft 12；adjust_bearing_plate 12；hold_gearbox_housing_drive_shaft 11 |

front共有1,944个含异常类型的原子段，其中391个多标签。**六类中每一个非null异常动作名，都能找到同名normal段。** 例如转轴Handling=96段，同名normal=3段；放十字改锥Spatial=65段，同名normal=7段。动作名可能是有用线索，但绝非充分异常判据。分布来自标注审计，不是对官方定义的反向证明。[统计](annotation_audit.json)；[30组异常/正常同动作对照](category_examples.jsonl)。

## 4. 必须修正的既有假设

1. **空握工具不能固定映射到Temporal或Handling。** 正常稳固、等待另一只手、转移过程也可能出现这种画面。TAS-B若标异常，可保留其类型；解释仍需说明实际发生什么、哪里违背已知要求。
2. **放回零件时还握着工具，不自动判错。** 必须分清是否影响摆放、是否是正常双手协作、是否已有具体对象/区域规范。它可能涉及多类，也可能normal。
3. **Spatial不只指零件装反。** 本地大量Spatial发生在放下改锥、螺丝、轴和扳手的动作中，工作区布置可能很重要，但未取得官方区域判定规则。
4. **Handling不等于“掉落/打滑”。** 本地最常见有效动作是转轴；旧prompt若强求明显滑脱会误缩窄类别。对确切原因无依据时应保留未知。
5. **Wrong part不只指物料选错；Wrong tool不等于徒手操作。** 当前数据中存在转轴标Wrong part、徒手松螺丝标Wrong tool的例子，同名正常动作也存在，需要上下文或原标注者解释边界。
6. **Temporal和Procedural的严格边界未查明。** 不把“顺序错误”从一个标签自动挪到另一个；若GT有多个标签，保持多个。
7. **procedure_graph.json不是完整专家规则书。** 官方代码按ASR事件共现与先后频次挖掘，配置明确写：**“Edges are robust prerequisites mined from data.”** 当前文件num_videos=92，min_confidence=0.9，102条边的目标全为recover_ok；因此不能直接用于所有安装/拆卸动作的强制先后判定，也不是B型的已验证完整规则。[官方图](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/tasks/PSR/gemini_3_1_pro/configs/procedure_graph.json)；[挖掘实现](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/tasks/PSR/gemini_3_1_pro/learn_procedure_graph.py)。

## 5. 对QA生成的直接调整

建议输入按以下内容组织，属于本项目后续工程设计，不是IMPACT官方流程：

1. 固定目标视角、左右手、时间范围和原生GT类型；保留稳定标签子区间及其原始ATR来源。
2. 提供目标动作序列、另一只手并行动作、前后正常和recovery动作。上下文时间与目标时间分开；回答“有没有更正”时视频必须实际覆盖更正过程。
3. 提供A/B适用的工具/部件背景；仅对已明确对象与步骤使用已核验适配关系。统计图只能作为线索。
4. VLM先描述可见对象、动作、接触和变化，再提出带证据的局部原因；不强迫六类都解释成预设错误模板。
5. 输出分开保存 `gt_labels`、`observed_actions`、`explanation_status`、`explanation`、`rule_sources`、`evidence_frames`、`unknowns`。没有具体原因字段就保存null，不伪装成GT-answer。
6. MCQ类型答案按GT保留；“为什么错/应该换成什么”的开放题仅在具体实例的参照和证据足够时生成。现有要求带可靠视觉原因的MCQ，原因未知时继续待审；不改成Correct，不以模型自信替代证据。

已准备独立参考prompt：[anomaly_taxonomy_reference_v1.txt](../../../prompts/impact_qa/anomaly_taxonomy_reference_v1.txt)。标明工作解释和非官方规则，尚未接入生产或声称带来质量提升。

仍缺少的核心信息：六类逐类标注指南、Temporal与Procedural边界、Spatial工作区规范、Handling操控准则，以及Wrong part特殊实例的原始判定备注。现有公开证据不足以补齐这些内容；本轮未向作者发消息。

## 6. 可复现与来源

- [统计脚本](../../../scripts/audit_impact_anomaly_taxonomy.py)：全量TAS-B字段与六类动作/正常对照，ATR字段及计数。
- [采样脚本](../../../scripts/inspect_impact_anomaly_examples.py)：六个上下文窗口、每个12帧；保存原始帧号/PTS与GT。
- [案例整理脚本](../../../scripts/build_impact_anomaly_case_dossier.py)：目标手、邻接动作、另一只手、真实ASR状态差分、直接帧图审查备注和断言。
- [案例核验结果](dossier_audit.json)：6例、72帧、15个目标原子段；来源、类别计数与正常对照断言通过；模型请求0。
- [标注SHA清单](annotation_source_manifest.json)；[官方源文件SHA清单](source_manifest.json)。
- 官方来源另包括 [Benchmark协议](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md)、[v1.1变更说明](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/CHANGELOG.md)、[标注图例](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/annotation_demo.svg)。本地资料快照位于 `sources/impact_anomaly_audit_20260927/`。浏览工具返回404后采用HTTP直接获取官方文件；网络故障不作“资料不存在”的证据。
