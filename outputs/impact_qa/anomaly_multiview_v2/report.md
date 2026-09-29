# IMPACT 第二轮多视角视觉补查（2026-09-28）

结论：持有工具、伸入料盒、手指操作、台面暂放都不能独立映射为异常类型。增加视角能帮助确认对象、目标盒和组件状态，但不自动补全原始标注的原因。本轮把证据细化到了可读的料盒编号、物体释放和状态变化；仍未获得可推广到全数据的六类官方操作判据。

## 范围与可信度

- 7 次执行、5 位参与者、12 组目标操作，各查看 front/top/ego，合计 36 个视角窗口。6 组是上轮疑点补查，6 组是新增 front 目标（3 异常、3 normal 候选）。不是 36 个独立试验。
- 36 张序列图：720 帧条目、714 个唯一源帧；5 个 ego 窗口放大查看共 10 张细节图，复用 60 帧。另查看 SS 正常转移段全部 22 张连续源帧，新增 10 个唯一帧；本轮合计 724 个唯一源帧。
- 审查者为 Codex 直接图像审查，不是人工专家；大部分窗口为采样审查，不是整段逐帧播放。前后上下文单独标记。GT 对审查者可见，因此不是盲测。
- 本轮继续使用了上一轮检验参与者，仅用于疑点跟进，不能报告为新的独立测试。未计算分类准确率或误报率。
- 12 个 front 原生参照、21 个其他视角同动作时间候选、3 个仅用于观察的近似窗口。都不宣称逐帧同步；同名动作也可能只覆盖同一次操作的部分。
- 本轮未调用 Qwen API，未新增正式 QA，未更改既有 QA 或上轮冻结的 rulebook。参考 prompt v3 独立保存，尚未进行其生成效果复测。

## 关键实证

### 1. normal 持工具入盒：反例经三视角确认

`LE07UF17_Disassembly_A_004`，右手，front/top 160.733–162.667 s；ego 161.175–163.101 s。三视角原生 `place_screw` 均为 normal、异常向量全零。

正面、俯视可见右手持红黄柄改锥伸入紧邻蓝盒的红盒，之后带同一工具撤回。ego 可读到 `Box 4`，蓝盒为 `Box 5`；进入盒内时工具杆朝斜上方，手指操作处被遮挡。能够确认“仍握着工具入盒”，不能补写“刀尖把螺丝送入盒内”或精确释放瞬间。

[第一视角细节 1](details/ac_caf796a863e97b95_ego_p1.jpg)；[第一视角细节 2](details/ac_caf796a863e97b95_ego_p2.jpg)；[正面序列](frames/ac_caf796a863e97b95_front/sheet.jpg)。源标注位置分别为 front/top `/segments/70`、ego `/segments/77`，完整文件名及 SHA 在 `visual_reviews.jsonl`。

这足以否定“拿着工具去放部件就是错误”的充分条件；不能反向宣称所有同类动作都正常，更不能把目标手 normal 扩大为整段双手均正常。

### 2. 没拿工具也会有 Spatial；细节图能确认实际释放

`LE06AS03_Disassembly_A_003`，右手，front/top 122.800–125.433 s，ego 124.253–125.818 s，`place_screw/Spatial`。

ego 的 f3117–f3134 显示右手把细长金属紧固件放在桌面的灰色区域，末两帧手指离开后物体仍在桌上；改锥躺在旁边。GT 提供 screw 名称，视觉支持形状、台面位置与释放。这个实例说明“Spatial 的原因总是同时拿着工具”同样不成立。

[细节 1](details/mv_8ddc3ed4e499_ego_p1.jpg)；[细节 2](details/mv_8ddc3ed4e499_ego_p2.jpg)。尚不能从一例推出“所有临时桌面放置都是 Spatial”：需要针对该对象/步骤的放置要求。

### 3. Box 2→Box 3：局部纠正候选，不冒充已经证实的纠正

