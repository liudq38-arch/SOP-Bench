# Spatial专项：视觉事实、任务规则和原始标签分别核验

本轮查了21个目标操作（原front标签10异常、10normal、1recovery），12次执行、6位参与者；42个top/ego操作窗口加2个补查窗口。直接查看44张序列图、792帧条目/773唯一源帧，以及6张完整原图细节。审核者Codex，未经过真人专家审核；定向取样，不能估计准确率或全库错标比例。

## 最可信的局部规则

**在当前A型拆卸任务中，已拆下并进行归位存放的部件，应进入现场步骤图指定的组件组料盒。** 判错须确认对象与状态、实际目的地和适用指引；已经释放、仍在手中尝试归位应分别表述。此规则来源于任务约定及可见过程，不依赖“原GT永远正确”。

现场图示与官方手册对应的A型分组：Box 1侧手柄；Box 2拨杆及其弹簧/垫圈/螺丝组；Box 3轴承板及其两螺丝；Box 4适配板、小锥齿轮及相关长螺丝/螺母；蓝Box 5壳体和轴组件。具体小紧固件必须确认身份，不能用泛称screw自动分配盒子；本轮直接行为核查集中于手柄、拨杆及适配板，其他分组来自参考图，不是本轮每类均验证。

| 目标 | front时间（秒） | 实际观察与判断 |
|---|---|---|
| KI05KO01_Disassembly_A_001 手柄 / p6_spatial | 17.900–21.333 | 手柄放入Box 4并留在盒内。现场Step 1要求Box 1；支持局部Spatial错误。ego原标签normal疑似漏标。 |
| 同执行手柄 / p6_recovery | 57.000–59.033 | 右手将该外观手柄从Box 4移至Box 1并释放；支持纠正，原phase recovery。初次左手、纠正右手。 |
| 同执行拨杆 / p9_spatial | 55.567–57.033 | 持拨杆进入Box 3区域，后续仍在手中；结合Step 2要求Box 2，支持错误目标尝试，初次是否释放不确定。 |
| 同执行拨杆 / p9_normal | 59.033–60.500 | 拨杆放进Box 2并留下。虽原phase normal，仍可在前后语境中描述改变目的地。 |
| AL07EJ17_Disassembly_A_001 手柄 / p11_normal | 9.167–10.600 | 拆下手柄放Box 1并释放。 |
| NA07GE21_Disassembly_A_002 手柄 / p12_normal | 8.433–10.067 | 同样放Box 1，top补足ego视线移开期间的释放。 |

两个具体Spatial解释局部成立，但它们都来自KI05同一次执行，不能包装成两参与者或已经完成跨参与者异常规则验证。两位其他参与者提供正确目的地参照；不能据此计算召回率。手柄中间状态另外按约4s采样，非35.7s全帧连续跟踪。

现场指引原图：[NA步骤图](details/p12_normal_ego.jpg)、[LE步骤图](details/p4_normal_ego.jpg)。手柄证据：[错盒后仍留在Box 4及图示](details/p6_spatial_ego.jpg)、[移至Box 1](details/p6_recovery_ego.jpg)。拨杆最终[Box 2落点](details/p9_normal_ego.jpg)。这些均为实际源视频图像，不是示意生成图。

## 不保留为硬规则的推断

- 工具未回初始排列区就算错：p1同视频十字改锥异常/normal均中央附近放置，p3 normal扳手在白色台面，缺少明确区域约定。p2/p8虽然重现“异常靠工作中心、normal回工具区”，都来自NA同一参与者，仍不足以定通则。
- 部件只要暂放桌面就算错：p4适配板、p5轴承板有类似normal暂放；应区分临时加工、腾手、存放。normal也可能漏标，因此这些是反例线索，不能反向把所有桌面放置判正确。
- 持工具入盒就算错：沿用上轮已检查反例，当前规则须解释实际违反的条件，不能用共同持有替代。

## 疑似标注问题与匹配问题

1. **高优先级疑似漏标：p6_spatial_ego。** 同样可见手柄入Box 4，ego18.782–21.391s标normal。依据是可见错误落点、现场指引与后续纠正，不是front/top多数票。
2. **疑似误标或缺少隐含约束：p10_spatial。** LE06AS03_Reassembly_A_001 front127.433–127.933s、ego127.824–128.426s，适配板从Box 4取出让另一手拿螺母，再放回原Box 4；各视角Spatial。没有观察到错误盒号，不能生成“放错盒”的解释。是否有摆放方向、人因或冗余取放标准仍未知，独立标签保留unknown。
3. **局部标注差异：p4_normal。** front/top place_adapter_plate normal；ego邻近dismount normal及null Spatial。动作边界和类别共同不同，待查而非确定错标。
4. **已拒绝的自动对应：p7_spatial_ego。** 同名loosen_screw和±3.5s匹配选到了较早Temporal段，不能视为同一Spatial事件的跨视角冲突。补50.5–52.3s后看到工具收回，仍未建立明确位置错误。p7_normal则是另一工具/紧固件阶段，也不能算严格对照。

## 记录、复现和应用

- `cases.jsonl` / `followup_cases.jsonl`：冻结的原生GT、区间、手别、媒体及对应候选；源GT未修改。
- `visual_reviews.jsonl`：44条视角记录，原标签与独立物理判断分开，包含审查范围、全部源帧、PTS、来源SHA和pointer。
- `direct_review_notes.json`：21个操作及2个补查语境的联合解释；含反例、疑似错标与原因未知。
- `rules.json`：可用于后续实验的局部规则与被否定捷径。
- `audit.json`：36份GT、423个来源段内容/SHA核验，773唯一帧，最大PTS与标注时钟差5.684e-14s；这个数字不代表跨摄像头已经逐帧同步。

运行 `.venv-impact/bin/python scripts/inspect_spatial_rules.py`、`scripts/inspect_spatial_followups.py`、`scripts/audit_spatial_rules.py`。渲染器缓存保留；GT、帧范围、作用域、原文件内容及代码语法检查通过。抽帧为4前文+10目标+4后文；短目标用于判据诊断，不自动加入生产≥5s优先集合。

新的六类工作框架在 `reports/impact_qa/anomaly_first_principles.md`，简洁参考prompt为 `prompts/impact_qa/anomaly_first_principles_v4.txt`。未调用模型、未新增QA、未接入全量生产。下一轮从Wrong tool继续按独立任务约束核验，允许质疑normal和anomaly两侧的原GT。
