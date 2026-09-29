# EgoErrorVQA、CaptainCook4D、IMPACT 调研

## 2026-09-28 当前判据研究更新：GT可错，Spatial完成首轮独立约束审查

用户明确要求允许annotations出错。当前方法：先从任务目标、机械接口、组件状态及明确的任务约定判断违规，再用原GT检查一致性；保留疑似漏标/误标，原始文件不覆盖。机械原理不能推出任意盒号或经验时长阈值。六类候选定义、术语、边界与限制集中在[anomaly_first_principles.md](reports/impact_qa/anomaly_first_principles.md)，替代把normal/anomaly当不可质疑真值的旧设想。

证据：Spatial专项21目标/44视角或补查窗口，792帧条目/773唯一源帧，12次执行/6参与者。手柄Box 4存放后移到Box 1，现场指引与另外两参与者正确存放支持局部空间错误；ego normal疑似漏标。拨杆支持错误目标尝试，初次释放未确认。适配板取出再放回原Box 4虽各视角Spatial，仍无错盒证据，列疑似误标或隐含条件未知。具体时间、图像、SHA和pointer见[本轮报告](outputs/impact_qa/spatial_rules_v1/report.md)。两个支持异常同属一次执行，不能称泛化验证或计算识别准确率。

来源限定：论文§3.3原文“six non-exclusive type labels”，只支持类别可并存，未给逐类机制判据；[论文](https://arxiv.org/html/2604.10409v1)。官方[Manual_Book图](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/Manual_Book.svg)Disassembly行支持部件分组，具体Box编号由视频现场Step 1/2图与盒标签核验。规则属于任务约束推断，不冒充官方异常rubric。历史资料在下文，具体判据以当前记录的支持度为准。

## 当前研究补充：实际异常/正常对照（2026-09-28）

完成Wrong tool/Spatial判据研究首轮71案例：41异常、30normal匹配候选；Codex直接检查1420帧条目，另做不提供GT的VLM事实观察。详细证据、源标注pointer/SHA、帧和时间在[完整审计](outputs/impact_qa/anomaly_contrast_v1/case_audit.jsonl)与[报告](outputs/impact_qa/anomaly_contrast_v1/report.md)。这是本项目实例研究，不是官方定义。论文只给出“Anomalies carry six non-exclusive type labels”，出处为[IMPACT §3.2](https://arxiv.org/html/2604.10409v1)，公开rubric缺项见[来源审计](reports/impact_qa/anomaly_taxonomy_audit/report.md)。

“局部序列解释”指将GT异常区间与经图像核准的实际工具、后续更换及同一局部组件续作对应，不能推导未看清的螺丝槽型或成功纠错。冻结条件后，发现侧3例、参与者隔离检验侧1例满足完整局部材料要求。既有Torx→Phillips，也有Phillips→Torx，型号A不足以指定唯一正确工具。[冻结条件](outputs/impact_qa/anomaly_contrast_v1/rulebook_frozen_v1.json)不是自动类别分类器。

关键反例：LE07UF17_Disassembly_A_004右手160.733–162.667秒，GT normal/place_screw，同时可见仍持改锥伸入红盒再返回；因此不能将“持工具去放部件”作为充分错误条件。[放大帧](outputs/impact_qa/anomaly_contrast_v1/validation/direct_frames/ac_caf796a863e97b95/retained_tool_check.jpg)。Spatial放轴例的异常目标携带圆形组件且最终没释放，正常对照已是裸轴并放入蓝盒；必须核对对象状态，不能只按同动作名比较落点。

“边界对照”指同一次连续动作被切成相邻normal/anomaly区间，只用于诊断边界，不能当独立同状态正反例。本轮30个匹配normal中8对紧邻、3对间隔<5秒；另有状态不等价例，因此没有计算类别准确率或误报率。12个保留Spatial案例仍无足够规范性原因，不能用位置常识填补。

模型观察修正：上下文视频描述会侵入目标且混淆左右手；分离目标区间、扩大操作区和单帧预算后，8个困难例中4个主要错误得到修正，2个仍有明显错误。多项设置同时改变，非消融试验，不归因于某一因素。JSON有效与高置信度不能代替语义核验。[逐例比较](outputs/impact_qa/anomaly_contrast_v1/discovery/focus_comparison_notes.json)。保存[证据规则few-shot](prompts/impact_qa/anomaly_evidence_rules_v2.txt)，未接入生产。GT类别QA、可见动作QA和规范性原因QA需要分别记录可用性，避免将盲模型分类能力当GT正确性的前提。

## 当前试验补充：多异常 MCQ 的范围与证据（2026-09-26）

以下为本项目根据本地GT提出的工程方案，不是论文报告的方法或已验证性能。证据来自 [clipfix4候选](outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix4/fixed_mcq.jsonl)、[原始异常分布](outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix4/anomaly_length_distribution_20260926.json) 和 [新离线审计](outputs/impact_qa/mcq_grouped_v1/offline_audit.json)。旧题目的原文为 “Does this clip contain an abnormal operation?”，但GT答案仅取完整且≥5秒异常；因此短异常、跨边界异常或canonical去重均可能使整段措辞与答案范围不一致。

定义：episode是时间相交或相距≤0.5秒的ATR事件组，只用于组织，不改变任何原始event/hand/标签/时间边界。canonical归属指同一ATR事件在重叠组件clip中仅保留一个出题归属（优先最短完整包含clip），它不表示其余clip的该异常消失。局部观察窗口是原始视频中最多30秒的连续观察范围，前后最多3秒上下文，2fps采样；长episode可跨多个窗口，GT仍保留完整源区间。

实测212个拟出题单元中，208个需要明确指定手和时间区间，只有4个不存在其他原始ATR相交记录、可以保留整段措辞。这是严格范围检查的结果，不是异常识别准确率。审查采用无类别提示的视觉观察，再按GT逐类核对；标签决定目标答案，但不能充当可见证据。具体类型没有参考条件时允许uncertain；自动保留与真人验收分别记录。异常边界来自GT，视觉证据只确认事件，不宣称每帧边界都获验证。

实施后更正：不能要求盲VLM先自主认出异常才允许GT出题；这会把数据扩充变成重做ATR标注。实际应分别记录GT答案可靠性、目标动作可见性、异常原因的视觉支持，见 [四轮试验报告](outputs/impact_qa/mcq_grouped_v1/final_report.md)。同时不能信任同模型自报“事实一致”：本次出现用工具/徒手以及左手/右手的文本矛盾。模型多轮审核只能筛查，不能替代独立审计。

原标注语义的关键证据：在本地TAS-B精确子区间复算中，322个目标ATR事件包含513个事件—类别组合，43个事件内部类别不是时间恒定的；24个类别的实际支撑短于1.5秒。[类型时长审计](outputs/impact_qa/mcq_grouped_v1/type_duration_audit.json)。因此原规则“ATR总时长≥5秒就让其所有标签继承≥5秒”不成立。新方案保留每个类型的TAS-B时间子区间，对过短类型设置hold，不能将无视觉支持或被过滤异常重标为Correct。

论文核查日期：2026-09-17；方案与 QA 试制增补：2026-09-18。已阅读三篇原文，并核对官方仓库和实际标注。本文区分 **论文报告**、**发布文件实测**、**基于证据的判断**；三篇论文的指标均非本机复现结果。首轮未下载媒体；后续用户授权 IMPACT QA 试制，已复用用户完成的 ego 视频下载并通过哈希/CRC 校验，见 §7。9 月 18 日另用已有 Qwen3-VL-8B 做合成容量探测。没有训练模型，已有权重直接复用。

## 1. 三篇论文是什么关系

| 论文 | 主要贡献 | 视频来源 | 最适合回答的问题 |
|---|---|---|---|
| EgoErrorVQA | 跨场景程序性错误 VQA 基准、A2A 评测器、Ego-ADR 零样本推理流程 | 重用 CC4D、EgoOops、EPIC-Tent、Assembly101 | 给定步骤片段、程序文本和问题，VLM 能否解释/识别错误？ |
| CaptainCook4D（CC4D） | 真实厨房第一视角多模态数据及错误理解基线 | 自采 384 次烹饪录制 | 能否定位步骤、识别步骤错误、学习程序结构？ |
| IMPACT | 真实工业装配中动作—状态—步骤完成—异常恢复的多层标注和统一基准 | 自采角磨机拆装，112 次执行、每次 5 个视角 | 能否在遮挡、多条合法执行路线、异常和恢复下理解工业流程？ |

上述定位来自各论文摘要及任务章节：[EgoErrorVQA](https://arxiv.org/html/2608.24134v1)、[CC4D 正式论文](https://proceedings.neurips.cc/paper_files/paper/2024/file/f4a04396c2ed1342a5d8d05e94cb6101-Paper-Datasets_and_Benchmarks_Track.pdf)、[IMPACT](https://arxiv.org/html/2604.10409v1)。IMPACT 此处明确指 **A Dataset for Multi-Granularity Human Procedural Action Understanding in Industrial Assembly**，不是医学配准或机器人控制领域的同名方法。

**不能直接横向比较三篇的 F1。** EgoErrorVQA 的评测依赖已给定的片段、步骤与错误类别，CC4D 的监督错误识别主要是步骤二分类，IMPACT 则区分逐帧分割、完成事件、状态与多标签异常诊断，评测单位和输入先验不同。下文详细列出各自协议。

## 2. EgoErrorVQA

### 2.1 身份、数据和任务

- 标题：*EgoErrorVQA: Assess Egocentric Comprehension Capabilities through Procedural Errors for Ego-Agentic AI*。
- 作者：Junlong Li 等；arXiv:2608.24134v1，2026-08-25。GitHub 仓库描述标为 EMNLP 2026；本次获取的是 arXiv 版本，不将仓库描述当作已核验的正式会议录。
- [论文](https://arxiv.org/abs/2608.24134)、[官方代码和标注](https://github.com/z1oong/EgoErrorVQA)。核查提交 `5403cdd05e007b01c88448587c1a1803a27266e2`。
- **这是评测集，没有配套训练集。** 原文 Limitations 的短引文：“does not include training data”。因此不能把其开放题和选择题当作独立 train/test：它们大量共享视频和片段。[原文 Limitations](https://arxiv.org/html/2608.24134v1)

表中前四个数量来自论文 Table 2，已逐项与下载 JSON 复核；最后一列是本次按 `video_id` 去重的实测值。

| 来源 | 场景/任务数 | 开放题片段 | 开放题 QA 对 | 选择题样本 | 两种评测合并后独立视频 ID |
|---|---|---:|---:|---:|---:|
| CC4D | 烹饪，24 | 960 | 1,857 | 1,000 | 359 |
| EgoOops | 手工/实验，5 | 215 | 418 | 215 | 50 |
| EPIC-Tent | 搭帐篷，1 | 184 | 426 | 182 | 4 |
| Assembly101 | 玩具车装配，合并为 1 类任务 | 446 | 859 | 460 | 97 |
| 总计 | 31 | **1,805** | **3,560** | **1,857** | **510** |

论文 Table 1 写 800 个原始视频，但发布 JSON 的合并结果是 510 个来源内唯一视频 ID；800 的统计口径未能从发布文件复现，不能把它解释成需要下载 800 个独立文件。[论文 Tables 1–2](https://arxiv.org/html/2608.24134v1)；实测见 [annotation_validation.json](reports/annotation_validation.json)。

**输入/输出。** 开放题输入为程序文本、问题及指定时间片段，输出自然语言回答。选择题额外给当前动作描述和错误类别定义，要求输出 `correct` 或一个错误类别。实际更接近闭集标签生成，并非每道题都有 A/B/C/D 选项。论文在动作区间内均匀抽取 8/16/24/32 帧，而非从完整长视频自动寻找错误。[§3.2、§4.1、§6.1、附录 C](https://arxiv.org/html/2608.24134v1)

错误体系为 8 类错误，加 `correct`：Wrong Object（对象/工具错误）、Wrong Action（动作执行错误，包括部分时间/温度/数量错误）、Wrong Order（顺序错误）、Omission（漏步）、Unintended and Unnecessary Action（多余/非预期动作）、Correct Wrong Action（纠正先前错误的动作）、Equipment Failure（设备故障）、Others。**Correct Wrong Action 表示恢复事件，并不表示新的违规行为**；这与 CC4D 的错误类别不一一对应。[§4.1、附录 D](https://arxiv.org/html/2608.24134v1)

### 2.2 数据构造和方法

**QA 构造。** Qwen2.5-7B-Instruct 根据源标注生成问题与答案，3 名标注者约 80 小时审核，另有人工补充和干扰性提问；最终 2,749 对经模型生成后人工修订，811 对人工编写。程序文本保存在 `procedure.json`，共 31 项。[§3.3](https://arxiv.org/html/2608.24134v1)

**Ego-ADR = Adaptive Decoupled Reasoning，自适应解耦推理。** 原文明确把推理拆为 “Key-step match”、“Video narration”、“Error classification”：先定位程序中的相关步骤，再描述视觉观察，最后与程序要求比较并分类。[§5、Figure 3、附录 G](https://arxiv.org/html/2608.24134v1)

| 分支 | 步骤匹配 | 视频描述 | 最终判断 |
|---|---|---|---|
| 深解耦 | 用文本推理检索当前、前后步骤；程序库由 Qwen2.5-VL-7B 结构化 | 生成片段叙述 | 根据叙述、程序上下文和类别定义做文本推理 |
| 浅解耦 | TF-IDF unigram/bigram + 余弦相似度；低于 0.25 时回退字符序列匹配 | 显式描述对象/工具、动作和异常 | 错误类型词表与关键词匹配 |

分支依据模型能否稳定进行纯文本推理；Qwen2-VL、Qwen2.5-VL 用深解耦，Video-LLaVA 用浅解耦。它是**零样本推理组织方法**，不是新的视频编码器，也没有用该基准训练新模型；Ego-ADR 增益只在选择题上评估。[§5.1–5.2、§6.1、Limitations](https://arxiv.org/html/2608.24134v1)

**A2A = Agent2Agent 协议。** Green agent 是评测方，传递片段路径、时间范围和问题，接收 White agent（被测模型）的回答；这个通信封装本身不等于在线连续视频监测。[§1、附录 B、官方 README](https://github.com/z1oong/EgoErrorVQA)

### 2.3 评测、结果和复现边界

开放题由 Qwen2.5-7B-Instruct 和 DeepSeek-LLM-7B-Chat 两个裁判比较回答与参考答案的语义一致性，各打 0–5 分后平均。裁判分数不是视觉正确率。论文 Table 3 报告：人类 Avg-Sim. 3.77，Qwen2-VL-7B（24 帧）3.33，GPT-4o（8 帧）3.17。人类开放题只抽 75 对；选择题只抽 100 个样本，不能当作全量人工测试。[§3.4、Table 3、附录 C](https://arxiv.org/html/2608.24134v1)

选择题结果摘自 **Table 4 的原始数值**（百分数）：

| 模型，8 帧 | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Qwen2-VL-7B | 17.5 | 8.6 | 73.9 | 15.5 |
| Qwen2-VL + Ego-ADR | 21.5 | 11.2 | 67.5 | 19.3 |
| Qwen2.5-VL-7B | 12.8 | 10.1 | 97.3 | 18.2 |
| Qwen2.5-VL + Ego-ADR | 19.6 | 11.3 | 80.3 | 19.8 |
| Video-LLaVA | 44.2 | 7.2 | 16.3 | 10.0 |
| Video-LLaVA + Ego-ADR | 13.6 | 7.8 | 84.6 | 14.3 |
| GPT-4o | 57.9 | 17.5 | 25.6 | 20.8 |

**不能概括成所有指标都改善**：Video-LLaVA 的 Accuracy 明显下降。§6.3 的部分相对提升百分数与 Table 4 不一致；例如 Qwen2-VL F1 的表值对应约 +24.5%，正文写 +19.7%。本报告优先保留表中绝对值。[Tables 4–5、§6.3](https://arxiv.org/html/2608.24134v1)

另外，官方实现的 TP 只计错误类别匹配，**错误类型判错只计 FP，不同时计 FN**，然后仍使用 `TP/(TP+FN)` 算 Recall。这个 Recall 既不是标准多类宏平均 Recall，也不是通常的二分类错误检测 Recall；高值不能解释为识别了相同比例的全部真实错误。原文附录 E 和代码定义可核查，但正文的直观措辞容易引起误读。[评测代码 L426–498](https://github.com/z1oong/EgoErrorVQA/blob/5403cdd05e007b01c88448587c1a1803a27266e2/src/green_agent/agent.py#L426)

发布实现还存在以下具体边界：

- 开放题用 `random.choice(sample["qa_pairs"])`，每片段抽一道题，而非遍历全部 3,560 对；该文件未设置随机种子。[代码 L685](https://github.com/z1oong/EgoErrorVQA/blob/5403cdd05e007b01c88448587c1a1803a27266e2/src/green_agent/agent.py#L685)
- CC4D 选择题有 88 条多标签真值，输出只需匹配列表中任一标签；不能直接当作严格单标签九分类训练集。
- CC4D 选择题有 53 条非有效正时间区间；开放题有 52 条。多数源于漏步 `(-1,-1)`，不可直接裁剪为视频证据。EPIC-Tent 两份文件各有 2 条异常区间，包括 end < start。
- EgoOops 选择题 40 条错误样本的 `action_annotation` 为 null；代码却以该字段填当前步骤，不自动回退 `instruction_label`。
- 论文 Appendix C 写 `max_new_tokens=256`，公开 White agent 示例是 128、8 帧。仓库树未见独立 Ego-ADR 实现，已发布主体是评测器与 Qwen 示例，不能声称 Ego-ADR 已可原样运行。[官方实现](https://github.com/z1oong/EgoErrorVQA/tree/5403cdd05e007b01c88448587c1a1803a27266e2)

这些是静态数据/代码核查，不代表已测出对论文结果的影响；详见 [data_audit.md](reports/data_audit.md)。

## 3. CaptainCook4D（CC4D）

### 3.1 身份与采集

*CaptainCook4D: A Dataset for Understanding Errors in Procedural Activities*，Rohith Peddi 等，NeurIPS 2024 Datasets and Benchmarks。arXiv 最初发布于 2023 年，最新记录为 2312.14556v4（2024-12-09）；本报告以正式会议 PDF 为主要依据。[论文](https://proceedings.neurips.cc/paper_files/paper/2024/file/f4a04396c2ed1342a5d8d05e94cb6101-Paper-Datasets_and_Benchmarks_Track.pdf)、[项目页](https://captaincook4d.github.io/captain-cook/)、[标注仓库](https://github.com/CaptainCook4D/annotations)、[下载器](https://github.com/CaptainCook4D/downloader)。

摘要的规模证据为 “384 recordings (94.5 hours)”。共有 24 种 WikiHow 菜谱、8 位参与者、10 个真实厨房。GoPro Hero 11 录制 4K/30fps；HoloLens 2 提供 RGB、深度、音频、IMU、头部/手部追踪。**4D 在这里涉及随时间变化的三维/多模态观测，并非四个摄像机视角。** 本次未下载这些媒体。[摘要、§3、附录 C](https://arxiv.org/html/2312.14556v3)

数据同时包含正确执行和故意/非故意错误。错误采集包括即兴犯错、带漏步/乱序的脚本、参与者先设计错误再执行；因此不应将全部错误当作自然发生的日常失误。标注先由录制者完成，再交第二人审核。[§3.1–3.2](https://arxiv.org/html/2312.14556v3)

### 3.2 标注内容

- **步骤级标注**：起止时间、step ID、正常/错误、错误类型、错误描述；粗步骤可包含取物等准备动作和收尾动作。
- **细粒度动作**：论文称约 10K，覆盖约 20% 数据；当前公开 annotations 仓库未定位到独立承载这 10K 动作的文件，不能将已获取的粗步骤文件视为完整细动作发布。
- **任务图**：24 份有向无环图（DAG）。原文短引文 “a directed acyclic graph”；节点表示步骤，边 x→y 表示 x 必须在 y 之前，拓扑序表示合法执行序。[§3 Task Graphs、§3.2](https://arxiv.org/html/2312.14556v3)
- 论文 7 类：Preparation、Measurement、Technique、Timing、Temperature、Missing Step、Order Error；文件另含 Other，合计 8 个 tag。[论文 Figure 3](https://arxiv.org/html/2312.14556v3)、[发布类别](https://github.com/CaptainCook4D/annotations/blob/a8a920a3293c4db27099a20ddbe3a3a9be1283e3/annotation_json/error_category_idx.json)

**发布文件实测与论文统计不能混写。** 当前官方提交 `a8a920a3293c4db27099a20ddbe3a3a9be1283e3` 中：

| 统计项 | 本次实测 |
|---|---:|
| recording 数 | 384 |
| `is_error=False / True` | 164 / 220 |
| `steps` / `step_annotations` 行数 | 5,700 |
| 非负时间区间行数 | 5,413 |
| 带错误标签的步骤行数 | 1,964 |
| 负时间区间 | 287，其中 281 条仅标 Missing Step，6 条无错误 tag |
| 存在重复 step_id 的 recording | 53 |
| task graph 文件 | 24 |

论文概称 5.3K 步骤，附录图表列正常/错误录制 173/211；与本次实测 164/220 不同，原因未获官方明确解释。不要用论文的四舍五入数或历史脚本常数覆盖文件实值。[正式论文 Figure 23、Table 18](https://proceedings.neurips.cc/paper_files/paper/2024/file/f4a04396c2ed1342a5d8d05e94cb6101-Paper-Datasets_and_Benchmarks_Track.pdf)；[实测报告](reports/annotation_validation.json)。

### 3.3 方法与实验设置

这是**数据集及基准论文**，不是单一新模型。方法线索及原文依据如下：[§4、附录 B](https://arxiv.org/html/2312.14556v3)。

| 任务 | 方法 | 输入与输出 | 指标 |
|---|---|---|---|
| 监督错误识别 SupervisedER | V1：预训练特征 + MLP；V2：步骤内部时序 Transformer；V3：多模态 Transformer | 每秒特征 → 步骤正常/错误；子片段多数投票 | Acc、P、R、F1、AUC |
| 零样本错误识别 ZeroShotER | Video-LLaVA / TimeChat；V1 单步骤问题；V2 Llama3 生成错误类别专属问题，回答做 OR 聚合 | 视频 + 针对步骤的问题 → 二分类 | Acc、P、R、F1 |
| 多步骤定位 MSL | 预训练视觉特征 + ActionFormer | 未裁剪长视频 → 步骤类别及时间边界 | mAP@tIoU、Recall@K |
| RobustMSL | 只在正常录制训练，分别在正常/错误录制测试 | 检查执行错误对定位的影响 | 同上 |
| 自监督程序学习 | TCC / CnC 表征学习 + Pro-Cut Module | 多段同任务长视频 → 关键步骤及顺序 | Precision、Recall、IoU |

MLP 基线的直接证据是原文 “trained a Multi-Layer Perceptron (MLP) head”。常用预训练特征包括 3D-ResNet、SlowFast、X3D、Omnivore、VideoMAE、ImageBind；使用特征不等同于把完整骨干在 CC4D 上重新训练。[§4.1、附录 B.2](https://arxiv.org/html/2312.14556v3)

训练超参数：MLP 用 batch 512、Adam、lr=1e-3；V2 用 batch 1 个步骤、lr=1e-5；V3 lr=5e-5。三者 50 epochs、正类 BCE 权重 1.5，论文使用单张 A40。[附录 B](https://arxiv.org/html/2312.14556v3)

可核对的例子：ZeroShotER 单问题→多问题，Video-LLaVA F1 从 6.7 到 41.8，TimeChat 从 2.26 到 46.1；但 Accuracy 分别从 64.3 降至 52.85、65.0 降至 43.5。说明更积极检出错误并不等于各项能力全面改善。[正式论文 Table 3](https://proceedings.neurips.cc/paper_files/paper/2024/file/f4a04396c2ed1342a5d8d05e94cb6101-Paper-Datasets_and_Benchmarks_Track.pdf)

### 3.4 数据划分与加载要点

论文讨论环境、人员、菜谱、录制、步骤、录制类型等划分；其中 **step split 允许同一录制的不同步骤进入不同分区**，不能解释为对未见视频的泛化。[附录 A.2](https://arxiv.org/html/2312.14556v3)

当前发布 JSON 的 train/val/test：

| 划分 | combined | normal-only |
|---|---|---|
| 环境 | 216 / 115 / 53 | 84 / 48 / 32 |
| 人员 | 204 / 84 / 96 | 90 / 35 / 39 |
| 录制 | 213 / 62 / 109 | 90 / 26 / 48 |
| 菜谱 | **0 / 0 / 0** | **0 / 0 / 0** |

非空划分内部无重复、无跨分区 recording 重合、无未知 ID。**recipe JSON 只是空壳，step split 在该仓库中没有独立发布文件**。不能看见文件名就认为划分可用。[官方 splits](https://github.com/CaptainCook4D/annotations/tree/a8a920a3293c4db27099a20ddbe3a3a9be1283e3/data_splits)

加载应以实际结构为准：`complete_step_annotations.json` 是 recording ID→dict，内部字段是 `steps`；`error_annotations.json` 是 list，内部为 `step_annotations`。文档的示例结构与实际不完全相同。`recording_id` 为 `1_7` 形式的字符串；重复步骤需要保留出现位置，不能只按 `(recording_id, step_id)` 去重。负时间表示不存在可直接裁剪的对应片段，不是普通视频时间。

## 4. IMPACT

### 4.1 身份与规模

*IMPACT: A Dataset for Multi-Granularity Human Procedural Action Understanding in Industrial Assembly*，Di Wen 等，arXiv:2604.10409v1，2026-04-12。官方页面当前仍标为 ACM Multimedia 2026 Dataset Track **under review**，故不写成已录用。[论文](https://arxiv.org/abs/2604.10409)、[项目页](https://kratos-wen.github.io/IMPACT/)、[代码](https://github.com/Kratos-Wen/IMPACT)、[数据发布](https://huggingface.co/datasets/KratosWen/IMPACT)。代码核查提交 `4fed5faa5f05f7aece55712e458defa1f372b248`，数据版本 **v1.1**。

原文的结构性证据是 “partial-order prerequisite graph” 和 “Recovery is explicitly labeled”：允许不同合法装配次序，并显式区分正常、异常与恢复。[摘要、§3–4](https://arxiv.org/html/2604.10409v1)

- 112 次执行、13 位参与者；4 位预先熟悉操作、9 位新手。任务是商业角磨机拆卸/重新装配，两种型号：Fein CG15-125BL、WSG7-115A。
- 每次 1 个第一视角 + 4 个外部视角：Tobii Pro Glasses 3（1920×1080，名义 25fps）；4 台 RealSense D455 提供 RGB-D，名义 30fps。还有第一视角 gaze/audio 与 NASA-TLX 工作负荷问卷。
- **39.5 小时是跨视角累计量**；Table 1 的 unique duration 为约 8.0 小时，不是 39.5 小时独立操作。场景为固定实验工作台和受控照明，不等同于 CC4D 多个真实厨房。[§3.1、Table 1](https://arxiv.org/html/2604.10409v1)

### 4.2 标注层次和任务术语

| 层次/缩写 | 内容 | 主要指标 |
|---|---|---|
| TAS-S：步骤级时序动作分割 | 给每帧分配粗步骤/背景；论文 26 个步骤类别 | Accuracy、Edit、F1@10/25/50 |
| TAS-BL/BR：左右手原子动作分割 | 两只手独立标注动词—对象，允许同时操作 | 同上 |
| CV-TA：跨视角时间对齐 | 找到另一视角中的**同一次动作发生** | Recall@1/5、Median Rank、Coverage |
| CV-SMR/SMC：跨视角语义检索/分类 | 找到同类动作或预测 verb/noun/action，不要求同一次发生 | Recall@K、mAP / Top-1、Macro-F1 |
| AF-S：短期动作预判 | 动作开始前预测手部交互 | mean Top-5 Recall |
| AF-L：长程步骤预测 | 观察 2 个步骤，预测未来 5 个；从 5 条候选未来中取最佳 | AUED、ED@z，越低越好 |
| PSR：步骤完成事件识别 | 51 类完成事件，用前置条件图评价顺序 | Completion F1、Delay、POS |
| ASR：装配状态识别 | 17 个部件实例的状态向量，-1/0/1 对应错装/未装/正确安装 | Macro-F1、Transition F1、Final-State Accuracy |
| PPR-L/R：左右手程序阶段识别 | normal / anomaly / recovery | Accuracy、Macro-F1、分类型 F1 |
| ATR-L/R：左右手异常类型识别 | 在异常片段上做六属性多标签诊断 | mAP |

任务、方法和定义依据：[论文 §3.2–4.3](https://arxiv.org/html/2604.10409v1)、[官方 BENCHMARK.md](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md)。**ATR 默认已给异常片段，不是从所有帧端到端检测异常**。POS 衡量预测完成事件序列与合法程序顺序的相似性；AUED 为随预测长度变化的编辑距离汇总，不能与分类准确率比较。

六类异常属性：temporal、spatial、handling、wrong part、wrong tool、procedural，可同时出现。`null` 表示未获得对应有效动作标签/可观测信息，不能无条件当作正常行为。NASA-TLX 是主观工作负荷信息，不是错误类别标签。[§3.2、§4.1](https://arxiv.org/html/2604.10409v1)

论文说 137 个有效动作类别；v1.1 的 `action_labels` 和 mapping 是 **138 项，含 null**。不能仅凭 137 与 138 就认定版本不一致。v1.1 确实另外修订了 M4/M6 螺母类别、时间边界、部分阶段字段和 117 个视频，应固定标注与视频版本一起复现。[发布说明](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/CHANGELOG.md)

### 4.3 方法、训练与关键结果

IMPACT 的核心是数据/统一协议，比较多种既有方法，而非提出一个名为 IMPACT 的新神经网络。[§4.3](https://arxiv.org/html/2604.10409v1)

| 方法组 | 具体基线及作用 |
|---|---|
| 时序分割 | LTContext（长上下文）、ASQuery（查询解码）、DiffAct（扩散细化）、FACT（帧—动作交叉注意力） |
| 跨视角 | 冻结 I3D、VideoMAEv2、MViTv2；余弦近邻检索/线性分类头 |
| 短期预测 | AVT、ScalAnt、零样本 Qwen3-VL-8B |
| 长期预测 | ScalAnt；AntGPT/PALM 的先识别再预测；Qwen3-VL-8B |
| 状态和完成事件 | MS-TCN++、VideoMAEv2+Head，先预测状态再导出完成事件；对比直接视频→步骤的 STORM-PSR、Gemini 3.1 Pro |
| 异常/恢复 | 时序分割模型用于阶段识别；LTContext/FACT 用于异常多标签诊断 |

论文配置：4×A100 40GB；冻结表征骨干，16 帧 clip、stride 1 提特征；按各方法默认参数和预训练权重运行。TAS 与跨视角等使用五视角；State & Reasoning 使用 front 视角。详细方法参数应以任务目录对应配置为准，不能把某一个学习率套给所有基线。[§5.1、代码 tasks](https://github.com/Kratos-Wen/IMPACT/tree/4fed5faa5f05f7aece55712e458defa1f372b248/tasks)

论文 Table 5（S1、front）的结果：

| 方法 | ASR Macro-F1 | ASR Trans-F1 | 最终状态准确率 | PSR POS | PSR F1 | Delay 秒 |
|---|---:|---:|---:|---:|---:|---:|
| MS-TCN++ | 0.84 | 0.33 | 0.93 | 0.21 | 0.26 | 8.46 |
| Gemini 3.1 Pro | 0.44 | 0.10 | 0.81 | 0.36 | 0.23 | 19.26 |

可以支持的判断是：VLM 的程序顺序分数较高，但完成事件的时间定位和状态识别仍弱；高最终状态正确率不代表过程监测准确。长程预测中 ScalAnt+I3D AUED=0.622，AntGPT=0.667，PALM=0.801，Qwen3-VL=0.827，语言模型并未自动解决多路线预测问题。[Tables 4–5、§5.4–5.5](https://arxiv.org/html/2604.10409v1)

### 4.4 官方协议与实际发布的差异

文档定义 S1 IID、S2 跨人、S3 跨设备配置、S4 外部视角→第一视角，并声明按 trial 分区以防跨视角泄漏。[§4.2、BENCHMARK.md](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md)

但本次下载的、通过官方公布 SHA-256 的 v1.1 包显示：

1. **TAS-S S1 的 448/56/56 是视角文件数，不是 trial 数。** 去掉视角后，训练与测试共有 42 个相同 trial。例：`AL07EJ17_Disassembly_A_002_top` 在训练；right/ego/left 在验证；front 在测试。与文档“同执行所有视角同分区”的陈述冲突。
2. TAS-S S2 的测试 trial 有 9 个也出现在训练。S3 测试为 B 型，训练/测试 trial 不重合，但训练/验证仍有交叉。S4 在同一批执行中用 exo 训练、ego 测试，属于**见过执行的跨视角迁移**，不能直接当作未见执行泛化；这可以是一个评测设定，但需明确披露。
3. ASR 和 PSR 实际只提供 **92 个 front 录制，64/10/18 划分**；该划分 trial 不重合。不能把论文 §5.1 概括的 112 个 front 视频当作每个状态任务的实际评测规模。
4. 文件名标出的配置为 93 个 A、19 个 B，而论文 §3.1 写 92/20。这里仅报告命名统计，未观看视频核定硬件型号。
5. 已公布的 Gemini PSR `procedure_graph.json` 是从 92 个视频挖掘的图，53 个节点、102 条边，置信阈值 0.9；metadata 明确标为数据挖掘前置关系，**不能当作人工工程约束真值图**。`procedure_info_IMPACT.json` 的 51 项是部件完成事件映射，也不是 51 条图边。图挖掘究竟是否限制训练集，需核对对应运行路径，不能仅凭这份静态图断言论文发生图监督泄漏。[发布图文件](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/tasks/PSR/gemini_3_1_pro/configs/procedure_graph.json)

逐项证据、trial 列表和样本在 [impact_validation.json](reports/impact_validation.json)、[data_audit.md](reports/data_audit.md)。以上均是发布资产核查，未据此推算论文指标的偏差。

## 5. 数据下载、历史资产和后续使用边界

完整路径、版本、体积、许可、获取状态见 [data_inventory.md](reports/data_inventory.md)。主要资产：

- CC4D：直接复用当前 `cc4d_annotations/`。全部非 Git 文件与历史目录同名资产 SHA-256 一致，且本地 commit 等于官方当前 HEAD。
- EgoErrorVQA：`annotations/egoerrorvqa/`，9 个 JSON，2,558,258 bytes；包含完整发布 VQA 标注与 31 个程序文本。
- IMPACT：`annotations/impact/IMPACT-v1.1-annotations.zip`，8,485,262 bytes；解压 7,216 文件、458,673,739 bytes。**解压体积主要来自逐帧文本标签，包内没有视频/特征/权重**。
- 补充上游：EgoOops 官方 metadata、Assembly101 的 mistake detection 标注、EPIC-Tent 官方标注，见清单。EgoErrorVQA 的派生问答不替代这些原始标签。
- 三篇论文 PDF 与可检索文本在 `papers/`；来源快照在 `sources/`；所有统计及前 10 条样本在 `reports/`。

历史目录 `/home/ldq/sop_work` 中的 QIC parquet、评测器和预测结果属于 *Can Multi-Modal LLMs Provide Live Step-by-Step Task Guidance?*，是 CC4D 派生的另一基准，不是这三篇的额外训练集。其 timed instruction/feedback 可作将来交互指导研究的线索，但任务标签、图和分区需要独立对齐。[QIC 官方说明](https://github.com/Qualcomm-AI-research/qualcomm_interactive_cooking_eval)

历史脚本里的“IMPACT 挖掘图 vs 人工图 15 vs 1”等数字未在本次原文中找到可直接对应的证据，不沿用为论文结论。历史模型预测也没有转换成真值或重新评测。

**基于以上证据的后续建议（不是已完成实验）：** 若研究跨场景错误解释，EgoErrorVQA 适合做评测入口，但必须固定采题、负时间处理和指标实现；若研究厨房 SOP 监测，CC4D 适合做基础标注源，但需要显式选 recording/person/environment 分区；若研究偏序任务图、状态约束及恢复，IMPACT 更匹配，前提是先明确资产版本、实际 trial 划分和图来源。三者都不宜未经审计就作为现成无泄漏基准直接启动大规模训练。

## 6. 2026-09-18：细节感知与单卡推理方案

完整方案见 [sop_detail_design.md](reports/design/sop_detail_design.md)：采用分层观察、可回溯事件/对象状态记忆、带时间和状态约束的 SOP 偏序图，以及证据不足时的局部高分辨率/高帧率回看。规范、视觉事实和推断分开存储；时长与前置条件由代码检查。在线与离线、原始 VQA 片段协议与完整视频监测分别评测。

依据新增原始来源：[VideoAgent](https://arxiv.org/html/2403.10517v1) 强调迭代取得回答所需证据，[VideoTree](https://arxiv.org/html/2405.19209v3) 使用问题驱动的分层视频表示。准确短引文和本任务可迁移/不可直接声称的结论均在方案 §1。本方案是待消融验证的组合设计，不声称其新颖性或最优性。

官方 Qwen3-VL-8B 配置为 262,144 上下文 token，常用视频处理器默认最多采 768 帧；帧上限可配且受分辨率/总像素/token/显存共同约束。BF16 8B 权重约 16.33 GiB，文本 KV 约每 token 144 KiB；全 256K KV 约 36 GiB，仅两者相加即超过 48GB。默认 768 帧和原生上下文都不意味着任意分辨率可运行。[配置](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct/blob/main/config.json)、[官方预处理](https://github.com/QwenLM/Qwen3-VL/blob/main/qwen-vl-utils/src/qwen_vl_utils/vision_process.py)

标注统计：选择题有效片段的时长中位数依次 CC4D 33.826s、Assembly101 10.917s、EgoOops 19.312s、EPIC-Tent 9.2s；CC4D/EgoOops 最长接近 9/10 分钟。详见 [统计与前十条时间样本](reports/design/ego_duration_stats.json)。当前标注不足以为全部工具、空间关系和有效活动时间提供完整独立真值，后续需要独立的小规模人工细节审计。

## 7. EgoErrorVQA 生成流程与 IMPACT QA 试制

专门调研见 [生成流程报告](reports/impact_qa/egoerrorvqa_generation.md)，实施入口见 [试制说明](reports/impact_qa/README.md)。EgoErrorVQA 开放题使用文本标注驱动 Qwen2.5-7B 生成，再由人观看视频审核和补题；MCQ 是固定错误体系下的类别判断，没有公开逐题四选一干扰项生成流程。

本轮 IMPACT 采用目标手/动作时间段为单位，保留 normal/anomaly/recovery 与六维多标签；Qwen3.5-27B 先观察视频，后对照标签整理事实，再生成开放题并独立请求审核。类别题保留原标注，不由模型猜测覆盖。112 个 ego 视频已校验，20 开发和 60 试制事件来自 80 个不同执行，标注时间以实际 PTS 对齐。所有自动结果均待人工审核，执行状态和最终产量以试制报告为准。

v7 最终完成 80 事件：84 对开放候选、80 条类别题；严格机器通过 47 对，不能当作准确率。已有开发样本的代理看帧检查为 8 保留/10 建议修改/2 建议拒绝。问题主要是小部件与细动作误读、无依据的方向/用力/结果、同模型共误。详见 [质量记录](reports/impact_qa/quality_status.md)。用户随后明确先满足 EgoErrorVQA 风格，因此下一轮以标注辅助的简短正确性、错误行为、纠正动作问答为目标，不要求每题具备完整规范图和因果解释。复用代理目视动作叙述帮助补足源数据没有错误自然语言描述的缺口，保留其非真人来源；事实正确性要求仍保留。[原流程与迁移依据](reports/impact_qa/egoerrorvqa_generation.md)

## 8. 实际视频输入格式与片段长度（2026-09-18 本地实测）

最新题型研究：[开放题全库与 Assembly101 专项](reports/impact_qa/question_taxonomy_report.md)。全库3560题，Assembly101 859题；按非互斥文本特征，装配/连接760、明确步骤完成68、遗漏70、多余81。官方回答模型确实接收 Task Procedure；发布的玩具装配规范是一份通用文本，不是各型号完整 DAG。[评测代码](https://github.com/z1oong/EgoErrorVQA/blob/5403cdd05e007b01c88448587c1a1803a27266e2/src/green_agent/agent.py#L680)。v10 设计恢复完整正常流程＋前置图输入，补充安装关系、完成、顺序、漏步等题型。IMPACT 的 ASR/PSR 提供状态/完成来源，但双对象关系、视角同步和规范权威性要单独处理；ASR -1→1 与 PPR recovery 不能直接等同。新增提示与输入契约已保存，尚未运行 v10。

后续执行更新：已进入 v10/v10.1 开发，详见 [方法与来源](reports/impact_qa/v10_method.md)。新下载官方 [Manual_Book.svg](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/Manual_Book.svg)，文字标题为“Reassembly”“Disassembly”，完整渲染后由研究代理对齐五个粗装配阶段；图示顺序用于 reference_order（是否按提供示意图的先后操作），不自动作为唯一合法顺序。论文原文 “multiple valid execution paths” 支持保留这种区别。[§3.1](https://arxiv.org/html/2604.10409v1)。接收部件关系优先从示意图与画面核对，当前仅手柄→齿轮箱壳体具有代理目视映射，仍待真人核验。

开发批次已完成至v10.2：12窗口24开放题＋12安装状态MCQ，已接入完整提供的图示流程、状态和前后步骤。原始输出、代理范围修订、待补视觉证据分别保留；[结果与示例](reports/impact_qa/state_qa_results.md)。确定性状态检查能避免字段/数值误配，但无法保证自然语言不扩大到整套组件，仍需逐题语义检查。该结论来自本轮具体失败与修订记录，不宣称已解决自动QA标注质量问题。

已新增三个 front 视频的逐帧实测：H.264、1280×720、30fps，5214/5126/5623帧，全部解码PTS等于帧号/30且与ASR帧数一致。因此后文“外部视频尚未下载”属于此前测量时的历史状态，不适用于本轮这三个视频。front ZIP通过官方SHA-256，按需解压，原ego数据保留。生成器使用完整公开参考流程＋状态/时间线，评测输入去除执行真值和候选挖掘图。

### 8.1 当前已下载的 IMPACT ego 视频

本地实测对象是 `/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/ego` 中的 112 个 MP4，而不是只根据论文名义参数推断。逐文件解析 MP4 容器、视频轨 `stsz/stts` 和 `moov` 元数据后，112 个文件完全一致地表现为：1920×1080、`mp4v`、24.917 fps、无非零码率音频轨；视频样本数与 `duration_sec × fps` 交叉核对全部通过。总大小 15,323,163,887 bytes（约 14.27 GiB），总视频时长 27,725.985 s（约 7.70 h），总视频帧 690,847。论文原文写的是 “one Tobii Pro Glasses 3 egocentric stream at 1920×1080 and 25 fps”；本地文件把名义 25 fps 具体实现为 24.917 fps。[IMPACT 原文](https://arxiv.org/html/2604.10409v1)；[本地逐文件统计](reports/design/impact_media_stats.json)

整段 ego 录制时长分布：105.471–1,027.010 s，均值 247.553 s，中位数 200.747 s，P25/P75 为 166.473/282.498 s，P90 为 366.778 s；整段帧数为 2,628–25,590，中位数 5,002 帧。也就是说，输入通常是 2–6 分钟、约 4–9 千帧的长视频，最长约 17.1 分钟、25.6k 帧，不是天然的短 clip。

外部视角的 MP4 尚未在本地，因此不能声称其容器编码或实际帧数已测出；标注元数据显示 front/left/right/top 均为 30.0 fps。论文对应描述是 “four Intel RealSense D455 exocentric RGB-D cameras … at 30 fps”。当前结论要区分“标注元数据名义帧率”和“本地媒体容器实测格式”。[IMPACT 原文](https://arxiv.org/html/2604.10409v1)；[本地统计范围说明](reports/design/impact_media_stats.json)

### 8.2 IMPACT 标注动作片段长度

对 `TAS-B/ego` 的 112 份文件逐段统计，13,148 条左右手原子片段的时间端点按闭区间帧号换算为秒。全部片段时长为 0.602–140.306 s，中位数 1.967 s，P25/P75 为 1.164/4.535 s，P90 为 9.873 s；其中 `action_label=0` 的 3,357 条背景/空动作段不应直接当作动作 QA 目标。非空原子动作 9,791 条，时长中位数 1.726 s，P25/P75 为 1.084/3.732 s，P90 为 8.629 s。

按 PPR 阶段，非空原子动作的数量和时长中位数分别为：normal 8,538 条、1.726 s；anomaly 1,068 条、1.605 s；recovery 185 条、1.164 s。最长 normal/anomaly/recovery 原子段分别为 140.306/93.711/10.916 s，长尾主要来自连续操作或合并标注，不能把中位数当作所有事件的固定窗口。用于当前 QA 试制的 0.5–35 s 过滤是实验抽样约束，不是数据集原生片段长度定义。

`TAS-S/ego` 粗步骤 4,423 段的时长中位数为 2.247 s，P25/P75 为 1.284/6.300 s，P90 为 17.657 s，最大 130.578 s；粗步骤和左右手原子动作是两个标注层，不能互换为同一片段集合。[IMPACT 标注结构](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md)；[本地统计](reports/design/impact_media_stats.json)

### 8.3 对 Qwen3-VL 输入设计的直接含义

若把整段 200 s 视频按 24.917 fps 全量送入模型，将产生约 5,000 帧，远超单卡推理的合理预算；即使只保留 32 帧，时间间隔也约 6.3 s，容易漏掉 0.6–2 s 的原子动作。当前更合理的单位是：以标注动作段或 2–4 s 重叠窗口为基本输入，先做目标密集抽样，再在动作边界、工具接触和异常候选处局部加密；跨窗口信息放进事件记忆，而不是把整段视频一次性塞入模型。768 帧容量测试只能说明合成张量可运行，不能把它解释成对这类 25 fps 长视频的直接端到端输入上限。[容量实测](reports/design/capacity_results.md)；[细节理解设计](reports/design/sop_detail_design.md)

按采样频率换算，整段录制中位数 200.747 s 对应约 201/401/803/1,606 帧（1/2/4/8 fps）；P90 录制对应约 367/734/1,467/2,934 帧。非空原子动作中位数 1.726 s 对应约 2/3/7/14 帧（1/2/4/8 fps），所以动作级 QA 可用 4–8 fps 的局部证据，长视频必须采用分窗与记忆。该换算只描述帧预算，不改变原始视频 PTS。[本地统计](reports/design/impact_media_stats.json)


## 9. v10.2直接质量复审：状态、动作与异常的边界

本轮源标注知情的研究代理检查了36题及22张图板（205个不同原帧），不是盲审或真人验收。结论：可保留部分SOP开发候选，不能原样扩量为异常理解数据集。[完整报告](reports/impact_qa/state_v10_2_independent_audit/quality_review.md)

可核验的本地证据：003末帧3016的TAS-S原字段为`"label": "insert_bearing_plate_assembly"`、`"has_anomaly": false`、区间2869–3768，TAS-B同刻双手均normal，而ASR的bearing_plate=-1。这支持“跨任务标签不可直接互译”，不支持重新定义全库-1或宣称原标注错误。[TAS-S源记录](annotations/impact/IMPACT-v1.1/annotations/TAS-S/front/AL07EJ17_Reassembly_A_003_front.json)、[逐题源字段及图证](reports/impact_qa/state_v10_2_independent_audit/per_question_audit.jsonl)。三个负例都截在首次-1后15帧，故选样器本身必须检查“尚在安装”和“已发生可见操作错误”的区别。

另一失败来自把组件状态自动改写为动作：TAS-S区分`retrieve_gearbox_housing`与`install_rotor_assembly`，原问题却称安装外壳。修订应从动作段与接收关系获得动作语义，不能仅由ASR=1推导。6条改写建议独立保存，原输出未覆盖。[修订建议及对应源段](reports/impact_qa/state_v10_2_independent_audit/revision_proposals.jsonl)

开放题全部为判断式，21/24为Yes，12道顺序题全Yes；MCQ语义恒选正确安装的基线75%。这是本开发批次分布检查，不是模型性能或论文全库统计。现阶段应修正采样与任务定义，并保留具体简单异常问法；不能只增加prompt同义表达来掩盖同一事实重复。


## 10. v11：视觉、GT事实和GT参考答案共同生成

用户明确要求生成阶段同时看到视觉证据与GT答案，已落实：由ASR/TAS-S/TAS-B构建逐题事实约束，GT参考答案是结构化标注的确定性推导，模型看原帧及GT后生成自然问答；后续源语义核验和不带GT视觉回答分别执行。这是本项目工程设计，非声称原论文方法。官方任务定义把组件状态、左右手phase和异常属性分开，原文“independently for each hand”对应手级范围。[官方说明](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md)；[具体输入输出及范围](reports/impact_qa/gt_v11_results.md)。

实践证据：GT的pick_up_phillips_screwdriver能支持“螺丝刀”大类，但当前图像不能独立分辨刀头；v11.1将三个工具问答降低到该大类，保留源GT原值。另一方面，三个state=0问题改问安装存在性后，独立视觉模型虽答No，却仍有错认部件的解释，故未作为充分视觉验收。这说明正确答案与正确证据也应分别检查。[原题与无GT回答](outputs/impact_qa/gt_v11/open_candidates.jsonl)、[修订与回答](outputs/impact_qa/gt_v11_1/open_candidates.jsonl)。

最终24开放＋24MCQ，逐题代理复审15个题意优先候选/9暂缓；7 Yes/7 No/10描述题。GT引用全部可追溯，但未解决具体异常机制、部分部件身份及精确时长边界问题，不等于异常数据集完成。采样使用GT边界，必须声明为标注辅助分段协议，而非端到端无分段评测。


## 11. 复查与扩量标准

新协议将源支持、视觉可回答性、时间范围、问答表达、MCQ唯一性和数据隔离分开记录，采用先隐藏GT回答、再揭示GT对照的复查顺序。设计依据是本地v11.1出现“答案No符合GT，视觉解释却把适配板当轴承板”的具体失败；详见[原审核输出](outputs/impact_qa/gt_v11_1/open_candidates.jsonl)与[验收协议](reports/impact_qa/review_and_scale_protocol.md)。这是本项目建议的工程控制，不声称来自论文固定标准。

总体≥95%、每类≥90%、严重缺陷0等是建议放行阈值，不是测得准确率。验收应在未用于调参的trial上执行，QA同trial相关，不能根据数百QA简单宣称独立统计保证。官方ASR split1按workflow分层，元数据原文为“workflow-stratified random search minimizing state_changes mean drift”；参与者跨集合重叠。[源划分](annotations/impact/IMPACT-v1.1/annotations/ASR/splits/split1_summary.json)。本项目验收划分与官方test用途需区分。

## 12. v12跨执行开发：GT支撑与视觉确认仍须分开

8个trial/8参与者共93题意，开放与MCQ各93；完成自然措辞/干扰项、时钟/问句次序两轮修订。本节是本项目实测和工程设计，不归为EgoErrorVQA或其他论文提出的方法。[结果与完整证据](reports/impact_qa/gt_v12_results.md)

三个可核验失败决定了下一步方向：

- 时间表达冲突：v12.1的KI03AR28正常动作复核写“frames (0.0s to 1.2s) do not overlap”，把短片相对时间与原片3.6秒开始混淆；v12.2在公开输入中显式给出换算及四张锚点映射。[原记录](outputs/impact_qa/gt_v12_1_development/runs/gt_5b0646084efcf9bfd9ba.json)
- 答案位置提示：此前全部24道顺序MCQ问题先提及的动作就是先发生的动作。改为不依赖时序的字面排序，现14/24，仍需记录真实步骤分布偏置。[修订合同](outputs/impact_qa/gt_v12_2_inputs/contracts.jsonl)
- 自信不等于一致：LE07UF17工具源动作是`pick_up_combination_wrench`，无GT回答却为“A small silver screwdriver”；这是源与模型回答冲突，不足以判原GT错误。类似分歧共11条。[分歧队列](outputs/impact_qa/gt_v12_final/gt_visual_disagreements.jsonl)

225个源引用机械核验和93组模型语义审核通过；无GT视觉自报50可回答，其中11短答案冲突、39表面一致。16异常属性题无一自报可回答。研究代理实际看过51个题意的抽帧板并读全部问答，未连续播放，也没有真人签署。不能把来源正确当可见性正确，不能用自报可回答比例代替验收。

下一步“动作起点局部帧＋全程概览＋操作区裁剪”由本轮24.267–287.1秒顺序窗口仅16视频帧、微小工具混认等具体证据驱动。保留全幅上下文与原时钟；GT辅助取窗协议公开声明，按时间排列帧不能携带“这个是正确动作”的标签。统一部件图册只提供身份，不标出本次执行结果。[媒体与分层数据](reports/impact_qa/gt_v12_final_summary.json)

历史隔离审计也修正原计划：train bundle实际31装配/33拆卸，与summary各32不同；保留池仅6条相对已查v7/v11历史未暴露的装配trial，另10条是暴露过的回归集。不能为满足16trial目标把回归集冒充独立验收。保留trial本轮未生成或查看新视频证据。[来源与暴露清单](outputs/impact_qa/gt_v12_split_manifest.json)


## v13：视觉密度与标签粒度的实证诊断（2026-09-19）

本节为本地开发实验观察和待验证设计，不作为论文已有结论。固定33题主对照发现：工具全幅均匀2/7短答案一致，局部密集7/7；顺序局部密集3/8，加入另一训练执行的具名动作演示5/8，再加入无序粗细标签关联6/8。官方无标签图片没有增加总体一致数。核心证据及输入差异见[完整实验报告](reports/impact_qa/gt_v13_results.md)、[逐条比对](outputs/impact_qa/gt_v13/compared_results.jsonl)。这些数字不是独立准确率。

“粗细标签关联”定义为：另一训练执行中，normal原子动作时间中心落入某粗步骤，过滤通用/跨步骤共享动作后保留关联，不含先后约束。源原词如`install_rotor_assembly`与`insert_bevel_gear`说明粗步骤可以从子组件动作开始；这不保证目标图中物体身份已识别。示例和关联的源JSON pointer、原值及哈希保存在[provenance](outputs/impact_qa/gt_v13_action_reference/glossary_provenance.json)。下一步应先得到带帧号的动作身份证据，再计算实际顺序，不能依靠描述性流程猜时间。

安装prompt的正例结果有明显误导风险：4正例均与GT一致，但加入2个未安装反例后为5/6，gt_21ecb41eb954e9d7a907由原C的No退化为Yes。模型原文“bearing plate assembly is visibly inserted”与GT不一致，说明部件/关系判断仍有问题；看见连接也不足以验证牢固或整体完成。[6题原输出](outputs/impact_qa/gt_v13/install_state_strict_results.jsonl)。不采用该prompt作为全局状态默认值。

6异常＋4正常题四条件全部弃答；研究代理直接查看这些图板仍无法确认具体错误机制。后续异常QA需要原生属性、实际动作对象、可见偏离及适用规范共同支持；仅有宽泛异常标签不能产生有依据的错误原因与纠正措施。当前分题型输入建议仅为开发策略，[策略文件](outputs/impact_qa/gt_v13/recommended_input_policy.json)未放行生成。保留6个未暴露trial；实际目视25个目标图板，真人/连续播放均0。


## v14：全量候选门槛与工具类开发（2026-09-19，验收前记录）

先固定[候选最低要求](reports/impact_qa/full_generation_requirements_v14.md)：来源与隔离100%、严重缺陷0、综合≥95%/每类≥90%、具体视觉证据≥95%、完成率≥99%。有限训练装配候选覆盖最低每类30事件/5trial/3参与者；原16trial/8参与者广覆盖目标仍未满足。阈值为项目工程约定，不归于任何论文。机器门槛拒绝缺失数值、非有限数值、GT泄漏、版本不匹配与仅模型自审。

v14使用8开发trial全部46个合资格normal工具拾取事件，而非上轮7题。GT驱动受限问答（原问题＋原答案逐字校验）及代码置换三选一，模型生成时同时看GT和视觉；这是固定工具题模板验证，不宣称开放语义多样性。首轮GT隐藏复核38一致/7弃答/1冲突。第二轮在原视频同帧上增大操作区有效像素，并要求前后帧，40一致/6弃答/0冲突；原扳手冲突修复但1旧成功样本转弃答。空间输入和prompt同时改动，不做单变量归因。[v14.1结果](reports/impact_qa/gt_v14_1_tool_normalized_full_summary.json)

直接查看46个事件四帧概览及40组保留候选的证据对。工具工具大类QA有可见支持，但一条模型before端点已拿着工具，说明结构化证据仍不是可靠GT。冻结输出只包含来源答案与选项，私有模型观察文字不进入金标准答案。6弃题另列，模型弃答不证明问题无效。全部开发样本40螺丝刀/6扳手且46右手，保留自然分布声明，不冒充平衡或左右手泛化。

“在途请求合并”指相同完整请求同时到达时共用一个异步任务，各调用者拿深拷贝结果，失败清理后可重试。受控假后端测试通过；冻结旧API不修改。模型经常将transport标签`Frame target_0`带入证据ID，新增可追溯去前缀，不改变工具答案、时间或原响应；未知ID仍报错。

异常继续单独推进：8开发trial原子标注212个异常事件，字段原名`action_label`、`anomaly_type`、`entity`、`start_frame`、`end_frame`等，没有自由文本的具体错误机制；源字段不足不代表视频推理永远不可能，但不能直接将属性改写成无依据错因。[异常清单](outputs/impact_qa/gt_v14_anomaly_inventory/events.jsonl)。工具类通过也不等于异常理解目标达成。

### v14冻结验收：过滤后的质量与覆盖必须分开

固定15文件后，在6个此前保留训练trial/5参与者的全部33合资格事件运行：28一致保留、4弃答、1冲突，全部运行完成。先保存研究代理不看GT/模型的33条图像回答，再对照GT：32可辨认、1不确定；对28保留候选及5弃题全部检查。28候选的源答案、视觉支持和选项均通过本次代理审查，但低于事先30独立合格事件门槛，自动放行false。[验收报告](reports/impact_qa/gt_v14_results.md)、[原始盲答](outputs/impact_qa/gt_v14_frozen_acceptance/blind_review/agent_final_blind_answers.json)

具体失败证据：tool_3314f7a4b94ffb531074的模型声称“no tool is lifted into hand”，而target_13至15可见红柄螺丝刀被拿起；tool_4a95d379a9a829ffc979模型写“flat metal wrench”，实际绿柄杆状工具离桌、银色扳手留桌。4个可辨认却未保留的事件集中于同一参与者两段执行，支持继续分开验证物体身份、接触/拾取和前后状态，不能依赖单一自报answerable。[保留原响应](outputs/impact_qa/gt_v14_frozen_acceptance/results.jsonl)、[逐题归因](outputs/impact_qa/gt_v14_frozen_acceptance/agent_adjudication.jsonl)

本轮结果限定于一种工具大类问法和右手normal拾取，保留25螺丝刀/3扳手。28/28是这个小批筛选后的代理审查比例，不是人工金标准或总体准确率；同trial样本相关。6个保留trial现已消耗，再据其修订就只能用作回归。不得补入开发题、重复改写或改变冻结过滤来凑30。[暴露清单](outputs/impact_qa/gt_v14_exposure_manifest.json)

## v15：按时间排列输入与证据仲裁

实际请求有时间回跳：先4张全窗context，再从动作起点给16张target。只按时间重排同20图，原46开发短答案一致40→43，没有开发回退；33已暴露回归仅28→29，仍有误认和旧成功回退。这支持修复媒体顺序，但不支持宣称模型漏判已经消失。[完整对照](reports/impact_qa/gt_v15_comparison.json)

身份/前后状态分解、端点高分辨率、提示比较移走/留下工具、两面板复合图及8B跨模型诊断均未得到可替代直接复查的稳定改善。例子tool_de3175ea544adfb611e7的endpoint8模型声称“green-handled screwdriver”，实际绿柄工具留桌，银色扳手离桌；源和直接图像支持正确QA，不应由错误盲答直接丢弃。[原模型输出](outputs/impact_qa/gt_v15_tools/endpoint8/exposed_regression/full_results.jsonl)、[图证](outputs/impact_qa/gt_v15_tools/endpoint8/exposed_regression/full_review/tool_de3175ea544adfb611e7.jpg)。未采用方向移入[archive](archive.md)。

“证据仲裁”在此仅指研究代理或真人直接检查原图与来源，记录支持或不确定后处置模型分歧；不是模型投票或多数一致。最终采用原20图时间排序作为主复核，弃答/冲突进入直接复查队列，未审核不通过，模糊继续hold。76支持事件中72为主复核提出、4为有记录的直接复查追加；3继续hold。答案锁定GT，私有模型说明和端点不作为gold。[实现和结果](reports/impact_qa/gt_v15_results.md)

本轮增加两张同刻细节图供审核，最终公开输入为22图，未新增时间点；8帧或并排图不作为最终评测协议。已有审核只在问答和原图核验一致时继承；新增难例显式记录。本轮属于源知情研究代理抽帧审查，不是真人、连续播放或新独立验收。旧回归支持数32不能覆盖原冻结筛选28的结果，全量仍未放行。

## v16工程修订：多角色证据筛选（2026-09-19）

根据本地v14/v15逐事件记录，合法证据ID不保证视觉语义支持；同GT一致可能同时存在错误端点，旧生成轮又主要复述固定问答。因此新增GT＋视觉出题、无答案视觉盲答、无GT逐事实/逐选项反驳审核、文本源语义核对四角色。此为本项目工程设计，不声称EgoErrorVQA原样使用这四步或已经最优。依据：[v15实测报告](reports/impact_qa/gt_v15_results.md)、[新流程及边界](reports/impact_qa/quality_v16_design.md)、[17混合冒烟结果](outputs/impact_qa/quality_v16_smoke/summary.json)。

术语model_passed_unvalidated仅指通过模型及代码筛选、未经独立质量验收的候选。0–3“证据等级”是未校准自报可见性分级，不是概率；三视觉角色取最小值且全部硬条件同时成立才保留。不输出长CoT，以原子事实和可核验引用代替不可审计的长解释。四角色复用同模型，因此不能据一致率估计独立正确率。

## v17：按题型检索充分数据，先资格后生成

本地对照的具体依据：v16四阶段生成230事件，75模型通过；追加只看所引两帧的工具复核后，68工具中仅29被该模型确认。此差异证明“答案一致”“引用字段有效”“所引证据充分”不能混为同一指标，并不等于原QA真值错误46条。原始记录见[证据复核](outputs/impact_qa/quality_v16_evidence/results.jsonl)。

采用事件证据包组织任务GT、完整公共流程、私有执行上下文、异执行动作参考、目标视觉及缺失项。公共流程直接复用[官方手册本地文件](sources/impact_docs/Manual_Book.svg)及已有核验转录，保留原限定“not a uniquely mandatory ordering”；工程方案不是一项论文实证方法。对源类别不能支持的因果、接收关系和强制依赖保持禁用。完整设计见[evidence_package_v17_design.md](reports/impact_qa/evidence_package_v17_design.md)。

230包/2653上下文源引用，固定17补锚点及公开参考的资格试验6可出题/8缺证/3校验拒绝；6随后真实生成＋交叉审核仅1候选。当前丰富输入仍不能保证部件识别正确，未宣称性能提升。该1例与旧批次重叠，不增加独立样本数。

## v18：完整输入物化与格式校验归因

### ATR片段与视频输入试验（2026-09-20）

ATR可提供明确同手异常段、多标签和来源动作，现已固定17事件配对研究。逐题审核后ego16/front12模型筛选题；这不是独立质量估计。6配对图板直接观察显示ego有近景优势，也有头向偏移导致操作出画的反例。见[ATR结果](reports/impact_qa/atr_v19_results.md)。正确工具和及时性仍缺规范工具/时限GT，未凭后续换工具杜撰答案。

按用户要求实现原生MP4输入。工程依据为本机vLLM0.18.0源码`compute_frames_index_to_sample`：fps与帧上限取较小采样数，均匀覆盖首尾；HF禁二次采样。目标8fps/64帧、上下文2fps/64帧，长段重叠切窗。真实18请求均返回但3选项格式拒绝；扳手无GT视频仍误认，不能宣称视频优于定点图片或ego必然优于front。[配置、源码依据及实测](reports/impact_qa/video_v20_configuration.md)。这些是本项目工程结果，不是原论文实验结论。

### v1.1标注结构复核与勘误（2026-09-20）

全量核验TAS-S 560文件/21995段，`has_anomaly`全部false、`meta_activity`全部none；因此历史文档中引用粗步骤false只应视为原始字段值，不能支持“步骤无异常”。异常GT须从TAS-B的phase/六属性获得。[核验统计](reports/impact_qa/annotation_schema_audit.json)、[详细字段说明](reports/impact_qa/annotations_explained.md)。示例419–461的逐帧标签包含461，发布ATR段259–279的num_frames=21，明确这类原始边界为含端点；历史派生exclusive命名仍需另行审计，未回写冻结结果。

v17的230证据包现均具备真实媒体输入，新增213事件取帧，原17保留。去重核验5371媒体hash/2129源引用；与v17的2653上下文引用次数不是同一统计口径。依据：[v18预检](reports/impact_qa/evidence_v18_precheck.json)。

对v16失败归因发现，把25词说明上限当硬语义标准会误拒结构正常的输出。离线重放19例，12仅私有文字超建议；保持全部语义门槛后，其中8仍隔离、4仅恢复为待审候选，不能宣称准确率改善。v18保留原文、仅给style_warning；公开问答长度、错误证据与GT冲突仍拒绝。原始记录和可重放统计见[evidence_v18_validation_replay.json](reports/impact_qa/evidence_v18_validation_replay.json)。这是本项目工程校验修订，不是论文方法结论。

v18最终230事件生成161组草稿，33工具候选完成全部模型筛选；77非工具无最终保留。[完整统计](reports/impact_qa/evidence_v18_final_summary.json)中的“formal_release: false”保留。33候选仅1种问法，31螺丝刀/2扳手且全部右手；即便粗粒度视觉判断成立，也不能作为安装/异常理解覆盖已达成的证据。代理直接查看33前后图，[观察记录](outputs/impact_qa/evidence_v18_review/agent_direct_observations.jsonl)限定为“supports_generic_tool_pickup”，不扩张到正确安装、工具型号或异常原因。

当前工程判断：下一步瓶颈是可见实体和GT部件名对应、连接状态及动作起点，而非单纯增加文字上下文。[失败分析](reports/impact_qa/evidence_v18_analysis.json)记录身份参考需求16、同步视角20、规范来源21（多选，非独立计数）；89语义隔离都含盲答证据不足。这支持先补对应证据、在新版本短路明显不足事件的实施优先级，尚不证明这些补充一定改善质量。全部数据来自已暴露训练事件，正式独立验收仍待建立。


## v21 当前生成目标：详细视觉描述 → 描述性开放QA（2026-09-20）

用户本轮明确改变输出目标，后续以[descriptive_v21_design.md](reports/impact_qa/descriptive_v21_design.md)为当前设计。旧方案保留用于复现，不再指导新出题。工程依据来自本地旧prompt，而非未经核验的论文归因：旧[v19/generate.txt](prompts/impact_qa/v19/generate.txt)明确写“open and three-option MCQ pairs”和“Answers <=65 words”，直接造成输出类型与详细描述目标不一致。现取消强制配套MCQ和65词限制；开放题只描述可见事件，固定MCQ由明确GT独立构造。

新术语“逐帧卡片”指每个目标原始解码帧对应的可读观察记录，不是隐藏CoT；“事件表”指带帧引用的可见状态变化及先后，不是规范拓扑图。目标默认原始帧全覆盖；视频8fps分支只辅助动态观察，前后文2fps明确标注采样。帧覆盖完整不保证内容正确。GT核对阶段将annotation facts与visual facts分开，不能用标签补画面细节；首次观察不给GT，后续叙述/出题仍得到视觉和GT核对信息。

当前产物为设计、六个prompt、三个虚构few-shot和Schema/配置；尚无v21推理结果或质量提升证据。不新增论文方法效果主张。少量试跑、事实支持率/遗漏审核及人工视频核验是后续验证项。


### v21真实小样复查结论（2026-09-20）

[实测报告](reports/impact_qa/descriptive_v21_pilot_review.md)记录75次真实请求。逐帧覆盖和更长答案不保证动作理解：首8帧冗长输出5444token/169.27秒，紧凑版1394token/44.67秒，但仍漏可见变化。发生few-shot虚构答案46词连续复制、front操作者手别反转、动作/时间引用错配，同模型审核会漏错。密集56原始视频帧＋8静态图修订仍出现扳手插入的未证实事件，不能声称更多帧解决了视觉证据问题。

本机vLLM源实现原文“the minimum of the two will be used”见[video.py](.venv-impact/lib/python3.12/site-packages/vllm/multimodal/video.py:372)，对应fps/num_frames取更小约束。64帧672×384与128帧480×256采用相同总时空像素预算；两次128帧均HTTP推理成功，分别因输出截断与错误引用而未通过质量校验，不是OOM。本轮尝试官方在线文档工具返回404，容量解释依赖本机安装源码和真实请求，不冒称最新远程文档核验。

工程改进优先级：静态状态→前后转变→受限ID引用→GT视觉冲突核对→已核验事件表转写QA→实际引用图审核＋人工核验。不是已有论文验证的收益结论。详细事实、反例和文件路径均在本轮报告。

## 长视频QA构造调研（2026-09-20）

完整原文依据、方法对比和迁移边界集中在[调研报告](reports/impact_qa/long_video_qa_generation_survey.md)，原文快照及哈希索引在papers/long_video_qa_survey_20260920。此次只调研，未新增模型实验。

最相关组合是标注驱动出题、分层事件记录、按问题回看视觉和人工核验。EgoErrorVQA明确写“Our generation process is purely text-based”，生成真值依赖已有步骤/错误标注及后续人工观看，不是让VLM凭视频自由造答案。[原文](https://arxiv.org/html/2608.24134v1) LLaVA-Video用“Every 10 seconds”“Every 30 seconds”分层描述，再生成QA；1fps和0–3分钟数据设定不能直接推出工业细节或小时级可靠性。[原文](https://arxiv.org/html/2410.02713)

可靠长视频benchmark仍依赖高质量叙述和人工：HourVideo要求“human feedback for all”；EgoLife称模型是“filtering and inspiration tool”。[HourVideo](https://arxiv.org/html/2411.04998v1)、[EgoLife](https://arxiv.org/html/2503.03803) 新预印本CapMem以“captions as a semantic index”组织记忆，支持将摘要用作找证据的入口，不等于摘要成为GT。[原文](https://arxiv.org/html/2609.17688v1)

新术语：原子事件表指带源时间、实体标识、前后状态和媒体引用的局部观察记录；层级记忆指局部事件上方的步骤/全局检索摘要；两者都不自动是真值。已发生顺序图记录实际行为，规范顺序图记录有来源的应然约束，二者必须区分。下一轮工程建议见plan.md与调研报告，不将建议写成已验证收益。

### v22对调研方案的实际检验（2026-09-20）

[实测报告](reports/impact_qa/event_v22_results.md)显示事件表/逐事实复核能限制答案新增句子，但不能保证事件真实。27B与8B都在候选审核中认可f0000717的虚构插入；[该帧](outputs/impact_qa/descriptive_v21/frames/atr_17fd15858f5679ef_ego/f0000717.jpg)可见工具与部件分开。多模型同意不是独立真值，GT核对也会把错误物体名合理化。

代理先看图建立22条保守事件后，生成6开放QA全部原句保留；来源明确为代理辅助非自动或真人gold。这一对照仅支持“已知事实→问答组织可受控”，不支持“自动视频理解已解决”。单帧无候选观察在个别关键帧避免插入推断，但仍误认物体和接触对象。局部事实可靠性不足时暂停层级历史扩张；文献中的高质量人类叙述/校对文本前提在本项目同样不可省略。

### 用户新方向：连续视频history小样v23

用户提出2秒连续观察→保留history→整合动作→ATR辅助出题，优先验证上下文组织，不以v22局部失败概括模型能力。实现完整描述账本、最近两段和滚动状态摘要；与LLaVA-Video分层描述“Every 10 seconds”“Every 30 seconds”的思路有关，但2秒设置是本项目选择，并非原文参数。[论文](https://arxiv.org/html/2410.02713)

[v23实测](reports/impact_qa/history_v23_results.md)：两视角16clip完成，20事件均被整合引用，ego保留取工具/持续操作/末端移开，生成6题后隔离1否定题。每视角8描述只有3种不同文本，仍需检查记忆重复与遗漏；这是可行性小样，不是可靠性定论或整条长视频复现。新增真实人工记录仅一条v22辅助片段“通过”，不迁移为v23标签。

## 2026-09-20：以具体操作判断取代描述型题目

EgoErrorVQA论文称“Our generation process is purely text-based”，依据流程和步骤错误信息生成，再通过视频人工核查；[论文](https://arxiv.org/html/2608.24134v1)。本地Assembly101开放题859条中707条以确认式问句开头（82.3%，正则表面计数，非官方语义分类）。因此开放QA可以是“这一步是否正确完成”的问题，答案用自由文本解释；详细描述和history应保留为证据层。具体样例、源文件hash与v24实验见reports/impact_qa/step_v24_results.md。完成性需要目标部件的结束状态；ATR错误类型只支持相应错误判断，不自动决定安装状态。

## 2026-09-21：已认可方法进入批次生成

用户批准v24方式并授权开始后续生成。沿用此前EgoErrorVQA式具体操作开放问答（自由文本答案可对应yes/no问题），将2秒描述/history作为证据。批次区分ASR部件末态问答与ATR操作异常问答，来源作用域不可混淆；实现和实际费用记录见plan.md的v25节及reports/impact_qa/batch_v25_status.md。

新增数据划分核对：各任务官方train并不等价于跨任务、跨视角的试次互斥。此批是训练数据扩充，不用于独立验证成绩；正式评测需要先以源试次划分，再放置同源的全部QA，避免视频派生样本进入两侧。具体重叠计数在outputs/impact_qa/batch_v25/split_audit.json。

## 2026-09-23：从时间清单改为整体操作 QA

用户对 v26 冒烟结果的直接反馈是：原动作题主要输出动作时间和序列，没有先回答“整体做了什么、用了什么工具、处理了哪些部件”。因此本轮把 action_sequence 定义为两层答案：第一条事实是整体装配/拆卸摘要，列出工具和部件；后续事实逐条覆盖 TAS-B 动作，保持手别和顺序。时间区间仍作为私有证据字段保存，但不再进入公共答案前缀或模型要求的时间表。

这个取舍与 EgoErrorVQA 的已核验生成边界一致：论文明确写过 **“Our generation process is purely text-based”**（[EgoErrorVQA 原文](https://arxiv.org/html/2608.24134v1)），说明标注驱动的问答生成可以先由文字事实约束；本项目把该约束具体化为整体事实＋原子事实，而不是让模型从视频自由概括。该引用支持生成输入的来源边界，不证明本轮模型答案已经正确。

当前整体事实不把重叠的手和工具强行绑定到某个部件；只有 TAS-B 明确提供关系时才使用“工具—部件”对应。这样保留用户需要的工具/部件完整行动概览，同时避免从两个并行手部标签推断未标注的机械关系。所有事实仍带 source IDs、事件 IDs 和原始区间，便于审核页面只显示 QA、需要时再回看 GT。

本轮新增 `component_v26_gt_r1` 作为纯 GT A 方案：先验证标注驱动的整体行动答案，再决定是否恢复视频 B 对照。Qwen3.8-27B 权重尚未完整，尚未产生该版本模型输出；旧 Qwen3.5 结果不能当作新 prompt 或新模型的质量证据。

### v26 GT-only 完成记录（2026-09-23）

上一段是启动时状态快照；随后 Qwen3.8-27B 下载、双服务预检和 GT-only 生成均已完成。23 个 clip 的 154 条开放式候选全部通过自动结构/事实复核；人工视频只作为页面审核证据，不改变本轮“模型只输入 GT”的实验条件。全量审计未发现 action_sequence 的时间戳前缀、整体摘要缺失或 fact 顺序缺失。该结果证明当前输入合同能把答案组织成“整体操作摘要＋原子动作序列”，不证明视觉理解质量或人工验收通过；正式发布仍保持关闭。

## 2026-09-23：v27 异常动作规则与视觉证据

2026-09-27修正：本节为空握/共同持有等候选行为设置的规则仅保留为历史记录，不是六类异常的充分判据；后续以文末“六类异常判定依据核查”和独立reference prompt为准。

本节记录项目的异常证据操作规则，不将其称为 IMPACT 官方类别定义。v27 选题 prompt 用 `ERROR RULES` 单独标记：ATR 至少 5 秒异常区间内，操作进行时手持工具却明显未对工件使用（“empty holding”）；或放回/摆放一个部件时仍握着另一个部件/工具，且画面可见地干扰释放、摆放或交接；反复无效操作、明显错误对象也只在动作直接可见时计入。正常拿起、持有、短暂停顿、遮挡或动作意图不清楚，不自动判错。

异常类别仍由 ATR GT 固定；候选筛选使用视频＋GT，之后单独运行不看异常标签的盲视觉检查。每个异常时间段需要引用该时间段内的源帧并描述具体可见动作；没采到区间内证据帧、或盲审判断不可见的区间不进入最终 MCQ 答案。64 帧预算下优先覆盖长 ATR 异常段的中心与边缘，再补 TAS-B 动作中心和全片均匀上下文；每帧保留原片帧号和时间映射。

这些规则落实为 prompt 与程序验证，不是论文结论；schema/区间检查和同模型复核都不等于真人视觉判断。r5 小样的实际服务量、模型选择、候选题型与发现的时长区间重叠问题见 `experiment_log.md`。时长题须使用完整组件状态操作的完成帧；同一目标的状态操作窗口和较宽 episode 窗口重叠时，不能把它们当作两个可独立提问的动作。

## 2026-09-24：组件 clip 时长审计与修复证据

这是对本项目 IMPACT 标注切分的工程实测，不是新的论文方法结论。旧实现的装配边界在 [`v26_data.py`](impact_qa/v26_data.py:172) 中按 ASR/TAS-S 完成锚点加2秒，并在 [`v26_data.py`](impact_qa/v26_data.py:248) 无条件加入视频末尾；拆卸则在 [`v26_data.py`](impact_qa/v26_data.py:213) 明确保留带4秒前后文的独立重叠窗口。旧 all-splits 文件的实测结果是765个原始clip中113个小于3秒，最短0.033秒，且短片全部为装配片段。

修复遵循一个可审计的原则：合并相邻边界不会引入新时间区间，只把无法支持稳定视觉理解的短分区归入相邻较长分区；拆卸窗口只在源视频内扩展，不改写操作标注。实现位于 [`clip_repair.py`](impact_qa/clip_repair.py:19)，索引阶段在 [`v26_data.py`](impact_qa/v26_data.py:397) 同时保存 raw/repaired 两套记录。这个选择的依据是本地标注覆盖对照，而非假设模型一定从更长片段获益：修复后有效 TAS-B 事件完整包含数由9984增至10037，ATR错误完整包含数由1391增至1397，说明合并至少减少了边界截断；视觉准确率仍需真人审核。

新版本的最小片段门槛为3秒。全量索引结果为原始765→修复652→含有效TAS-B动作的manifest 651，修复后最短4.467秒；112个装配视频的首尾及相邻边界检查全部通过。可复现统计和断言由 [`audit_clip_splits.py`](scripts/audit_clip_splits.py:63) 生成，结果保存在 `outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix3/clip_split_audit.{json,md}`。该版本仍有111个manifest片段至少60秒，最长706.97秒；长片段不能用固定秒数切分解决，否则可能重新制造短尾片段，下一步应依据组件/动作边界另设策略。

### v28 clipfix3 全量生成结果（2026-09-24）

新版全量流程将同一条完整 clip 和结构化 GT 同时交给模型：先按候选题型选择，再为选中的开放题生成公共问题和答案，最后用同一 clip 的视觉帧、GT事实和来源ID自动复核。代码只确定性构造固定异常 MCQ 的选项/GT答案，视觉检查负责确认异常是否在对应 ATR 区间可见。这个流程边界延续了本项目对 EgoErrorVQA “Our generation process is purely text-based” 的来源约束理解，但本轮具体结果是本地工程实测，不是对论文性能的复现结论。[EgoErrorVQA原文](https://arxiv.org/html/2608.24134v1)

651个修复后 clip 全部完成，生成2312条开放式QA：整体操作651、组件完成性923、操作时长417、详细操作250、观察顺序71。Qwen自动复核保留2285条、挂起27条；挂起题仍保存在结果中，不能把自动keep当作真人准确率。141个固定ATR异常候选中，仅4个进入视觉盲检查，均没有在异常区间确认具体可见错误行为，所以没有导出MCQ。该零MCQ结果体现了视觉证据门槛，并不表示141个ATR标签没有异常。

可复现结果见 [`full_run_audit.md`](outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix3/full_run_audit.md)、[`full_run_audit.json`](outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix3/full_run_audit.json) 和 [`audit_component_v27_full.py`](scripts/audit_component_v27_full.py)。审计确认题目ID无重复、题目均绑定manifest clip、证据帧均属于相应输入、媒体路径无断链、合同问题为0。自动hold主要集中在组件最终状态与视觉画面不一致的完成性回答；在真人逐题审核完成前，`formal_release`保持关闭。

### v28 clipfix4：source-end 清理尾巴（2026-09-25）

短片时长门槛本身不能识别“有意义动作”：有些4–5秒片段包含真实收尾操作，有些同样长度的片段只是视频末尾的工具收纳、部件放置或 recovery。用户复核的两个 KJ03 尾片段属于后者。工程上新增了一个更窄的语义过滤条件：必须同时是视频末尾、没有有效ATR、没有高层TAS-B组件操作、也没有核心安装/拆卸动词，才从 manifest 排除。这样不使用模型猜测，也不把所有短片段误删。

过滤后 manifest 从651降为648，排除3个明确尾巴，最短剩余片段4.80秒；未改变片段的模型结果直接复用，QA从2312降为2309。`tail_excluded.jsonl` 保存每个排除片段及原因，`clip_split_audit.json/.md` 和 `full_run_audit.json/.md` 记录新计数。该规则仍是本项目的工程清理策略，不是 IMPACT 官方标注定义或论文方法结论。

## 2026-09-25：IMPACT 工具、部件与 A/B 型号知识块

这次调研的目标是给后续 VLM 生成提供一个短而可审计的对象背景，不把百科知识当成当前 clip 的事实。论文 §3.1 将任务概括为 **“12 components and 4 tool types”**，说明官方图示的物理类别是 12 类；本地 PSR `component_names.json` 进一步将 Model-A 的五颗螺丝和两颗 M4 螺母按位置拆开，因此 ASR 实例为 17 个。论文还明确两配置 **“differs in component connectivity and required tool operations”**，并用 **“partial-order prerequisite graph”** 描述流程约束，支持把 A/B 背景分开、避免把展示顺序当作唯一顺序。[论文 §3.1](https://arxiv.org/html/2604.10409v1)

官方固定 commit 图例把四种工具标为 A–D：A 一字螺丝刀、B 十字螺丝刀、C Torx 六瓣梅花螺丝刀、D 两用组合扳手；图中 A/B 又分别标出两种角磨机配置。手册图示和 GT 定位帧支持保守的工具—部件参考：A 型十字改锥用于适配板长螺丝，配对应 M4 螺母；Torx 用于轴承板和拨杆螺丝；组合扳手用于内部六角螺母；已核对的 B 型轴承板拆卸片段使用一字改锥。它们是型号/任务的参考操作，不能覆盖当前 clip 的 GT，也不能从“拿起工具”推断已接触或已正确紧固。

部件功能采用三档边界：官方图例或原始字段为直接来源；在手册/视频中清楚可见的外观和紧固关系标为视觉支持；“适配、支撑、传递旋转、弹性回位”等是基于几何的保守机械解释，不能直接当作完成性、扭矩、隐藏啮合或材料事实。特别修正三点：`M4_nut_plate_topleft/lowright` 是适配板相应位置的 M4 螺母，而不是额外的螺母板；`gearbox_housing_drive_shaft`、`spin_drive_shaft` 是组合/动作语境，不是新增实体；适配板在参考图中是深色环形转接件，不能统一描述为银色平板。

Model-A 是 Fein CG15-125BL，Model-B 是 Fein WSG7-115A。参考图中 A 为黑色壳体，适配板在转子入壳端附近并配拨杆组；B 为银灰壳体，适配板画在转子另一端，官方图没有单列 A 的拨杆/弹簧/垫圈组或两颗 M4 螺母。B 本地有三个 `remove_locking_lever_assembly` 粗粒度 TAS-S 段，所以只能说图示/词表存在冲突，不能断言 B 样本绝无该机构。论文统计 A=92、B=20；本地 TAS-B/front 文件名计数 A=93、B=19，少 ASR 的文件是 `KE03ER16_Disassembly_A_001_front`，其首帧外观与 A 一致，差额暂不擅自修正。

全量离线核对覆盖 112 份 TAS-B/front、92 份 ASR：19 个 TAS-B 名词、17 个规范 ASR 名称和 4 个旧 ASR 名称全部进入知识映射。ASR `state_changes` 原始行有 11121 行，但相邻 `state_sequence` 的真实组件差分是 3231 个、分布在 1355 个帧时刻；共同变化只能作关系佐证，不能当作直接接触或顺序因果。为工具和部件各选取了带文件、视角、GT segment pointer、时间戳和 SHA256 的 34 张视频帧；图源 `2anglegrinderconfig.svg` 的固定 Git blob SHA1 为 `0a56f418588b92fadb923bf0b5d1bd0877ca4205`。

可复用文件：[`configs/impact_qa/object_knowledge_v2.json`](configs/impact_qa/object_knowledge_v2.json) 是主知识源；[`prompts/impact_qa/v28r_object_knowledge.txt`](prompts/impact_qa/v28r_object_knowledge.txt) 是完整英文块，另有 `_A`、`_B` 两个型号裁剪版；[`reports/impact_qa/impact_object_knowledge.md`](reports/impact_qa/impact_object_knowledge.md) 是中文审阅报告；[`reports/impact_qa/object_knowledge/visual_evidence.json`](reports/impact_qa/object_knowledge/visual_evidence.json)、`audit.json` 和 `source_manifest.json` 保存证据与哈希。推荐把适用的 A/B prompt 放在“clip 型号之后、逐 clip GT 和视频证据之前”，用于命名和功能背景；开放题、完成状态、顺序、时长和异常类别仍必须以当前 clip 的 GT/视频证据为准。本轮未把知识块接入批量生成，也没有测量它对 VLM 的增益。


## 2026-09-26：MCQ 必须使用各视角自己的时间与标签

IMPACT 论文 §3.2 明确写出 “view-specific refinement for occlusion and phase adjustment”；§4.1 将 ATR 定义为 “a multi-label diagnostic on anomalous segments”。这支持两个边界：相邻多标签异常不能强制改单标签；跨视角不能仅复制 front 的标签和帧号。[本地论文原文](papers/IMPACT.txt:448)

本地核验例：SS07EL13_Disassembly_A_002 的 front 右手 frame1608–1779 标 F；top 同一帧段标 D+F；ego 右手 frame1341–1483 标 F，实际 fps=24.917，非30。NA07GE21_Disassembly_A_003 的 front hand_spin_drive_shaft 异常段与 ego 的 adjust_drive_shaft normal 段也不是同一原生动作标签。本实验只匹配同手、相近时间/时长且有共同动作名的区间用于视角对照，GT 始终取所在视角；此方法不是帧级同步，更不能作为跨视角一致性真值。

工程改进：将同手相邻、phase 和六维 anomaly_type 向量完全相同的 TAS-B 段合成“稳定标签区间”，保持每个动作和 ATR 来源。先选≥5s且有非 null 动作的完整区间，一段一题，多标签仍多选。这避免一个7秒ATR段里的0.5秒Spatial标签被错误当作7秒异常。该分段是本项目提案，非官方 ATR 定义；原始标注保留不改写。MCQ 固定答案来自 GT，VLM 的可见动作描述和错误原因另存，不能因看不懂而把标签改成 Correct。

R1 的实际失败提示：同模型两阶段都说高置信度，并不能排除把工具空握写成工具接触、把另一只手的转轴归到目标手。下一轮放大操作区域并保留全图嵌窗、显式描述工具尖端与对象关系、检查动作语义矛盾。只检查有限、明确的矛盾，不用关键词匹配冒充完整语义理解；能否改善必须看实际复测和直接帧图核验。[实现](impact_qa/mcq_native_checks.py)；[试验目录](outputs/impact_qa/mcq_grouped_v2/native_r1/summary.json)。

## 2026-09-27：六类异常判定依据核查

公开论文 §3.2 的直接表述为“Anomalies carry six non-exclusive type labels”；官方ATR资产说明为“All assets are generated from the canonical v1.1 bimanual annotations.”。六类是可共存的标签，ATR由TAS-B生成。本轮检查正式正文、官方固定提交文档/图示/代码/发布清单及issue，未发现逐类操作判据手册或逐段原因文字；不能把本项目概括的类名释义称为官方定义。[论文](https://arxiv.org/html/2604.10409v1)；[ATR说明](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/dataset/ATR/README.md)。

本地审计560份TAS-B（67,492原子段）及7,797条Split1 ATR：TAS-B segment只有动作、动词、名词、帧、phase、六维异常向量及entity，没有原因/正确替代工具/违反规则字段。front的1,944个异常原子段中391个多标签；六类的所有非null异常动作名都有同名normal样本。Temporal常见null/hold，Spatial多place工具或部件，Handling大量hand_spin_drive_shaft；Wrong part也有转轴而非拿错件的实例。分布是关联，不是充分判据。[数据审计](reports/impact_qa/anomaly_taxonomy_audit/annotation_audit.json)。

直接查看六例共72张源帧并核对双手GT上下文，发现明确可解释的局部工具纠正链：KI03AR28_Disassembly_B_005右手57.467–60.533s拿十字改锥/对准/松螺丝标Wrong tool；之后收回、拿一字、对准标recovery，64.733s起松螺丝标normal。可描述这一具体更换过程；其余五例尚不足以给出唯一原因，尤其不能自动写成打滑、装反、漏装或未达到任意时限。该工具例不足5秒，仅用于语义诊断。审查者为Codex，非真人。[实例证据](reports/impact_qa/anomaly_taxonomy_audit/case_dossiers.jsonl)。

另一个重要限制：官方PSR代码中的图声明“Edges are robust prerequisites mined from data.”，由92条ASR数据、min_confidence=0.9等阈值统计挖掘；当前102条边的目标均为recover_ok。这不等于完整专家流程，不能无条件用作所有安装/拆卸动作的异常因果规则。术语“局部解释”在本项目指仅针对当前片段、由动作和可核验参照支持的说明，不升级成通用标注规范。[图配置](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/tasks/PSR/gemini_3_1_pro/configs/procedure_graph.json)。

后续方法提案：分开存GT类别、可见动作、局部原因与未知项，先用明确的异常→纠正→normal链构造原因/纠正QA；空握、共同持有、徒手、重复或时长本身不触发任何固定类映射。参考prompt独立保存、尚未接入或宣称性能增益。[完整报告](reports/impact_qa/anomaly_taxonomy_audit/report.md)；[reference prompt](prompts/impact_qa/anomaly_taxonomy_reference_v1.txt)。

## 2026-09-28：从实例发现判据，需要对照和未见样本

本项目方法提案由两项证据支撑：官方论文只确认“six non-exclusive type labels”，本地所有异常动作名又都有normal同名对照，因此不能仅由动作名称推出充分判据。[论文](https://arxiv.org/html/2604.10409v1)；[本地审计](reports/impact_qa/anomaly_taxonomy_audit/annotation_audit.json)。提案是本项目的工程研究设计，不冒称其他论文已经验证其效果。

全112个front源视频有1809个唯一标签稳定异常区间。Spatial单类有动作区间322个，265个<1.5秒、53个1.5–<5秒、仅4个≥5秒；只观察长段会系统漏掉短暂放置行为。Wrong part仅42个区间，来自16次执行/10参与者，只有9个单类区间，适合整池审计而非随机挑几例推广。该统计范围不同于648父clip内候选统计。研究中保留短标注诊断不等于修改生产门槛。[覆盖统计](reports/impact_qa/anomaly_taxonomy_audit/followup_coverage.json)。

拟采用成组观察：目标异常、同对象/状态normal、相近其他类别、前后与恢复动作。metadata匹配只筛候选，不能声称严格因果对照；不同型号/紧固件/双手角色会混淆结论。先隐藏类别描述可见事实，再核对动作GT和异常类型，按参与者/执行隔离发现与检验例；规则冻结后才评估未知比例、normal误触发、跨类混淆及无依据原因。术语“工作判据”指有限适用、带正常排除条件和反例的项目规则，不等于原始标注规范。判定来源不明或标注疑似冲突时保留未决，不为解释全部样本而扩大定义。[执行设计](reports/impact_qa/anomaly_taxonomy_audit/next_round_design.md)。

## 2026-09-28：多视角补查的实际结果

已完成上轮71例Wrong tool/Spatial/normal候选审查后，继续针对12组操作检查front/top/ego，共36窗口、724唯一源帧；审查者为Codex，非人类专家，且本轮GT可见，不是新的独立检验。方法依据仍是论文的“view-specific refinement for occlusion and phase adjustment”和“Anomalies carry six non-exclusive type labels”，以及以下直接实例；保留视角差异不代表判定哪份GT错误。[原文](papers/IMPACT.txt:446)；[论文](https://arxiv.org/html/2604.10409v1)；[本轮审计报告](outputs/impact_qa/anomaly_multiview_v2/report.md)。

LE07UF17_Disassembly_A_004右手front160.733–162.667s的normal反例，在ego161.175–163.101s看清红黄柄改锥仍握在手里、右手伸入Box 4；工具杆向斜上方，不能编成刀尖送螺丝。与之相对，LE06AS03_Disassembly_A_003的Spatial/place_screw在ego124.253–125.818s清楚显示细长紧固件释放在灰色桌面，改锥在桌上。工具共同持有既不是异常的充分条件，也不是这些Spatial存放事件的必要条件。[normal细节](outputs/impact_qa/anomaly_multiview_v2/details/ac_caf796a863e97b95_ego_p1.jpg)；[Spatial细节](outputs/impact_qa/anomaly_multiview_v2/details/mv_8ddc3ed4e499_ego_p2.jpg)。

本项目新增的控制变量是“组件状态”：LE07UF17_Disassembly_A_001同名store_drive_shaft的Spatial与normal片段，中间发生适配板分离；带大盘的轴与已分离的轴不是同一状态。SS07EL13_Disassembly_B_005的异常存螺丝进入Box 2，后续normal段右手从Box 2移向Box 3，但22张连续源帧仍不能消除指间遮挡；只能称局部纠正候选，不能称同一颗螺丝已经被视觉追踪并纠正。[逐例事实及原生GT指针](outputs/impact_qa/anomaly_multiview_v2/visual_reviews.jsonl)。

术语“局部纠正候选”指前后GT及动作轨迹与纠正解释相容，但对象连续性或规范依据未满足；不是确认的纠正，也不能当官方异常定义。3组局部操作存在跨视角标签差异，其中front/top normal在ego可能为Wrong tool/Procedural或Temporal；不能复制Correct答案。新参考prompt要求分别记录GT、手/工具/对象状态、接触、目的地、释放、最终状态、适用规则及未知项；只在证据足够时生成事实问题，规范性原因另外把关。此为本地审计驱动的工程提案，尚未复测prompt生成质量。[差异记录](outputs/impact_qa/anomaly_multiview_v2/crossview_differences.json)；[prompt v3](prompts/impact_qa/anomaly_evidence_rules_v3.txt)。

## 2026-09-28：六类首轮完成后的工作判据修订

本轮是直接视频证据研究，没有新增外部方法或作者标注规范。既有论文短摘“six non-exclusive type labels”支持类别可并存，不支持用类名推具体原因；“view-specific refinement for occlusion and phase adjustment”要求保留原生视角差异，并不使多数标签成为真值。[已保存原文](papers/IMPACT.txt:445)；[论文](https://arxiv.org/html/2604.10409v1)。以下规则是本项目假设，由逐例源帧和约束支撑，非官方定义。

依次审核Wrong tool/ Wrong part/ Handling/ Procedural/ Temporal，33目标、23执行、13参与者、72窗口、1512唯一源帧；Codex直接看图，GT可见，非人类专家/盲测。工具有3条同目标局部更换链候选；更短的Handling补查比长hold更具诊断性：ER07AD15_Reassembly_A_003 top47.833–48.7秒，小件离手后落台并追取；KE03ER16_Disassembly_A_001 top19.4–20.333秒，拨杆样组件释放时未被接住而落台。连续26/28帧支持控制失误候选，但允许有意落台与否仍须任务约定，不能推损伤/力矩。[第一例连续图](outputs/impact_qa/remaining_rules_v1/followups/h6_top_detail.jpg)；[第二例连续图](outputs/impact_qa/remaining_rules_v1/followups/h7_top_detail.jpg)。

Wrong part的7个定向异常目标未验证“换错部件身份”：wp1始终同一环反复翻转试装；wp7动作名为pick_up_bearing_plate但端盖留Box3、手在Box4。这支持新增“动作对象疑点”状态，不支持全部原标签错误。Procedural pr1已补齐关闭→重新打开→内部紧固→重闭合，但必要前置条件仍需验证。Temporal约88秒和44秒目标仍有双手工作，不能直接写成空等；14.7秒hold_lever异常与17.467秒normal候选也不能提供统一秒数门槛。[逐例证据与GT指针](outputs/impact_qa/remaining_rules_v1/visual_reviews.jsonl)。

术语“局部控制失误候选”指可见脱离/散落与重新拾取轨迹，在保持控制的任务约束下支持Handling；意外性、规范适用性仍需评估。“偏序前置条件”只约束真正有依赖的状态转换，不要求所有动作遵循唯一顺序。物理原理可以约束接口和连接，不能推出盒号和一般时长上限。六类工作规则与反例见[报告](outputs/impact_qa/remaining_rules_v1/report.md)、[机器可读规则](outputs/impact_qa/remaining_rules_v1/rules.json)；[独立prompt v5](prompts/impact_qa/anomaly_first_principles_v5.txt)未接生产、未做生成指标复测。

发现方法风险：h6 ego同名候选匹配到前一次正常取件，视觉否决该同事件关系；不能把它当当前错误的ego漏标。GT/工具匹配只是检索候选。h4 ego仅141.47秒，未覆盖315秒目标，保留缺失并改front/top，不截断造证据。下一步是补具有区分力的实例/任务约束，不能用更多相似hold片段替代规则验证。

## 2026-09-28：front规则的全量关联及任务阶段约束

用户限定front后，对112个视频、13512单手原子段计算43个代理条件。术语“GT一致率”是规则触发中同类标签占比，“GT覆盖率”是该类标记中被条件命中的比例；两者均不是真实视觉准确率。四个较强动作条件（hand_spin、place/store前序loosen、NULL≥8s、重装dismount）分别为96/111、62/96、90/123、16/22，同类覆盖28.9/9.0/9.6/5.1%；合计类别一致率75.0%、六类标记覆盖11.0%。[完整表和分母](outputs/impact_qa/front_rule_coverage_v1/report.md)；[可复算逐规则结果](outputs/impact_qa/front_rule_coverage_v1/metrics.json)。该结果支持候选检索，不能据lift称分类准确率提高35倍。

本项目提出以“具体紧固件＋操作阶段”限制动作代理。依据是官方[手册](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/Manual_Book.svg)的工具接触图与front局部过程：A适配板长螺丝为红黄十字，A轴承板/拨杆为绿黑Torx，轴端螺母为银色扳手；B已核对轴承板拆卸为黑蓝一字，不能复制A连接。手册是图像证据，没有杜撰文字引文；参见[保存的图像总览](reports/impact_qa/manual_book_contact.jpg)。安装“手指预拧→工具紧固”、拆卸“工具松开→手指旋出”是本研究结合接口和视频提出的阶段解释，非另一个数据集作者规则。LE07UF17_Disassembly_A_004 front63.767–70.733秒，绿工具之后手指处理并去料盒，为正常阶段解释提供实际例子。[源帧](outputs/impact_qa/front_rule_coverage_v1/frames/carried_other_1/sheet.jpg)。

“持件未开始”需要判断任务是否已具备启动前提以及双手是否有效推进。重装hold≥8s只有27/436为Temporal；加另一手操作类GT覆盖≤10%后15/49，视觉仍见NULL期间在工作。推断持工具＋徒手104段，Handling9/104、Temporal8/104；工具持有推断本身有遗漏，不能据此证明该语义规则真实误报率。TAS-S阶段＋推断工具不匹配仅4/29与Wrong tool一致，失败源是紧固件泛称、工具跟踪和步骤粒度。31窗口/612front帧的[逐例记录](outputs/impact_qa/front_rule_coverage_v1/visual_reviews.jsonl)保留反例、未知及GT冲突。

任务依赖用局部前置关系，不用唯一全序。官方论文短摘“partial-order prerequisite graph”和“six non-exclusive type labels”分别支持偏序和多标签表述，但不提供本轮具体判错原因。[论文§3](https://arxiv.org/html/2604.10409v1)；[本地正文](papers/IMPACT.txt)。Temporal工作假设扩展到可见延迟启动/低效停滞，明确不要求一定有硬性截止时间；它仍需排除有效工作、检查与双手协作，不能从图像断言心理上在思考。新[参考prompt](prompts/impact_qa/front_task_stage_rules_v1.txt)将GT、事实、要求、替代解释分开，未声称完成生成质量复测。

时长门槛是数据选择问题：96个放置前loosen条件中仅10段≥1.5s，0段≥5s。原子段时长、异常稳定区间时长、clip时长应分开；短错误可由长上下文展示，但不能扩大错误范围。当前真实语义准确率保持未估计，需要后续GT隐藏、独立裁决及概率抽样加权；本轮31例是已知标签的诊断样本。

## 2026-09-28：front MCQ广覆盖候选与协作审核设计

本轮不把规则命中直接转换为最终答案，而是建立候选→视觉证据→人工结论三层。全部1809个front连续GT异常区间保留；另保留168个命中预先冻结代理条件但GT没有异常标签的事件，并在元数据中写明`origin=rule_candidate_without_GT_anomaly`。这样可检验标注漏标候选，但不把它们标成Correct或异常。

视频展示偏差的原因是旧native pilot有20秒完整run限制、旧页面按短时长优先，且旧生产clip是局部异常区间。新组保留目标的真实原片区间，并扩展前后语境到至少45秒；不把上下文帧错误算进目标。目标候选时长分布为<1.5秒781、1.5–5秒701、5–20秒429、20–60秒58、≥60秒8；长上下文量化为组播放时长中位54.63秒、最长163.5秒。模型输入编码视频为4fps，目标区间加密采样并记录原帧ID/PTS；视频播放展示使用源时间的完整上下文。

MCQ固定七项定义来自front_task_stage_rules_v1：Correct、Temporal、Spatial、Handling、Wrong part、Wrong tool、Procedural。异常选项可多选，Correct互斥。Qwen只输出具体事实、progress、每类supported/contradicted/insufficient、短理由和目标证据帧；GT类别、模型视觉结论和人类答案物理分栏。Temporal新增强约束：运动不等于推进，否定Temporal需要可见状态变化或另一手有效支撑；持续调整但没有状态变化不得直接当normal。

协作审核保存question revision、审核昵称、答案、通过/不通过/证据不足、备注和快照；题目领取使用锁和30分钟租约，尽量避免多人重复领取；同题意见冲突显示待复核；旧版本无法覆盖新版本。页面7863优先显示当前题目、GT、视觉依据和证据帧；“通过·下一题”“不通过·下一题”“证据不足·下一题”固定在右侧，另保留完整源视频和同clip全部题目。

实验暂不报告模型准确率：GT分层输入可能带标签偏差，候选模型看到动作/阶段标注，且人类结论未完成。应以通过率、证据充分率、GT—视觉冲突率、按参与者/型号/类别分层的人工一致率作为下一步指标。所有candidate默认`formal_release=false`，不能直接进入训练或正式评测。

front_mcq_expansion_v1已完成：1977题全部有视觉说明，39题至少一类获模型支持、264题出现反证、1674题证据不足。模型支持集中于Temporal，其他类缺目标接口/摆放要求/部件身份等证据，不能通过降低标准来增加已确认异常量。定向源帧复查还发现工具动作遗漏及部件颜色身份误称，已在UI标注；这说明本轮最有价值的交付是可追溯候选池和多人核验流程，而非未经人审的高准确率数据。[完整报告](outputs/impact_qa/front_mcq_expansion_v1/report.md)；[逐题结果](outputs/impact_qa/front_mcq_expansion_v1/questions.jsonl)；[来源/区间审计](outputs/impact_qa/front_mcq_expansion_v1/audit.json)。

审核队列修正：审核记录追加与前端选题是两个独立环节；正确保存不代表界面自动排除已审。2026-09-28用户实测发现initial固定取第一题、clip列表/子题列表未按人审状态过滤。统一以当前question revision的所有审核员最新意见决定全局已审；未审默认队列过滤贯穿所有入口，已审/分歧另设显式入口。同一clip多个目标共享视频，需用题目ID和目标时段判定是否重复，不按视频是否相同计审核进度。原始3次提交保留，按题目去重为2道已审；不得删除重复提交历史来掩盖UI问题。

题型口径核验：最新1,977题全部是异常类型MCQ。独立旧开放式题库2,309题/648clip，其中完成性923、整体操作648、时长417、详细过程250、顺序71；candidate2282、held27。MCQ的facts/reason/alternative是解释字段，不是额外开放题。页面标签明确数量与题库来源，避免混淆。

2026-09-28 审核播放区间提示：使用题目结构化scope.playback_interval_s和目标手生成标记，以播放器currentTime同步判断段高亮；颜色表示当前播放位置进入判断区间，不代表人工确认异常。目标外保留上下文，可从起点或提前3秒播放，帮助比较动作起止及前置状态。区间直接关联题目ID和播放组ID，避免依赖问句文本或将源视频时间当成clip播放时间。该项为审核工具改进，不改变标签、生成数量或异常规则。

2026-09-29 用户人审反馈进一步确认“标记存在”与“异常原因可解释”需要分开。论文§3.2的“six non-exclusive type labels”不提供手悬空、选件、徒手转动的具体判错门槛；§3.1的“partial-order prerequisite graph”也不支持用唯一示范顺序判错。[论文](https://arxiv.org/html/2604.10409v1)。发布README说明ATR/PPR由canonical TAS-B派生，因此二者一致不是独立证据。今日直接HTTP复核论文和官方仓库README均200；web工具404，不将失败解释为资料不存在。建议先用60–100个含正反例和争议的样例校准要求，再独立新样本检验；隐藏GT、取消预选、区分规范缺失与视觉不足。此为本项目建议，尚未实施界面改造。[具体协议及来源](reports/impact_qa/review_criteria_reset_20260929.md)。

按用户明确要求，当前8次提交/7题已备份后从活动人审队列清空；不再把之前的通过记录计为有效裁决。原标注和1,977候选保留。对fx_d68d994f397213b8仅补看两张front源帧，接触区域被遮挡，不能确认旋拧效果或工具要求；未把不确定重标为Correct。开放QA可保留经核实的事实，但不能借原异常标签补造原因。

2026-09-29 按用户要求将已有领域参考接入7863。[中文速查](reports/impact_qa/review_reference_20260929.md)和configs/impact_qa/review_reference_v1.json复用原工具知识与六类判据。A官方手册图支持适配板长螺丝用红黄十字、轴承板/拨杆用绿黑Torx、内部螺母用银色扳手；B仅有局部轴承板拆卸的一字工具证据，完整B安装紧固细节未核验，明确不套A的17组件图。手册来源及图像证据见[原知识报告](reports/impact_qa/impact_object_knowledge.md)。论文短摘“partial-order prerequisite graph”支持允许合法换序，[原文](https://arxiv.org/html/2604.10409v1)。

审核辅助采用“当前动作对象优先、粗步骤辅助”的工具参照：实际案例TAS-B为装适配板、TAS-S为安装轴承板，不能仅凭粗步骤显示一字工具为当前要求。UI显示两类标注与差异提醒，仍不直接判定谁错。双手动作/TAS-S/ASR按源时间转换为clip时间并随播放更新；状态可错及无ASR明确展示。1,532题有ASR、445题无ASR（B432/A13）。六类定义、型号拆装流程、工具外观和部件作用折叠展示，证据不足仍不映射Correct。本轮没有新增模型判定或修改QA答案。

2026-09-29 用户要求快速交付7864纯3D拆装动画。复用已核对的[A官方手册](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/Manual_Book.svg)及[A/B结构图](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/2anglegrinderconfig.svg)，以程序化几何展示组件连接与工具映射，不新增关于内部精确结构的事实推断。A提供14步装拆；B仅结构参照。准确映射工具不等于准确模拟整个装配：尺寸、路径、螺纹、齿轮啮合和拨杆小件叠放未核验，不能声称完全正确，也不把动画顺序用作唯一正确顺序或新异常标注依据。页面与README持续显示上述范围。

2026-09-29 B动画扩展：再次查看[官方项目页](https://kratos-wen.github.io/IMPACT/)引用的2anglegrinderconfig.svg，放大B区域确认：除轴承板螺丝对外，还有图11上方的壳体螺丝对，以紫/蓝连接箭头指向轴组件支承法兰；旧静态模型遗漏该组，现补齐。官方文字“Valid trajectories follow a prerequisite graph rather than a single rigid sequence.”支持示意顺序不能作为唯一全序。项目页curl返回200，web入口404、GitHub raw超时，未将获取失败解释为资料不存在。

B新增独立11组件组/12步骤，图3适配板仍位于转子远端；支承法兰按图6轴组件整体建模，不将其与远端适配板混同。AL07EJ17_Disassembly_B_005的top149秒见红黄十字在已开盖壳体内操作，front TAS-B /segments/68–69分别提供拾十字与松螺丝上下文；208秒接触遮挡，不用来确认保持螺母的完整操作。一字轴承板示意沿用已有26.97秒视觉证据，不从样例频率推断唯一适用工具。具体顺序/轨迹仍是本项目示意推定，证据与限制保存于outputs/impact_qa/assembly_3d/b_reference/source_manifest.json。

2026-09-29 筛选完整安装参考：全55份front Reassembly（A45/B10）均有异常标注，无零异常原片。选择ER07AD15_Reassembly_A_004_front（132.233s，双手异常并集6.333s、5原子标注/4派生ATR段）与NA07GE21_Reassembly_B_005_front（153.367s、3.467s、2原子标注/2ATR段），两者各自是该型号最短完整安装录像。A更低异常总长的替代片为473.7s/5.6s及205.77s/5.733s；本次优先兼顾短时长。所有<1.5s标记均保留，按帧闭区间转半开区间并对双手求时间并集，不累加重叠时间。

ATR交叉核查发现分组后的多标签会把某类扩大到整个合并段，故核对每手所有异常时间并集，而不把派生ATR的类别范围等同于TAS-B精确类别起止；55trial的整体异常并集一致。A原ASR最终17组件全1，B无ASR；TAS-S分别覆盖五/四主要安装阶段及结束。人工检查两张阶段联系表，共43帧，只支持开头散件、过程安装与末尾整机/手柄的可见完整性，不宣称连续逐帧审核或机械合格。排名、证据、SHA与全部短标注区间见outputs/impact_qa/assembly_3d/complete_videos/selection.json及all_front_assembly_rankings.jsonl。

2026-09-29 双语流程文本保存于reports/impact_qa/assembly_disassembly_AB_bilingual.md；A依已有手册，B依据连接关系与局部样例，逐步保留证据边界。B壳体螺丝对与A适配板螺丝/M4螺母对分开，B扳手关系明确为接口推定、一字仅为样例；不编造卡扣结构、小件叠放、螺纹方向或扭矩。来源与官方“Valid trajectories follow a prerequisite graph rather than a single rigid sequence.”短摘均附于文末。

2026-09-29 新MCQ核验按用户指定8–16张目标图、前后最多各2图进行SOP盲审。PSR实查51状态操作与17组件、expected标志全false，未提供显式依赖边；组件连接前置由已核验手册/图及局部证据补充并注明未知，不能称为官方完整偏序。与此前4fps视频核验版本区分，本版是多图输入且长段密度下降，133.5s目标只有16张、间隔约8.9s，连续状态推进/重复尝试证据可能不足。协议、占位符、来源范围见prompts/impact_qa/mcq_sop_visual_v1_README.md；不因抽帧未见异常而自动纠正GT。