`SS07EL13_Disassembly_B_005`，右手：

| 原生时间 | GT | 已确认视觉事实 |
|---|---|---|
| front 87.233–89.667 s；ego 87.571–90.019 s | store_screw / Spatial | 右手进入 Box 2，工具在桌上；具体释放受遮挡 |
| front 94.100–94.967 s；ego 94.434–95.316 s | store_screw / normal | 右手从 Box 2 抬起，移向已有银色部件的 Box 3 |

原生上下文顺序为：移除螺丝→异常存螺丝→拆出并存放轴承板→正常拿螺丝→正常存螺丝。第二段全部 22 张连续 ego 源帧已查看，能确认盒间手部转移，细小螺丝仍被手指挡住。无法严格确认是此前的同一颗螺丝，也没有 Box 2/3 针对该螺丝的完整规范。因此保留“可能是改正存放位置”的局部假设，不写成正式原因答案。

[异常存放细节](details/mv_4b8ab0029243_ego_p2.jpg)；[正常段连续帧第 2 页](dense/mv_6a0bcfa0824d_ego/p2.jpg)；[全部连续帧清单](dense/mv_6a0bcfa0824d_ego/manifest.json)。增加帧数没有消除手部遮挡，不继续靠重复采样补写因果。

### 4. 同名存轴操作，组件状态不同

`LE07UF17_Disassembly_A_001` 左手：287.233–290.667 s 的 `store_drive_shaft/Spatial` 中，轴仍带着较大黑色盘状部件，先探向红盒再探向蓝盒，之后仍持组件回到操作区。297.733–299.833 s 的同名 normal 段中，大盘已分离留在红盒，较细轴被释放到蓝盒，撤手后轴仍留在盒内。

中间 front 原生 GT 有 `dismount_adapter_plate`（左手 292.767–295.667 s、右手 295.633–296.267 s）和 `store_adapter_plate`，视觉也支持分离后的状态变化。这对样例不能作为“对象状态相同、只改变放置手法”的干净正负对照。不能由此单独认定 Spatial 的官方原因就是没有先拆适配板。

[异常段俯视](frames/ac_5bdf885219e6c3a2_top/sheet.jpg)；[正常段俯视](frames/ac_2bd6151e86531bc4_top/sheet.jpg)。ego 同名异常段 290.043–291.407 s 只包含局部蓝盒动作，较早部分在 `null/Spatial` 中，必须保留前文，不能只取同名标签就认为事件完整。

### 5. Temporal+Handling 也不能靠类别名补原因

`KI03AR28_Disassembly_A_001` 右手 139.367–143.067 s，三视角对应 `store_screw` 均为 Temporal+Handling。ego 可见右手从台面拿细长物移入 Box 4，之后左手也操作该盒。右手没有同时拿改锥；左手另有 `store_M4_nut`，不要把两只手合成一个“纠正”动作。

[细节 1](details/mv_cfe39ed51190_ego_p1.jpg)；[细节 2](details/mv_cfe39ed51190_ego_p2.jpg)。这段 3.7 s 不能用来发明 Temporal 的时间阈值；GT 没有给出违反的抓握规范或前置顺序。97.633–98.967 s 的 normal 存螺丝候选处于不同拆卸阶段、不同对象状态/盒位，只是背景参照。

## 跨视角标注差异

完整记录：[crossview_differences.json](crossview_differences.json)。这里比较的是局部操作对应，不是逐帧同步，也不判定哪个视角标错。

