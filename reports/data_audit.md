# 发布标注与复现边界核查

核查日期 2026-09-17。只读解析官方文件和代码；未更改原标签、训练模型或评估视频真实性。机器可读结果：[CC4D/EgoErrorVQA](annotation_validation.json)、[IMPACT](impact_validation.json)、[上游](upstream_validation.json)。

## A. EgoErrorVQA

官方提交：`5403cdd05e007b01c88448587c1a1803a27266e2`。完整 9 个 JSON 均通过 JSON 解析、文件长度和 Git blob SHA-1 校验，并记录 SHA-256。

| 问题 | 具体证据 | 使用时含义 |
|---|---|---|
| 片段时间无效 | CC4D OE 52/960、MCQ 53/1000；EPIC-Tent OE/MCQ 各 2 条 | 需明确漏步如何取上下文，保留 raw 文件，不静默丢弃 |
| 多标签真值 | CC4D MCQ 88 条有多个允许标签 | 当前 evaluator 任一匹配即正确 |
| 当前动作字段缺失 | EgoOops MCQ 的 40 条错误样本 `action_annotation=null` | 官方 prompt 的当前步骤可能是 None |
| 采题有随机性 | `green_agent/agent.py:685` 对每片段 `random.choice(qa_pairs)` | 单次运行覆盖 1,805 个片段问题，而非全部 3,560 对；需要固定策略和种子 |
| 度量不是标准多类/二类 Recall | 错误类别判错仅进入 FP，然后 Recall=TP/(TP+FN) | 必须保留作者指标名并另报标准指标，不能混作 benchmark 排名 |
| 文件数/论文数不同 | 发布 JSON 去重为 510 个源内 video ID，Table 1 写 800 | 800 的口径未解释；本次可复现的是 510 |
| 论文配置与示例实现不同 | 论文 max_new_tokens=256；white agent 示例 128；未找到 Ego-ADR 独立实现 | 能下载 evaluator 不等于方法完整复现 |