| 局部操作 | front/top/ego 差异 | 出题处理 |
|---|---|---|
| ER10WE06_Disassembly_A_001 的长 store_screw | front/ego Spatial；top Spatial+Handling | 各视角保留自己的多标签；持工具不解释新增 Handling |
| LE07UF17_Disassembly_B_005 71.533–74.733 s | front/top attach_screw；ego pick_up_torx_screwdriver、align_screw，类别均覆盖 Wrong tool | 可描述取工具及接近组件；不用 attach 字面推导持续拧紧 |
| 同执行随后 74.733–76.133 s | front/top attach_screw/normal；ego 局部窗口为 Wrong tool、Procedural | 从跨视角干净 normal 对照中排除，不把 front Correct 复制到 ego |
| LE06AS03_Disassembly_A_003 左手 170.533–171.767 s | front/top store_screw/normal；ego 局部窗口为 store_adapter_plate/normal 和 null/Temporal | 保留观察，排除跨视角正常对照；此例还是另一只手，不能算严格配对 |

其中 3 组有标签差异、3 组有动作名差异，二者重叠。它们在定向疑点样本中的比例不能估计全数据标注错误率。

论文使用的原文为 “view-specific refinement for occlusion and phase adjustment” 和 “Anomalies carry six non-exclusive type labels”。这些文字支持保留视角差异与多标签，不意味着所有差异都已解释。[本地论文原文](../../../papers/IMPACT.txt:446)；[论文链接](https://arxiv.org/html/2604.10409v1)。本轮只重新查阅本地论文与已下载官方装配手册，没有新增网络检索。手册照片展示部分部件分组，不能等同逐类异常判据；A 型装配参考也不能无条件用于 B 型。

## 对生成过程的具体改进

新参考：[anomaly_evidence_rules_v3.txt](../../../prompts/impact_qa/anomaly_evidence_rules_v3.txt)。GT 类别仍来自原生标注；视觉部分按“手—工具—对象状态—接触—目的地—释放—最终状态”取证。料盒编号、同一对象跨帧跟踪、适用规范来源分别记录。标签分歧不投票，证据缺失不改成 Correct。

可用于事实类开放题的内容包括“是否仍拿着工具”“放到了桌面还是盒子”“存放前是否分离了盘状件”等，但只在该例证据足够时提问。原因类、是否正确类、是否已纠正类必须另有适用规范和对象连续性支撑。开放题仍应由 Qwen 生成；本轮的 Codex 审计笔记不是新增问答样本。

下一步优先核对台面操作指引/官方手册中具体组件和紧固件的存放分组及 A/B 适用范围，用图像可识别的部件连接到规范；对剩余 Handling、Temporal/Procedural 边界和 Wrong part 专门选实例，不把本轮结论当作已经覆盖六类。本轮 Wrong part 目标为 0。

## 复现与审计

入口：`scripts/inspect_anomaly_multiview.py --prepare-only` 预检；不带参数生成/复用源帧；`render_anomaly_multiview_details.py` 放大已有帧；`render_anomaly_multiview_dense.py` 对指定短目标逐源帧补查；`audit_anomaly_multiview.py` 核验并导出逐视角审核记录。复用 native_trial/common，密集源帧读取另存 `impact_qa/source_frames.py`。

21 份原始标注文件的 SHA、302 个上下文原子段的 pointer/起止帧/动作/手/phase/异常向量均核验通过；36 个窗口的源视频、GT 来源视角、帧作用域、引用帧存在性和完整审核记录通过。front/top 30 fps，ego 24.917 fps；PTS 与标注时钟最大差约 5.7e-14 s，仅表示抽帧时钟计算正确，不证明摄像机跨视角同步或 GT 边界精确。

六份新建/修改 Python 文件语法检查通过；普通抽帧和密集抽帧均验证缓存重跑。数据检查结果在 [audit.json](audit.json)，源代码和 prompt 哈希在 [code_manifest.json](code_manifest.json)，逐例事实和引用在 [visual_reviews.jsonl](visual_reviews.jsonl)。

预检发现 LE06 该执行没有同手 normal 螺丝存放对照，初始选择报空集合错误，未继续伪造配对；改为明确标记另一只手的参考，并在审核后排除其严格对照资格。另修正了近似 ego 窗口的图标题：使用 approximate review window，而非暗示原生 GT 区间。更新仅涉及标题，源帧和冻结选择未变化。