来源：[论文](https://arxiv.org/html/2608.24134v1)、[官方代码](https://github.com/z1oong/EgoErrorVQA/blob/5403cdd05e007b01c88448587c1a1803a27266e2/src/green_agent/agent.py)。

**度量的具体例子（根据代码推导，不是实验结果）：** 三个真实错误，预测一个类别正确、一个错误类别、一个 `correct`，得到 TP=1、FP=1、FN=1，作者 Recall=1/2；标准“是否检出错误”的 Recall 应为 2/3，严格类别匹配召回为 1/3。三种数值表达不同含义。

**EPIC-Tent 可定位的时间转换问题：** 源动作表 subject 2、action 6 的 `00:01:02:46`→`00:01:03:10`，对应 GoPro frame 3763→3787，源帧索引递增。EgoErrorVQA 转为 63.533→63.333 秒，反而倒序；数值与把 timecode 最后一段除以 30 相符。上游说明各视频帧率不同。此处可确定派生区间有误，但未查看原视频，故不强行统一重写为 60fps。[EPIC-Tent 原标注](https://github.com/youngkyoonjang/EPIC_Tent2019/blob/1e784a97ca0a1669988a8ba05d0a73ad812a204a/Synchronised_action_label.txt)

重复 `(video_id,start,end)` 并不自动等于冗余数据：不同动作问题可能共享片段。实测 CC4D 每个任务文件有 7 次键重复；Tent OE 29、MCQ 28。将来建立样本主键应加入问题/动作索引。

## B. CC4D

官方提交：`a8a920a3293c4db27099a20ddbe3a3a9be1283e3`。当前目录与 `/home/ldq/sop_work/cc4d_annotations` 的全部非 Git 文件哈希一致；官方 HEAD 相同。

- 384 个 recording、5,700 条步骤；有标签错误步骤 1,964。
- 错误标签实例数是多标签计数：Preparation 410，Measurement 331，Technique 502，Timing 177，Temperature 66，Order 795，Missing 285，Other 8。**不能相加当作互斥错误步骤数。**
- 287 行负时间：281 行仅含 Missing Step，另 6 行无错误标签。非负区间未发现 end < start。
- `Missing Step` 的 285 个标签实例并不全部使用负时间，不能仅通过时间判定所有漏步。
- 53 个录制有重复 step ID；step ID 非录制内唯一 occurrence ID。
- 两个 recipe split 文件 train/val/test 全空；其余划分没有 recording ID 交叉或未知 ID。
- 官方文档展示的 `complete_step_annotations.json` schema 与实际文件不同：真实字段是 `steps`，不是示例中的 `step_annotations`。
- 论文 5.3K 与文件 5,700 行，以及论文正常/错误 173/211 与文件 164/220 的差别未获确定解释，不擅自修改计数。

来源：[官方标注](https://github.com/CaptainCook4D/annotations/tree/a8a920a3293c4db27099a20ddbe3a3a9be1283e3)、[正式论文](https://proceedings.neurips.cc/paper_files/paper/2024/file/f4a04396c2ed1342a5d8d05e94cb6101-Paper-Datasets_and_Benchmarks_Track.pdf)。

## C. IMPACT v1.1

ZIP SHA-256：`ded862b7599fa2bedbfa7699bf554add955a18d5c9ff641ef7826751fe791cfb`，与发布 SHA256SUMS 和 Hugging Face LFS oid 一致；ZIP CRC 全通过。解压后 1,777 个 JSON 均可解析。

### C.1 文件覆盖和有效性

| 类型 | 文件/样本实测 |
|---|---|
| TAS-S | 560 个 JSON = 112 trials × 5 views；21,995 段 |
| TAS-B | 560 个 JSON；67,492 段，左手 28,149、右手 39,343 |
| AF-S | 560 个派生 JSON；67,492 段 |
| ASR | **92** 个 front JSON，17 个部件，1,457 个状态事件；状态值 -1/0/1 |
| PSR | 51 项事件字典；64/10/18 records；含无错误/含错误等不同 CSV 版本 |
| NASA-TLX | `metadata/NASA_TLX_anonymized.xlsx` 已获取；本次只确认存在，未解释问卷分数 |

TAS-S/TAS-B/AF-S 的所有片段均满足 0 ≤ start ≤ end < num_frames，允许单帧片段，未发现越界。该检查不等于已核验视觉标注正确性。

TAS-B phase 的片段数为 normal 56,482、anomaly 9,512、recovery 1,498；论文 normal 数为 56,487。片段占比与帧占比不同：论文 §3.2 的 83.68% / 14.09% / 2.22% 对应片段计数比例，§5.5 却将 recovery 2.22% 称为 frames。当前文件跨视角、跨手汇总帧计数中的 recovery 是约 0.97%，**不是独立视频时间比例**。不应沿用 2.22% 作为逐帧重加权的精确统计。

当前标签字段 fps 也有精度差：TAS-S ego 24.92，TAS-B ego 24.917；exo 30。后续按帧索引和版本匹配，不默认所有流恒为 25/30 的精确值。

### C.2 发布划分与文档的冲突

官方 [BENCHMARK.md](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md) 声称同 trial 各视角共用分区。实际以 TAS-S 为例：

| 划分 | train/val/test 文件数 | train∩val trial 数 | train∩test trial 数 | val∩test trial 数 |
|---|---|---:|---:|---:|
| S1 | 448 / 56 / 56 | 14 | **42** | 10 |
| S2 | 466 / 58 / 36 | 10 | **9** | 0 |
| S3 | 413 / 52 / 95 | 11 | 0 | 0 |
| S4 | 398 / 50 / 112 | 12 | 107 | 17 |
| ASR S1 | 64 / 10 / 18 | 0 | 0 | 0 |

具体复核样本 `AL07EJ17_Disassembly_A_002`：

- train：`..._top`
- val：`..._right`、`..._ego`、`..._left`
- test：`..._front`

源位置：`annotations/impact/IMPACT-v1.1/annotations/TAS-S/splits/{train,val,test}.split1.bundle`。这是相同执行的不同视角，而不是碰巧重名的独立执行。全部交集清单已存 [impact_validation.json](impact_validation.json)。

S4 以同执行做跨视角适配本身可以作为专门设定，但与“所有划分均 trial 隔离”的笼统描述不一致。以上证据不自动证明作者运行时使用了完全相同文件，也不量化对分数的影响。

### C.3 图与状态映射不能混用

[Gemini PSR 的 procedure_graph.json](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/tasks/PSR/gemini_3_1_pro/configs/procedure_graph.json) 有 53 个事件节点、102 条边；metadata 为 num_videos=92，min_cooccur_frac=0.25、min_support_frac=0.2、min_confidence=0.9，事件 install_ok/recover_ok/remove_ok。文件明确说明边是从数据挖掘的前置关系。它与 `procedure_info_IMPACT.json`（51 个部件事件）的语义和用途不同。

历史记录中关于图约束力度的数值未获得原文确认；不能把统计学习图的缺边当作工程上已经证明的可交换关系，也不能把该图直接称为人工 GT。

## D. 上游补充标注

- EgoOops：50 个视频、538 个步骤片段，其中 95 个有 mistake labels；5 个任务键；6 类原始错误。派生 VQA 仅取其中 215 个片段。
- Assembly101 mistake benchmark：328 个无表头 CSV、3,964 行；correct 2,927、mistake 707、correction 330。43 行为 6 列、没有末尾 remark；其余 3,921 行为 7 列。发现 1 条 end≤start；保持源文件原样。
- EPIC-Tent：动作/错误 CSV 保存 GoPro 与 SMI 的同步 timecode 和 frame index；漏步的 end time 不应作为事件持续时间使用。完整统计在 [upstream_validation.json](upstream_validation.json)。

原始标签不能直接替换 VQA 派生标签：尤其 correction 在 VQA 中作为 Correct Wrong Action 分类，IMPACT 则单列 recovery phase，三者业务含义不同。
