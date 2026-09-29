# 调研与标注核验日志

## 2026-09-28 Spatial规则专项与GT可错策略

环境预检：.venv-impact，torch2.10.0+cu129、CUDA runtime12.9、CUDA可用/7可见GPU、PyAV18.1.0、Pillow12.3.0。硬件沿用上一轮记录RTX4090/49140MiB；本轮CPU解码与JSON审计，没有新增GPU推理/显存分配，没有测试CUDA<=12.1。API请求0，temperature等模型参数不适用。

脚本inspect_spatial_rules.py选择8组16目标×top/ego32窗口；按4s前文+目标+6s后文，4/10/4帧抽样，3解码线程任务，各流2线程，源图JPEG96；按PyAV真实rate/PTS定位，front/top30fps、ego24.917fps。followups另冻结5目标×2视角及2语境补查，共21目标/44窗口/792帧条目/773唯一源帧。所有44序列图及6完整源帧细节直接查看；非逐视频全帧、非人类专家审核、非独立留出。

原front目标构成10异常/10normal/1recovery，12执行/6参与者。2局部Spatial解释成立（手柄错盒归位、拨杆错误目的地尝试），都来自KI05KO01_Disassembly_A_001，不计为两独立参与者验证。手柄ego normal疑似漏标；LE适配板原盒拿回被三视角标Spatial，独立判断缺乏违规证据，记录疑似误标/未知条件而非自动Correct。固定初始工具区、立即把所有部件入盒等捷径未采用。六类第一性原理工作定义仅框架，除当前局部案例外未新增类别认证；正式新QA0。

失败归因：初筛只看六位类型全零，会把p6后续recovery当normal；预检phase断言捕获，改为单独recovery角色后冻结，未把错误样本混入normal统计。同名动作±3.5s匹配在p7选中较早Temporal段；视觉检查拒绝此对应，另存手工补查语境，未覆写原映射或把它统计成真实跨视角类别冲突。一次笔记帧号引用验证发现不存在的索引，在写入前终止；最终按实际manifest引用已审帧和作用域。web访问论文404，沿用本地固定来源，未以失败当文献不存在。

验证：四份新增Python语法通过；复用native_trial/map_interval/source_frames，抽出evidence_audit.verify_native_action。36份GT/423来源段SHA、pointer、内容核验；44窗口的帧范围、作用域、媒体、GT手别和JSONL记录检查通过。最大PTS/标注时钟差5.684e-14秒，不代表跨视角逐帧同步。原始GT和生产QA未修改。输出spatial_rules_v1/report.md、rules.json、visual_reviews.jsonl、audit.json、code_manifest.json；参考prompt anomaly_first_principles_v4.txt尚未接入生产，未宣称QA质量已提升。

缓存复跑完成：两个渲染器成功，836张已缓存图像（含序列图）mtime未变，未重新解码写入；cache_check.json留存。

## 2026-09-28 Wrong tool / Spatial对照研究完成

输出目录outputs/impact_qa/anomaly_contrast_v1。预检torch.cuda.is_available为True、7张可见卡，PyAV/Pillow和本地视频/标注可读；runner也在调用前断言CUDA。GPU4/5复用vLLM8002、TP2，RTX4090每卡报告49140MiB，驱动610.43.02；结束快照显存41715/43211MiB，不代表峰值。torch2.10.0+cu129、CUDA12.9；未验证CUDA≤12.1。模型服务名impact-qwen38-27b，目录Qwen3.8_27B，架构Qwen3.5。max_model_len32768，服务max_num_seqs8，本轮并发4，temperature0/top_p1/seed20260928，关闭thinking，JSON schema输出。

选择冻结71案例：发现24异常+20normal，检验17异常+10normal，检验参与者KJ03JM25/LE07UF17。Wrong tool异常17、Spatial24；多标签4、短于1.5秒17均保留作研究，非生产。直接图像审查1420帧条目/1401唯一源帧，审查者Codex、可见GT，真人状态unreviewed。normal按动作名匹配不等于同状态：8对紧邻、3对间隔<5秒、11异常无normal候选。未构建独立同状态二分类金标，不报告准确率/误报率。

迭代：最初2个smoke响应因目标或上下文引用越界被拦截，保留原结果；修复为before/target/after各自schema枚举。observe_r1共44成功请求，上下文前4后6秒、4fps/短目标8fps、宽960+全景侧栏、像素预算8388608，实际26–124帧，prompt7840–18841token，输出571–863token。结构校验通过仍存在工具/左右手/动作归属错误，原图和实际编码视频抽查未发现片段取错，不能将问题简单归为模型不会识图。

focus_r1采用目标区间单独视频、crop[.10,.35,.90,1.0]、像素预算16777216、约24帧预算/动态1–8fps、最多3条事实。8个定向困难例成功，实际6–22帧、prompt2499–7538token、输出301–416；4个主要错误修正，2个仍有明显错误，另2个大体动作原本一致。多项改动同时发生且样本非随机，不作消融或总体准确率结论。规则冻结后27个保留例全部API成功，6–24帧、prompt2499–8240、输出313–418，仍有小对象、释放和左右手的错误。

有效实验请求79、总token787563；另2个失败smoke的token不计入该合计。媒体用file://video_url，服务do_sample_frames=false，保存源帧/时间和SHA。独立规则冻结后才提取检验帧，最终审核其hash未变。重跑27例检验新增API请求0，断点缓存有效。5份新Python源码全部py_compile通过；audit_anomaly_contrast.py核验71例来源pointer/SHA/边界、隔离分组、媒体哈希、引用、无GT的payload字段，结果通过。所有中间结果和失败缓存保留。

发现3例、检验1例支持局部工具更换关系；检验Wrong tool5例中另有2例部分证据/边界疑点、2例原因未知。12个检验Spatial均无已认证的规范性原因。明确normal反例：LE07UF17_Disassembly_A_004右手160.733–162.667秒持改锥伸入料盒，GT normal/place_screw，因此废止无条件“持工具存放部件就是错误”解释。形成rulebook_frozen_v1.json与独立证据prompt，未接入生产；正式新增QA0、确认通用类别规则0。Handling、Temporal/Procedural与Wrong part的扩展审查待下一轮，既有QA未改。

## 2026-09-17
- 阶段：文献调研与只读数据检查；不训练、不执行模型推理。
- 初步硬件：nvidia-smi 报告 7 张 NVIDIA GeForce RTX 4090，每张 49140 MiB，驱动 610.43.02；此处如实记录设备返回值，不推断标准商用配置。
- 工具故障：web 检索服务两次返回 HTTP 404；直接 HTTPS 访问 arxiv.org 成功，改用官方网页与公开 API。
- 现有资产：当前目录 cc4d_annotations/ 约 8.2 MiB；历史目录还含同名仓库、QIC parquet、历史预测与诊断脚本。未将历史计算结论视为已验证证据。
- 模型超参数、训练指标、GPU 显存占用：本阶段不适用，后续不填写虚构实验结果。

## 环境预检结果

- `python scripts/preflight.py` 成功，原始结果在 reports/preflight.json。
- Python 3.14.7，Linux 6.8.0-40-generic，预检可用存储约 3.25 TB。
- 7 张设备均由 nvidia-smi 报为 RTX 4090 / 49140 MiB，驱动 610.43.02；预检每张 memory.used=15 MiB。本任务没有申请 CUDA 显存。
- 当前解释器没有 torch；本轮仅用标准库、curl、git、pdftotext 进行 CPU 文献/数据检查，不依赖 torch，因此不安装或修改原训练环境。torch CUDA build / CUDA toolkit 兼容性未验证，不声称已满足未来训练需要。

## 下载与版本固定

- CC4D：本地、历史副本、官方 HEAD 均为 a8a920a3293c4db27099a20ddbe3a3a9be1283e3；非 Git 文件逐一 SHA-256 一致，复用不覆盖。
- EgoErrorVQA：commit 5403cdd05e007b01c88448587c1a1803a27266e2；9 JSON，2,558,258 bytes，Git blob SHA-1/长度/JSON 格式通过。
- IMPACT：GitHub commit 4fed5faa5f05f7aece55712e458defa1f372b248；数据 v1.1 annotations.zip 8,485,262 bytes，SHA-256 ded862b7599fa2bedbfa7699bf554add955a18d5c9ff641ef7826751fe791cfb；ZIP CRC 通过。解压 7,216 文件，458,673,739 bytes，其中 1,777 JSON 可解析。
- 补充上游标注：EgoOops commit ec0746d4dd71efad43437235a6e04ebf6f1ccf8e；Assembly101 mistake commit 6f3a953267ffb86cdeabf6751af05a75a011a4f8；EPIC-Tent commit 1e784a97ca0a1669988a8ba05d0a73ad812a204a。
- 三篇 PDF 均通过 pdftotext：EgoErrorVQA 20 页、CC4D 正式版 54 页、IMPACT 9 页。EgoErrorVQA 有字体类型警告，但文本提取成功；关键表值与 HTML 对照。
- 未下载任何视频、深度、音频、图像帧、特征或模型；没有运行带自动媒体下载的原作者入口。

## 数据核验结果

- CC4D：384 录制、24 活动、8 人、10 环境、5,700 步骤；1,964 错误步骤；287 负时间行；2 个 recipe split 文件空。非空分区无 recording 交叉。
- EgoErrorVQA：1,805 开放题片段/3,560 QA；1,857 MCQ；31 个程序文本；来源内独立视频 ID 合计 510；所有 task_id 均能找到程序文本，CC4D 子集 ID 均能回连本地 CC4D。
- IMPACT：TAS-S/TAS-B 各 560 JSON、112 trials；片段区间全部通过范围校验。ASR 92 front records，64/10/18 分区无重合。
- IMPACT 发布 TAS-S S1 train/test 共有 42 个 trial，S2 共有 9 个；文档宣称 trial 隔离但文件不符。保留逐 trial 交集，不静默重划分。
- 上游：EgoOops 50 视频/538 片段/95 错误；Assembly101 328 CSV/3,964 行；EPIC-Tent 1,261 动作/626 错误/29 份帧级标签。
- 前 10 条样本保存在 reports/*first10.json；主要检查 stdout 保存在 reports/*validation.log。

## 失败归因与处理

- web 工具 HTTP 404：服务不可用，采用原始站点/API，不编造检索结果。
- bs4 缺失：改用 Python 标准库 HTMLParser，未改动依赖环境。
- raw/arxiv/Hugging Face 部分请求超时：使用固定 Git blob、export.arxiv.org、NeurIPS 正式 PDF 和 HF 镜像。中断下载没有作为有效文件交付。
- Assembly101 初次按带表头 CSV 解析不正确：发现 label 列为空后改用无表头 parser；完整计数重算为 3,964，作废初次统计。
- 原始数据问题包括负时间、多标签、空划分、跨视角 trial 交叉，详见 reports/data_audit.md。它们不属于模型失败，未运行模型去估算影响。

## 论文实验参数与指标（非本机复现）

- EgoErrorVQA：7B/8B 模型评测使用论文所述 24GB 显存，8/16/24/32 帧；Ego-ADR 8 帧；论文 max_new_tokens=256，do_sample=False；Qwen2.5-VL+ADR F1=19.8（Table 4），自定义 TP/FP 口径。
- CC4D：论文单 A40，50 epochs，Adam，MLP batch=512/lr=1e-3；步骤 Transformer batch=1/lr=1e-5，多模态 lr=5e-5；BCE 正类权重 1.5。TimeChat 多提示 ZeroShotER F1=46.1。
- IMPACT：论文 4×A100 40GB，16-frame feature clips/stride=1；MS-TCN++ ASR Final-Acc=0.93、Trans-F1=0.33；PSR F1=0.26、Delay=8.46s。不能将这些论文结果视为已复现。

## 完成与验证

- 生成脚本全部通过 python -m py_compile；未执行第三方模型代码。
- 核查 scripts/validate_annotations.py、validate_impact.py、validate_upstream.py 的完整输出，已将差异写入报告。
- 交付：research.md、plan.md、experiment_log.md、reports/data_inventory.md、reports/data_audit.md、标注与论文、可复跑核验脚本。
# 2026-09-18：细节理解设计与容量探测

- 任务：给出 Qwen3-VL-8B-Instruct、单卡 48GB 的细节理解方案；没有真实视频评测或训练，没有下载新模型/视频。
- 预检：`/home/ldq/miniconda3/envs/sop/bin/python`，torch 2.9.1+cu128，Transformers 4.57.6，CUDA 可用，FlashAttention 可用；7 张 GPU 中仅使用 GPU 0。驱动/总内存记录见 `reports/design/environment.json`，单卡 CUDA 可见 50,894,602,240 bytes。此工作不要求 CUDA ≤12.1；本次实际环境为 12.8 版 torch 构建，未修改环境。
- 模型：已有 `/data_1/ldq/models/Qwen3-VL-8B-Instruct`；BF16 权重索引总量 17,534,247,392 bytes。在线官方路径经 hf-mirror 获得的模型/视频处理器配置与本地一致。来源快照哈希见 `reports/design/source_manifest.json`。
- 数据检查：`scripts/analyze_ego_duration.py` 输出有效时长分位数、字段非空覆盖和前 10 个时间区间；结果 `reports/design/ego_duration_stats.json`。无效/漏步区间没有混入时长分布，EPIC-Tent 派生时间值不视为已修复。
- 容量脚本：`scripts/profile_qwen3vl_video.py`，batch=1，BF16，FlashAttention2，384×672，固定合成随机帧，关闭自动缩放/重采样，生成最多 32 token；逐配置保存 JSONL，可断点跳过成功配置。这里的秒数不含视频解码/预处理，不代表真实任务服务延迟。
- 性能异常：原始视觉 patch Conv3d 路径 32 帧耗时 130.53s，峰值 allocated 17.51 GiB；不是 OOM。历史环境记录提示相同 kernel/stride 的 Conv3d 慢路径。另测将每 patch 覆盖全输入的卷积改写为同权重 Linear，16 个合成 patch 的 BF16 最大绝对差 0.00390625，通过 rtol/atol 0.02 检查；它在代数上等价但不保证 BF16 逐 bit 相同，也未声称语义结果完全不变。
- 原始慢路径的后续 64 帧探测被主动终止，SIGINT 未立即生效，随后用 SIGTERM 终止该自建进程；不是程序崩溃或 OOM。第一轮优化测试短暂与其并行，`qwen3vl_profile_linear.jsonl` 保留作探索记录，**不引用其中延迟作为独占性能结果**。确认停止后另起单进程测试 `qwen3vl_profile_isolated.jsonl`，作为最终容量表来源。
- 网络问题：web 搜索接口仍返回 HTTP 404；转用官方 GitHub/arXiv 和官方模型路径。Hugging Face 直连超时，配置经 hf-mirror 获取并与本地核对。没有从失败下载推断模型参数。
- 科学结论范围：只能确认特定合成张量形状、软件与输出预算的运行能力；没有得到 EgoErrorVQA 准确率，没有穷举 OOM 临界点，不宣称绝对最大帧数。建议方案及后续独立评测/消融见 `reports/design/sop_detail_design.md`。
- 最终结果：独占测试 32/64/128/256/512/768 帧全部成功；峰值 allocated 17.51/18.67/20.99/25.63/34.93/44.24 GiB，768 帧 reserved 46.54 GiB。完整表见 `reports/design/capacity_results.md`。所有本次生成脚本通过 py_compile，新增 Markdown 本地链接已校验；测试进程全部结束。
# 2026-09-18：IMPACT 异常理解 QA 试制

- 用户已确认执行计划：第一视角视频+标注，小规模英文 QA 试制，原生多标签类别判断，自动开发提示后人工集中审核。使用已有 Qwen3.5-27B，经 vLLM 本地 API 调用。未经审核候选不标记为真值。
- 发现用户已有全量原始数据下载任务，PID 282240，从 ego 开始顺序下载；未停止或重配。复用已完成 ego 包 15,323,188,764 bytes；SHA-256 与官方 `1ebdda9411a87769fc453138d0d0e2148bdec4d1df68d831431feafdddc24381` 一致，ZIP CRC 通过，解压 112 个视频。项目 datasets/impact 为现有数据根的符号链接，不复制媒体。
- 媒体预检：112 个视频 nb_frames、排序后视频 packet PTS 数、TAS-B 帧数全部一致；每视频首尾分别实际解码一帧成功。没有把这称为全部帧的逐帧损坏扫描。原标注端点为闭区间；转时间时 end 使用下一帧 PTS，证据抽帧记录准确 seek 的目标时间（精度为一帧）。
- 样本：随机种子 20260918；20 开发（10 anomaly/5 normal/5 recovery）、60 试制（30/15/15），共 80 不同执行视频，六类异常均覆盖。试制仅选非 null、完整标签且时长 0.5–35s 的原子动作，不声称覆盖全部长动作。首次按 anomaly→normal→recovery 抽样耗尽稀缺恢复视频；改为优先分配 recovery，配额已满足。此为抽样实现问题，非数据缺失。
- 80 事件 PPR 与 TAS-B 一致；ATR 一处较长合并段的向量与其内部原子动作不同，source_segment_count=4，不能错误传播合并后的全部标签。40 个 anomaly 事件对应的 TAS-S 粗段 has_anomaly=False，保留来源差异，不覆盖原子标签。
- 已生成 80 个审阅片段和 1,392 个初始关键帧；粗采样最多 24 帧、宽 672，上下文各 3s；确有视觉细节缺口时最多补看 24 帧、宽 1024。抽帧和视频压缩并不构成人工审核。
- 环境：已有 sop 环境 vLLM 0.16.0 不包含 Qwen3.5 架构；创建独立 .venv-impact，安装官方 registry 包含该模型的 vLLM 0.18.0（Torch 2.10.0）。原始 PyPI 下载 uv 很慢，改用阿里镜像并终止仅本任务创建的旧 pip 下载；不修改 sop 环境。安装/启动日志在 reports/impact_qa。
- 环境补充：网络依赖下载缓慢，发现 `/data_1/ldq/system_cache/uv` 有完整旧缓存。旧缓存索引指向迁移前路径，不能直接离线解析；将完整 wheel 树在任务目录重打包，由 uv 依赖解析离线安装成功，pip check 179 包通过。实际版本 vLLM 0.18.0 / torch 2.10.0+cu129 / Transformers 4.57.6，锁文件已保存。模型启动遇 SQLite 所需 CXXABI_1.3.15 与系统 libstdc++ 不匹配，仅服务进程设置 LD_PRELOAD 为原 Conda 对应库后解决。


## QA 开发迭代与服务调优

实际设备仍为 7 张 49140 MiB GPU。单实例双卡 BF16，上下文 32768，max_num_seqs=4，显存利用上限 0.85；CUDA graph 仅 decode，capture sizes=[1,2,4]。GPU 0/1 实测各约 41155 MiB。服务日志记录 4 请求并发时部分 10 秒窗口生成总吞吐 51–81 tokens/s；这不是全批均值或理论上限。

独立环境运行 torch 2.10.0+cu129、vLLM 0.18.0。未验证 CUDA <=12.1 的兼容性，不能把该环境报告为 CUDA 12.1 实验。原环境不覆盖安装。SQLite C++ ABI 故障通过仅服务进程 LD_PRELOAD 指向现有 Conda libstdc++ 修复；权重缓存加载约 7 秒，GDN warmup 约 137 秒，graph 捕获约 4 秒。启动慢主要是算子 warmup，不是下载或死锁。

v1：20/20 事件、40 对候选，无 API 最终失败；模型原始 pass=23，加入结构/可见性门槛后 14，6 事件有引用缺失。v2 移除观察动作提示，拒绝元数据问答。开发图像抽查进一步发现模型将段外工具使用解释为段内行为，故 v3 改为目标密集采样、逐帧时间范围标记及时间证据门槛。三轮不是仅提示文字的严格消融；输出质量须经人工评审，模型自审统计不作准确率。

新增 8001/8002 服务多模态冒烟初次使用无字数限制的图像描述、max_tokens=96，导致 JSON 字符串截断；属于测试请求输出预算不足，不是模型加载失败。改为单布尔字段、max_tokens=256 后两端均通过，预热后各约 1.15 秒，详见 service_pool_smoke.json。QA 请求预算仍为 2048，独立检查 finish_reason，失败最多重试 3 次。

追加目视开发：20 个 v3 事件均由研究代理直接检查目标帧并记录；不等于真人审阅。v4 6 事件暴露证据映射接口遗漏，修复为 v5 确定性事实链引用并记录 withheld_facts/source_graph_issues，原始失败产物不覆盖。

# 2026-09-18：IMPACT 视频格式与真实时长核验

本段含此前测量记录，最新 front 实测与 v10 运行记录见文末。旧 ego 汇总使用下中位位置而非偶数样本两中位值均值，200.747秒/5002帧应称下中位顺序统计量；通常定义的中位数为201.308秒/5016帧，不能把二者混报。

新增开放题全库研究：CPU 标准库读取四份官方 JSON，3560 QA/1805片段/1747唯一问句，Assembly101为859 QA/446片段/352唯一问句。scripts/analyze_ego_question_types.py 保存全量题和可重现非互斥文本规则、来源分布、来源阶段/答案极性及实例；不是官方题型标签或人工语义正确率。判断式起首2163，What1325，Why66，How1，其他5。Assembly101完成/漏步/多余命中68/70/81，分别全部Yes/No/No；不照抄此答案偏差。

scripts/audit_impact_state_support.py 核对92 ASR序列（装/拆各46）、1457状态记录、3231组件变化和候选图无环性（53节点102边）。状态-1→1共739，不报告为739次PPR恢复；AL07EJ17_Reassembly_A_002_front状态653→982变化时的双手动作均normal，说明任务粒度有别。front时间只按front标注30fps换算，未做ego同步转移。官方图为92视频挖掘，非完整人工正常SOP。两个脚本py_compile与输出计数检查通过，未新增GPU实验。web工具404，采用先前验证的官方来源快照。v10四阶段提示设计和输入契约完成，尚未运行，不报告性能提升。

补充 QA 批次状态：v7 的 60 个试制事件已全部成功，生成 64 对开放题，原始自审 pass/revise/reject=43/9/12；严格机器通过 37。加开发 20 对，合计 84 对开放候选、80 条类别题，严格通过 47。导出审阅 HTML/CSV/JSONL 并通过 release validator，无文件级错误；语义质量未获真人验收。开发代理看帧检查 8 保留、10 修改、2 拒绝。用户随后将近期目标明确为 EgoErrorVQA 风格的简短 QA，开展独立 v8/v9 开发对照。

v8 对照使用原始标注和 20 条既有代理目视描述，文本生成后以视频自审；20/20 事件完成、35 对 QA。自审输出遗漏第二题导致 7 个事件 review_indices_mismatch，不能将其忽略为全部通过；原始结果完整保留。文本质量问题包括标注措辞、把 wrong_part 编造成错误目的地。v9 改为逐题独立审核、补入目视问句以解释描述中的代词，并禁止无依据的规范位置推断。保持 v7 冻结文件及 60 个试制记录不变。实际 .venv-impact torch 2.10.0+cu129，CUDA 可用、7 卡，三个 API 健康；客户端复用既有双卡服务各并发 4。

v9 完成 20/20，20 对 QA，结构问题 0，自动审核 3 pass/3 revise/14 reject。逐条阅读发现审核器将来源支持的错误/恢复判断误当作必须从片段独立证明的物理事实，且仍放过无依据的规范位置推断；因此这组自审结果不能用于判断参考 QA 正确率。报告另列三个按源标注和已有代理看帧记录可保留的例子，不改写原始审核。所有产物仍 pending_human_review。脚本语法、候选 ID 唯一性及审核状态检查通过；恢复运行复用缓存而未重新生成。

- 使用 `/home/ldq/sop_work/mp4_probe.py` 对本地 112 个 ego MP4 逐文件读取 `moov/mvhd/tkhd/stsd/stsz/stts`；没有依赖 ffprobe，也没有重新编码媒体。
- 结果：全部为 1920×1080、`mp4v`、24.917 fps；无非零码率音频轨。总大小 15,323,163,887 bytes，总时长 27,725.985 s，总帧数 690,847；逐文件 sample_count / duration 与 fps 交叉误差小于 0.01，全部通过。
- 整段录制时长范围 105.471–1,027.010 s，中位数 200.747 s；帧数范围 2,628–25,590，中位数 5,002。外部视角媒体未下载，因此只记录标注中的 30 fps，未推断其容器编码或实际帧数。
- `TAS-B/ego` 共 13,148 段，非空动作 9,791 段；非空动作时长中位数 1.726 s，normal/anomaly/recovery 分别为 1.726/1.605/1.164 s。`TAS-S/ego` 4,423 个粗步骤，中位数 2.247 s。
- 报告与复跑脚本：`reports/design/impact_media_stats.json`、`scripts/profile_impact_media.py`。脚本通过 `python -m py_compile`，JSON 生成成功。

## 2026-09-18：v10 安装状态与顺序 QA 实际执行

- 下载与媒体：front ZIP完整31,487,236,951 bytes，SHA-256=`ab83fbfeaab5509886125ec058843806c77a2629e8015393e82235bbce4bcabb`，与官方一致。只按需解压AL07EJ17_Reassembly_A_002/003/004三个成员，解压校验CRC；没有声称重新扫描整个ZIP全部CRC。原片均H.264/1280×720/30fps，5214/5126/5623帧，全部15963解码帧PTS与ASR帧号/30一致。
- 前检：torch2.10.0+cu129，CUDA可用，7张49140MiB GPU；0–5用于三组TP2 Qwen3.5-27B，GPU6空闲。API8000/8001/8002均健康；单卡预检已用显存约41457–41853MiB。实际环境不是CUDA<=12.1，没有报告该兼容性。配置BF16、32768上下文、每服务并发4、总并发12、温度0.1/top_p0.8/seed20260918、thinking关闭。详见v10_preflight.json。
- 证据：同一参与者三个执行视频，12开发窗口，37.267–106.367秒，中位数74.400秒。原生视频16帧＋6精确锚点；v10.1起另加2个同帧裁剪，裁剪不增加原始空间细节。生成2200tokens、逐题审核1500tokens。官方Manual_Book.svg提供完整图示参考；其顺序不是唯一工程强制顺序，手柄→壳体映射为代理图像解释，待真人确认。
- v10冒烟：4/4事件、8QA，自动keep7/needs1；4题把completion错写install_relation，结构门槛拦截。一条将bearing_screw_topleft=-1写为unassembled，自审也重复此错误；根因是模型读长状态表后扩写了未要求的细节，不能只靠同模型复核。
- v10.1：加入代码计算的answer_contract、逐组件逐帧state_assertions核对、自然短答案和局部裁剪。10/12成功、20QA，keep14/needs6，已生成QA结构问题0。两个失败是规划器把illustrated规则ID放进support_ids，程序报planner:unknown_evidence_or_rule；不是API/OOM。原始失败记录保留。
- v10.2：将当前开发题型的证据资格选择改为代码计算，生成器保留完整流程与事实输入。12/12成功、24QA（completion9/install_relation3/reference_order12），状态/时间/来源结构检查0问题，keep18/needs6。36API调用（12生成＋24审核），没有再调用LLM规划。审核最大输入23668tokens；生成/审核请求延迟中位数31.53/27.85秒，含服务并发等待，不解释为独占速度或批次总耗时。
- 研究代理逐题读24QA、看12锚点图和官方3面板，另看1个手柄末态裁剪，未完整播放所有视频。15保留候选、3收窄单组件/整套组件范围、6轴承板末态需更清楚视觉证据。3修订独立导出、未伪装成模型原始输出或真人标注。全部pending_human_review，没有报告准确率/Recall@1。
- MCQ：同窗口另导出12条原生ASR三选一（正确安装/错误安装/未安装），源答案9个state1、3个state-1，未含state0正例。选项A/B/C位置各4。该扩展不等于EgoErrorVQA错误类别体系，也不是PPR异常判断。
- 验证：片段帧数、源JSON指针、逐帧状态声明、候选ID、评测字段隔离、文件名结果词泄漏检查通过；评测ID和媒体别名改用哈希，去除done/incomplete暗示。v7所有冻结哈希不变，8个新增/修改Python组件语法通过。缓存恢复再次运行成功，908个API缓存文件及mtime均未变，未新增模型请求。
- 产物：`outputs/impact_qa/state_v10_2/review_agent.html`、`agent_reviewed_candidates.jsonl`24、`agent_priority_candidates.jsonl`18、`agent_needs_visual_evidence.jsonl`6、`state_mcq_candidates.jsonl`12。参考输入与评测输入分离；最终报告`reports/impact_qa/state_qa_results.md`，逐请求统计与来源哈希另存。只有7种唯一开放问句、1个参与者，不能声称泛化性能或完整异常覆盖。


## 2026-09-18：v10.2逐题质量复审

- 范围：当前24开放题＋12MCQ，3个front原视频，未重审v7–v9。新增scripts/prepare_state_quality_audit.py用于CPU解码/抽帧和源字段统计；scripts/record_state_quality_audit.py序列化研究代理直接审查决定，不是新的自动质量判别器。
- 环境预检：.venv-impact的torch2.10.0+cu129、av18.1、CUDA可用、7卡，每卡49140MiB；本轮仅CPU处理，没有新增GPU推理、训练或VLLM请求。未验证CUDA<=12.1兼容性。
- 证据：1280×720原帧裁剪xyxy=[400,330,850,640]；全程每150帧概览，12窗口末段按距末帧[180,150,120,90,60,30,15,0]抽样；3片分别68/68/69不同源帧，共205，22张图板均直接查看。不是连续视频播放；细部遮挡不能由放大解决。路径/帧号见frame_manifest.json，已有源帧复用支持恢复。
- 结果：开放题12保留候选、3动作范围改写、3完成/异常语义改写、3需补视觉、3同trial事实重复；MCQ6保留候选、3需补视觉、3暂缓异常用途。36条ASR状态复核一致，不报告为语义准确率。全部真人状态pending。
- 失败归因：负例在首次ASR=-1后0.5秒截断，实际仍安装；组件状态被扩写成不匹配的安装动作；轴承板细节遮挡；同一顺序事实重复和21/24 Yes偏置。002左手null带异常，不能把其三个负例一概称双手正常；003/004末帧双手normal。ASR/PPR/TAS层级不能混同。
- 数据分布基线：恒Yes为87.5%二元极性，顺序题恒Yes为100%，MCQ恒选Correctly installed为75%；不是VLM实测准确率或开放解释评分。
- 输出：reports/impact_qa/state_v10_2_independent_audit/内保存完整中文报告、36题CSV/JSONL、6条待验证改写、统计和输入SHA-256。原候选不覆盖；本轮处置作为最新候选分流，旧priority文件仅作历史。两个新增脚本语法检查通过，源断言、题ID、图证路径及数量检查通过。


## 2026-09-18：v11视觉＋GT生成与v11.1粒度修订

- 预检torch2.10.0+cu129、av18.1、CUDA可用、7×49140MiB RTX4090；GPU0–5复用三组TP2 Qwen3.5-27B，每服务并发4。未验证CUDA<=12.1兼容性。原片H264/1280×720/30fps。
- 每题13–19个全幅原帧，2.5–81.233秒范围；253不同源帧、18不同审阅图板，均由研究代理直接查看。含GT动作边界，标注辅助采样，非连续播放。24个题意8类；59个源JSON引用/哈希核验通过，先检查first10。
- 按用户补充，实际生成请求包含视频帧、GT原始记录与GT参考答案；模型输出自然问答。GT文本核验不看图，无GT视觉复核不看参考答案/执行标签。导出的评测输入只含问题、流程、时间、哈希媒体和MCQ选项。
- 冒烟2/2、v11正式24/24、v11.1针对6题均完成。文本核验全通过不作准确率。v11独立视觉8自称answerable/16uncertain，其中3工具答案缺少GT要求的刀头类型；v11.1把工具题降为螺丝刀大类，state=0改问是否安装。v11.1视觉6自称answerable，但部件身份解释仍有幻觉，因此不照单接受。
- 最终24开放＋24MCQ，代理处置15优先候选、3身份待补、3时长待定边界、3异常可见性待补。7Yes/7No/10描述、11种问句；MCQ A/B/C=7/11/6。只有1参与者3trial，无训练与独立泛化评测、无准确率/Recall@1。新增异常题均handling，不宣称异常类别平衡。
- temperature0.1/top_p0.8/seed20260918/thinking关闭，生成650/source700/visual750 tokens。共96API调用（含冒烟6、v11的72、修订18）；最大输入19076tokens，请求中位延迟16.10秒，含并发环境影响。v11恢复运行成功且复用缓存；每题运行文件和API缓存支持恢复。
- 失败归因：GT特异性超出当前视觉分辨率；独立视觉模型对组件错认或追加扭矩验收要求；稀疏帧难与GT拾取动作起止定义精确对应。修复工具类和未安装问法，其余明确暂缓。读取PSR探索脚本误把目录当JSON报IsADirectoryError，已改回明确TAS/ASR路径，未把PSR用作本批证据；当前cwd无git仓库，使用源哈希验证而非git状态。
- 校验：新增5个Python文件语法通过，源指针/哈希、48题ID、截止帧、评测字段隔离、生成实际视觉与GT输入、MCQ正确答案核验通过，v7的16冻结哈希不变。详见reports/impact_qa/gt_v11_results.md、gt_v11_release_validation.json。


## 2026-09-18：复查和全量候选生成门槛制定

只核查本地记录并写验收协议，未新增GPU实验、生成调用或下载。ASR训练64/验证10/测试18，参与者分别13/7/9；当时依据summary记录训练装配32条、另29条；v12核对实际bundle纠正为31条、另28条，详见下文。front只解压3条，不宣称全量媒体已展开。

提出训练内8trial开发、16trial冻结验收、目标200–300题的工程覆盖方案；总体通过≥95%、每类≥90%、严重缺陷0为拟议阈值，当前未达成。发布测试题真人双审属于质量建议，不是运行可恢复候选生成的新增权限条件。外部web检索和NIST页面打开均返回工具404，因此未引用外部统计结论，未将相关QA当独立样本给错误率上界。协议和待办已保存。


## 2026-09-18—19：v12跨执行开发、v12.1与v12.2修订

- 预检：torch2.10.0+cu129/CUDA12.9/av18.1；CUDA可用7×RTX4090 49140MiB。复用3个Qwen3.5-27B TP2服务8000/8001/8002，各并发4，单runner总12；v12尾批与v12.1曾同时运行各自池，短时间全局上限24，需区别单runner与所有进程上限。未部署8卡4服务，未验证CUDA≤12.1。
- 8个front视频按需从已SHA校验ZIP解压并校验CRC；原片H264/1280×720/30fps，8视频完整帧数及PTS检查。93合同、225源引用，原始first10预检通过；7类题型，因GT资格不足跳过3个计划题意。8名参与者，不是独立验收样本。
- 87个不同原生连续短片，H264/1024×576/30fps/CRF20；93范围1.067–287.1秒，中位9.567秒。模型video输入配置16帧＋4原帧锚点，图板8帧；690不同审阅原帧。模型不看连续全部帧。最终433不同输入媒体SHA-256留档。
- v12：93生成/来源/视觉各一次，全部运行ok，来源模型93pass，自报视觉36answerable/50uncertain/7unanswerable。v12.1：48题（24顺序＋16异常＋8正常）自然语法与同属性数干扰项修订，全部ok/sourcepass，视觉17/26/5。
- v12.2：24顺序题重新生成/来源审核，按字面排序问题中的两种动作，避免始终先提正确动作；69题复用旧生成/来源审核；93题全部明确时钟映射后重审视觉。93ok/sourcepass；视觉50answerable/38uncertain/5unanswerable。该轮同时修改了时间和24问句列举顺序，不是单变量性能提升实验。
- 逐题代理读93组问答与视觉短答案；自报answerable中39与GT短答案一致、11冲突（6顺序、3工具、2安装），全部分歧隔离。未把其余39认定为视觉证据通过。直接看图51个题意，跨8参与者；源知情、抽帧观察，连续播放0、独立真人0。6优先完整复查/11分歧hold/24异常正常视觉hold/52待完整复查。16异常题没有独立视觉确认，不进入全量。
- 生成极性23Yes/30No/40描述，MCQ A/B/C=33/24/36；题型内安装全Yes、未安装/进行中/正常全No，不能称类内平衡。多标签全部保留；6异常属性均出现，样本量与可见性不足。
- 推理参数temperature0.1/top_p0.8/seed20260918/thinking关闭，650/700/750 token上限。共564次缓存API调用（165生成/165来源/234视觉），最大prompt10236tokens，请求耗时中位20.391秒，包含服务队列影响。逐调用统计见gt_v12_api_stats.json；不将累加请求时长当批次墙钟时间。
- 失败归因：动词映射遗漏screw_on导致准备脚本KeyError，显式补映射后重跑，未形成部分合同；模型把native相对时间误当原视频时间，导致误拒目标片段，已明确换算；原顺序题正确动作总先提及与异常正确选项更长，分别调整问题排序和等属性数选项；细小工具、组件混认与长窗口稀疏帧仍未解决。部分复合动作名称仍待自然语言复核。
- 历史核查：实际train64=31Reassembly+33Disassembly，与summary32/32不同；此前3条之外剩28装配。当前8trial有历史ego暴露，另6trial相对已查历史未暴露保留（5参与者）＋10历史暴露回归，未混称16独立trial。保留集和官方test未在本轮生成或查看新片段。
- 校验：225引用/93帧数/93MCQ/186公开输入字段通过；GT生成视觉与答案共输入、视觉审核无GT的实际缓存请求核验通过；Python及HTML内JS语法通过。v7的16冻结哈希不变；v12.2恢复成功，1568缓存文件及mtime均不变，新增请求0。公开输入与私有GT审阅页分开；审阅页保存答案、选项和GT首次揭示时间，可导出，不自动签署真人通过。
- 产物：outputs/impact_qa/gt_v12_final；结论与下一轮媒体改进见reports/impact_qa/gt_v12_results.md。全量放行false，准确率/Recall@1未报告。


## 2026-09-19 v13视觉证据消融及定向补测

- 环境预检：torch2.10.0+cu129/CUDA12.9、av18.1；7×RTX4090 49140MiB，6服务卡占41459–41853MiB。复用Qwen3.5-27B三TP2服务，8000/8001/8002各并发4，所有推理批次顺序启动，总上限12。未验证CUDA≤12.1，无第四服务。
- 固定8开发trial/33题，7工具8顺序4已装2未装2进行中6异常4正常，四条件132条。4context512×288＋16target640×448，front固定ROI(300,180,1000,710)；D另加2官方图板。uniform与dense按原帧/30秒，状态末3秒，顺序每个起点8槽位，可因截断重复。GT辅助取窗、不向视觉复核泄露当前答案；原v12视频输入不是同协议基线。
- 主结果按一致/冲突/额外工具细类冲突/弃答：A9/6/0/18；B11/6/3/13；C14/5/0/14；D14/4/0/15。工具A2/7→C7/7；顺序C3/8，动作参考5/8，无序粗细关联6/8；异常6和正常4全部弃答。状态未装/进行中原主条件各2/2短答案一致。无准确率或Recall@1结论。
- 补测：从本地ZIP仅解压KI03AR28_A003_top的103354962字节视频；2工具同步加8帧后仍2一致，C已经2一致，无提升证据。AL07EJ17_A003另训练执行提供5张动作演示，每张3帧、1152×350；无序粗细关联同源，65次引用检查，不是像素部件标注或规范顺序。
- 安装参考首轮4题：3有效（2一致1冲突），1三次JSON截断失败；冲突响应有答案与解释矛盾。简短状态prompt另跑4正例皆一致，但解释过度；严格证据边界加2反例共6题，5一致1冲突，未安装gt_21由基线No退化Yes。另gt_233正确No却误述截止时刻仍使用已放回的螺丝刀。保留负例与文字问题，不推广该prompt。
- temperature0.1/top_p0.8/seed20260918/thinking关闭；主及参考max_tokens850、紧凑状态450。163有效响应记录、159不同成功缓存键；另1失败键attempt3。主唯一缓存prompt6885–8385/中位7107.5，全缓存最大9985，请求秒中位18.561，非批次墙钟。[gt_v13_api_stats.json](reports/impact_qa/gt_v13_api_stats.json)。
- 新失败归因：4个正常案例B/C输入完全相同、并发首次请求同键，缓存最后写入覆盖前次解释；每条件结果保留，短答案/弃答未变，不伪造精确HTTP次数。下版合并同键在途请求并保留逐次raw。分析器最初假定visible_evidence总是string，遇list报错，现显式序列化后统计。证据ID另1处target_09格式与target_9不完全一致，原文保留。
- 复查：直接看25不同目标dense图板、2top、5训练示例、3手册面板和1总览；163短答案阅读。源知情研究代理抽帧观察，真人0、连续播放0，短答案一致不等于解释质量通过。
- 校验：1564媒体哈希、65源引用、输入范围/时钟/GT隔离/固定问句通过；8脚本语法通过，v7的16文件和v12的17文件哈希不变；主132恢复零缓存新增/修改。缓存差异和引用格式问题保留为未通过项；独立验收和全量放行false，6未暴露trial未消耗。
- 产物：reports/impact_qa/gt_v13_results.md；outputs/impact_qa/gt_v13/review.html、compared_results.jsonl、agent_image_review.jsonl、recommended_input_policy.json；8脚本快照gt_v13_code_snapshot.json。原93开放＋93MCQ未覆盖。

## 2026-09-19 v14门槛、工具开发两轮与冻结独立验收

- 预检：torch2.10.0+cu129/CUDA12.9/av18.1，CUDA可用7×RTX4090 49140MiB；6服务卡占41459–41853MiB，第7卡18MiB。沿用Qwen3.5-27B三TP2服务8000/8001/8002，每服务并发4，总12；实验池顺序启动。没有第4服务，未验证CUDA≤12.1。记录gt_v14_preflight.json。
- 查看新验收视频前固定候选门槛：来源/媒体/隔离100%、严重缺陷0、综合≥95%/每类≥90%、视觉≥95%、完成≥99%、每类≥30不同事件，有限候选最低5trial/3参与者。原16trial/8参与者广覆盖目标保留并披露未达，不冒充论文标准或实测质量。
- 8旧开发trial全部46个合资格normal拾取（40螺丝刀/6扳手，全部右手）；首轮38短答案一致/7弃答/1冲突，二轮相同46事件为40/6/0。工具生成逐字约束固定问题与GT参考答案，三选一选项由代码置换；不宣称丰富开放问法。二轮同时修订空间输入和prompt，非单变量消融；1个旧成功转弃答。
- 输入原片front1280×720/30fps，每请求4context512×288＋16target；首轮target固定ROI(300,180,1000,710)、640×448，二轮同原帧改ROI(280,270,1020,700)、960×560、JPEG96，context不变。生成仍用首轮媒体，二轮无GT复核/公开输入用高有效像素媒体；GT辅助取窗、原时钟、动作结束帧排除，元数据/哈希保留。开发范围1.533–3.3秒，不等于模型输入连续视频。
- 开发代理直接查看46事件四帧概览和40候选前后帧对；发现1条私有before端点已拿工具，完整输入更早帧支持QA。私有观察/端点不导出为gold。6弃题保留，不等同事实不成立。
- 故障与修复：初始12条v14.1冒烟中7条ID格式校验失败、3弃答、2一致；原因是模型复制transport的`Frame target_0`，不是GPU/HTTP故障。新增已知ID去前缀及端点并入引用列表的可追溯规范化，原响应保留、未知ID拒绝，复用已缓存响应完成归一化回归，不改答案。并发同键竞争以ReliablePool在途合并和逐次审计修复；旧v7 API未改。一次临时图板命令误用系统python缺PIL，切换既有.venv-impact即通过，无安装依赖。
- 15文件与模型revision冻结后，从本地ZIPCRC验证解压6保留front媒体，无新大体积网络下载。6trial/5参与者全部33合资格事件（28螺丝刀/5扳手，右手），3个不合资格源段另列。生成/复核均33完成；冻结筛选28保留/4弃答/1冲突，保留率84.85%。没有据验收输出修改prompt或筛选规则。
- 验收盲审：11概览板覆盖33事件，另索引0/17/29的20帧详图，保存最终盲答后揭示GT/模型；32可辨认、1不确定。揭示后读全部33问答及解释，查看28候选7证据对板、弃题1/2/4的20帧板。研究代理抽帧观察，真人0、连续播放0；不是每题20帧全部逐帧审核。盲答SHA256为4901dbf3121f00a27628b263c9c568407b9191577f2089a6105aea38670021aa。
- 代理候选质量28/28、具体视觉支持28/28，保留候选严重缺陷未发现；弃题中4实际可辨认、1继续hold。4个可辨认漏筛集中ER07AD15两trial，3漏看pickup＋1邻近工具混认。保留25螺丝刀/3扳手（89.3%螺丝刀），选项0/1/2为10/8/10；自然偏斜不能称平衡。28<30，release=false，仅事件数门槛失败，不能将开发样本、改写或手工救回事件补进冻结分母。
- 参数temperature0.1/top_p0.8/seed20260918/thinking关闭，max_model_len32768；生成180、首轮视觉300、追踪350输出token上限。204不同成功缓存键=79生成＋46首轮视觉＋79追踪；prompt5909–10348、中位6060。审计含缓存命中，未把缓存数等同HTTP尝试数。统计gt_v14_api_stats.json。
- 校验：66源引用、1188不同图像哈希、56公开输入/MCQ/请求GT隔离/时序范围；冻结开发和验收恢复runs及audit内容和mtime不变，新增请求0。3项单元测试通过、12文件语法通过；v7的16文件、v12的17文件及v14的15文件冻结哈希不变。核心日志和旧产物未覆盖。
- 产物：reports/impact_qa/gt_v14_results.md、gt_v14_acceptance_final.json、gt_v14_gate_evidence.json、gt_v14_release_gate.json；outputs/impact_qa/gt_v14_frozen_acceptance/reviewed_candidates.jsonl共28事件（28开放＋28MCQ），标agent_reviewed_candidate_gate_blocked。gt_v14_exposure_manifest.json记录6trial已消耗，不能再次称未见。全量生成未启动；安装/顺序/异常没有随工具类放行，212异常清单仅为后续证据资格准备。

## 2026-09-19 v15：输入顺序、模型诊断与分歧复查

- 预检torch2.10.0+cu129/CUDA12.9/av18.1，7×RTX4090 49140MiB；原3个27B TP2服务正常，各并发4、实验顺序运行。新增8B诊断仅在GPU6，8003、TP1、bf16、eager、32k、并发2、gpu_memory_utilization0.8。未验证CUDA≤12.1。全过程无新增模型/大视频网络下载。
- 实际发现v14请求先4context全窗、再16target动作起点，时间回跳。chronological20只重排同20原图/原prompt：46开发43一致/3弃答/0冲突，较40基线增加3且无回退；33已暴露回归29/3/1，2旧失败改善、1旧成功回退。失败的旧33不能重称独立验收。
- transition8用2context＋6target（槽0/3/6/9/12/15），同问答/GT；状态分解prompt。初始10冒烟4一致/2弃答/4未知Picture ID错误；原输出和prompt归档，明确合法ID后10题8一致/2弃答。全46为44/2/0；全33为29/2/2。新增一致有拾取证据仍不清例，不按数值最高选型。
- endpoint8同8时间点和transition prompt，仅context改原片固定ROI(280,270,1020,700)、960×560 JPEG96裁剪，其他6图完全不变、PTS验证；开发44/2/0（5改善1回退），回归29/3/1。inventory8同图片仅改prompt比较移走/留下工具，开发43/3/0、回归29/2/2。两条件仍在ER07AD15扳手事件认错邻近螺丝刀。
- pairboard使用同刻context_0/3左右并排1920×600，显式两面板原始秒数和ID，复合图不冒充单帧。开发37/7/2、6旧成功回退，停止向33回归扩展。所有失败版本保留，没有重试到期望答案才统计。
- Qwen3-VL-8B-Instruct诊断使用本地目录，模型标识和config/index/权重stat revision显式区分27B，缓存不串用。初次启动因系统libstdc++缺CXXABI_1.3.15失败，复用原服务LD_PRELOAD后成功；模型加载16.64GiB、KV可用18.91GiB。固定10开发同chronological20/原prompt：5一致/1弃答/4证据校验失败；部分失败响应还把螺丝刀说成扳手，端点null或毫秒整数，未猜测映射、未放宽规则、未扩展。任务自建8003进程组已停止，保留三27B服务。
- 参数各条件temperature0.1/top_p0.8/seed20260918/max_tokens350，27B thinking关闭；8B传入同接口配置，实际sampling defaults另存gt_v15_crossmodel_preflight.json（未显式覆写的top_k=20）。382不同成功JSON缓存键，包括8个两轮冒烟中的结构失败响应；不把JSON成功当证据通过，不将缓存键数当HTTP尝试次数。
- token/时延：chronological20 prompt10300–10348，中位单请求16.7–17.4秒；transition8约4.2k，中位7.9秒；endpoint8约5.1k，中位8.8–9.2秒；pairboard约1.6k，中位4.5秒。时间含服务排队，非端到端吞吐，不据低token版本夸大可用效率。
- 本轮直接看6开发20帧板、3开发8帧端点板、2回归端点板、6张原尺寸960×560端点裁剪；来源/模型知情，真人0、连续播放0。已核验相同问答和原图的历史直接审核被继承，不宣称本轮重看完79全部输入或382解释。开发e55b端点清楚显示绿柄工具离桌并在手中竖直操作，新增支持记录；4f1130/451b/39cf6仍hold。f704的模型after仍选得过早，私有端点不导出gold。
- 最终改为主复核＋有记录的直接证据分歧处置：79事件主模型提出72，7分歧中4复查支持、3hold；最终76支持=开发44＋已暴露回归32。相比上轮40＋28多8，不能视作新独立准确率或自动模型提升8。开放76＋MCQ76，65螺丝刀/11扳手，全右手normal；选项位置0/1/2为23/28/25。
- 公开输入统一22图=20原图时间排序＋2同刻detail_context端点，原时钟、GT辅助取窗声明；GT参考答案、选项唯一性、模型解释非gold分开。源知情代理审查候选，不是人工金标准。
- 核验158引用、1738不同图像hash、152公开输入隔离/时序/MCQ通过；主79恢复runs/audit内容和mtime不变、新增请求0；8测试通过，14新增Python及启动shell语法通过。v7的16、v12的17、v14的15冻结哈希不变，旧gt_v14_release_gate.json不覆盖。
- 产物outputs/impact_qa/gt_v15_reviewed，reports/impact_qa/gt_v15_results.md、gt_v15_final_summary.json、gt_v15_comparison.json、gt_v15_api_stats.json。新流程未做独立冻结验收，full_scale_release=false；旧33复查32支持不能用来修改原28冻结结果。仅读官方val trial名称，未读其新GT/视频；官方test未动。仍需新独立来源、状态/顺序/异常证据开发。

## 2026-09-19 v16 四角色质量筛选及候选生产启动

- 预检CUDA可用7卡，RTX4090每卡49140MiB，卡0–5使用41459–41853MiB，卡6为15MiB；torch2.10.0+cu129/CUDA12.9，av可导入；8000/8001/8002 models均HTTP200。3×Qwen3.5-27B TP2，每服务4、总12。未验证CUDA<=12.1。
- 新增四角色prompt、quality_v16共享schema/证据检查、准备器及带全局锁runner；temperature0.1/top_p0.8/seed20260918/thinking=false；max_tokens800/550/1100/600。源及媒体预检156事件351引用，105事件20图/51事件8图，全部按原时钟排序。
- 6项测试覆盖虚构证据ID、逆序、缺失事实检查、选项逻辑不一致、自信但工具冲突、类型伪造、不确定性及盲答payload隔离，全部通过。Python语法通过。旧v7/v12/v14/v15冻结分别16/17/15/19文件均未改。
- 混合冒烟17事件，耗时99.17秒，6 model_passed_unvalidated /11 quarantine /0 schema或运行错误；每事件4角色，缓存实际请求统计另计。通过：未安装2、进行中2、观察顺序1、工具1；异常类别2、动作正常性2、安装完成2全隔离。已知不明确工具39cf6/451b均隔离，不能把此17例当独立准确率。
- 启动batch001共156事件；并行仅CPU提取媒体，为其余17训练trial从已有ZIP解压/CRC核验并准备合资格工具段，无额外大视频网络下载。val/test不使用。正式发布仍false。

### v16生产收尾与v17充分数据入口

- v16两批230事件=153工具（31训练装配trial，125螺丝刀/28扳手，149右手/4左手）＋77操作/异常开发事件。初次墙钟782.368秒＋444.678秒。primary75通过/136隔离/19schema拒绝，非准确率。912不同成功JSON缓存响应，6816713输入token/174808输出token；缓存键不是HTTP尝试数，也不代表全部发生在当前批次（含冒烟复用）。19拒绝归因12私有审核文本超字数、4高等级却无拾取端点、3选项列表与逐项判断矛盾。保留原始结果。
- 17新增训练视频从已下载ZIP提取/CRC，74新增工具事件；工具片段1.533–4.067秒，20抽帧，未增加官方val/test暴露。全部已有训练历史暴露，不宣称独立验收。
- 无GT答案的两帧复核68工具：29支持/37证据不足/2schema拒绝；7非工具留专项复核。导出29开放＋29MCQ、私有证据和无GT评测输入；formal_release=false。代理直接看11不同事件（3完整20帧板、8引用证据板/组），源知情，真人0/连续播放0。
- v17新增230题型证据包/2653上下文源引用；固定17实际补取锚点并核PTS/hash，最多28图含参考，状态题无未来帧/状态/动作起点，异执行参考不与目标trial重合。只17媒体已补齐，其他是计划，不能混称230补帧完成。
- 17资格请求沿用3×TP2、每服务4，max_tokens850，其余采样参数不变；6ready/8needs/3schema拒绝。拒绝归因2个answerable/grade/needs矛盾、1个可回答事实只引用参考没有目标证据。无GT资格自信误认工具及组件，后续生成不能据此直接放行。
- 6ready真实执行完整GT＋视觉＋公共流程＋私有邻近动作/状态生成及三审，max_tokens800/550/1100/600，1候选/5隔离/0schema。该1条与旧工具事件重叠；未证明v17准确率提高。保留独立目录与冻结快照。
- 13项新测试通过（v16校验6、证据包4、资格3），Python语法通过。历史冻结不改；五个runner完成断点恢复检查，逐事件记录及请求审计不变、0新增请求文件。初始耗时另保存，避免把恢复耗时当首次吞吐。

## v18：213媒体补齐与230事件候选生产

### ATR双视角v19/v19.1与原生视频v20（2026-09-20）

- 预检7×49140MiB、torch2.10.0+cu129/CUDA12.9/av18.1，3个Qwen3.5-27B TP2服务HTTP200。vLLM0.18.0/transformers4.57.6，context32768。CUDA<=12.1未验证。无模型训练。
- ATR训练ego/front匹配363对，预先固定17不同trial/7参与者，其中12工具错误；最小匹配IoU0.4668。434去重来源/952图确认。v19每组7问题槽+生成4200/盲答2200/审查3000token，3服务各4并发，temp.1/top_p.8/seed20260918/thinking=false。
- v19整组严格校验33错误/1完成，耗时263.65秒；原因主要后续变化仅引用after没有before。v19.1逐题适配器保留原失败项目，隔离33缺端点和2选项错误，其余项目继续，34/34完成、耗时288.41秒（生成缓存复用）。ego64草稿/16模型筛选，front68草稿/12筛选；共132开放+MCQ草稿，非独立准确率。恢复136文件不变、零新增审计，6测试通过。
- 原生视频用file URI、opencv解码fps与num_frames双约束、HF do_sample_frames=false。目标8fps/64帧/8秒窗/1秒重叠，前后文2fps/64帧/32秒窗/2秒重叠。34视角制成92窗，实际6–64帧。视频宽960，总时空像素预算16777216；64帧HF实测grid32×24×42=8064token，对应每帧672×384。首次本地HF测试未剔除loader metadata.do_sample_frames导致构造报错，按vLLM同样剔除后通过，不是服务端失败。
- 3事件×2视角的12 GT视频窗口＋6无GT目标请求，18 HTTP模型响应成功，15基本选项/时间校验通过、3选项不足3项拒绝。初始134.85秒，最大prompt12092token。发现扳手无GTego误认螺丝刀；视频不自动提高工具身份正确率，存在第三人称/题型漂移，未全量放行。
- 6请求同时64帧、每服务2并发，全部成功，8.19秒，单请求实际输出14token（上限160），采样显存峰值42191MiB≈41.20GiB；不能外推长QA同样并发。长QA配置每服务1、总3，max_tokens1600。详细配置见video_v20_configuration.md。
- 6配对图板AI源知情直审，真人0/连续视频0。7861双播放器、单视角保存、视频模式原始输出折叠显示；HTTP200和两个Range206，未真实浏览器交互。原7860继续运行。代码/配置和原始响应均保留。

### 标注结构只读核验（2026-09-20）

- 用户要求详细说明annotations。本地TAS-B/TAS-S各560JSON全量统计；TAS-S21995段全has_anomaly=false/meta_activity=none，必须禁作正常性证据。TAS-B67492段，normal56482/anomaly9512/recovery1498；多视角多手计数，不是独立错误事件数。
- ASR92文件=46装配/46拆卸、17状态维；PSR同92执行。以MA07LF04装配001的动作419–461及PSR2673/2778事件核对JSON、逐帧TXT、NPY与CSV，示例源动作段确为含终点。未做模型调用或修改冻结产物。网页工具404、直接远端读取未成功，报告明确依赖已下载官方v1.1和论文快照。

### 人工审核前端（2026-09-20）

- 独立`.venv-review`：Python3.14.7、Gradio6.28.0、imageio-ffmpeg；CPU截取H.264/yuv420p/CRF21/veryfast，单转码2线程、预制并发4，无GPU使用。原始pip源下载缓慢，切换清华镜像安装成功，依赖锁文件human_review_requirements.lock.txt；生成环境不改。
- 输入161草稿，默认33筛选候选，支持工具/观察顺序筛选。161原始MP4全部存在、时间区间有效；161题目片段全部转码并完整解码成功，first10与预检报告保留。原始区间最长287.1秒，未人为截短。上下文模式扩展前后3秒并明确播放器内题目范围。
- 人工SQLite独立记录，临时库验证保存、修订追加历史和JSONL导出成功，正式库未写入模拟人工记录。模型记录只读。3新Python文件语法检查通过。
- 后台绑定0.0.0.0:7860；10.112.70.171页面HTTP200、视频Range206/video/mp4，Gradio客户端核验工具/顺序题、10条顺序筛选、上下文切换；未真实浏览器交互测试。入口与重启说明见reports/impact_qa/human_review_ui.md。

- 预检7×RTX4090 49140MiB，卡0–5占41459–41853MiB，卡6为15MiB；torch2.10.0+cu129/CUDA12.9、CUDA可用7卡，3服务HTTP200。继续3×TP2、每服务4、总12，未验证<=12.1。
- 230事件/31训练trial全部实际物化，最多28图；5371唯一媒体hash、2129去重源引用检查通过。原17冻结输入未改，独立目录输出、按trial检查点；val/test不动。
- 私有字数校验修订：保留原文＋style_warning，2000字符硬上限，公开问答长度及语义/证据检查不改。旧19拒绝离线重放12格式恢复（4待审模型候选/8仍隔离）、7仍拒绝，无新增API、旧记录未覆写。
- 6项新测试＋原6项baseline测试通过；新增代码语法通过。固定17冒烟8needs/3schema/5semantic quarantine/1evidence_screened，耗时3.068秒主要复用缓存，不能当新生成速度。三schema问题仍是资格逻辑矛盾或缺目标证据，未做语义自动修复。
- 230事件新版batch已启动，完整结果、原始响应、资格及各审查阶段记录到outputs/impact_qa/evidence_v18_batch；首次完整耗时由initial_completed_summary保留。正式发布仍false。

### v18完成与恢复检修（2026-09-20）

- 全230事件完成，首次1876.669849秒，约7.35事件/分钟（含缓存复用）。162进入生成，161结构合格草稿=151工具＋10观察顺序；1生成引用ID错误。最终33筛选工具候选、62资格缺证、89语义隔离、34两帧隔离、12schema拒绝、0运行错误。33开放＋33MCQ公开输入完成。
- 筛选33覆盖18trial/10参与者，31螺丝刀/2扳手，全部右手，问法仅1种。与旧v16的29交集18、新增15、旧未保留11；不是独立性能对照。全部77非工具仍无最终保留，不代表原GT错误。
- 944不同成功JSON缓存响应，12840550输入/175117输出token，包含历史复用，非本轮新增token或HTTP尝试数。相同模型多角色，未做独立概率校准。2事件私有文本字数警告，语义门槛未变。
- 12拒绝归因：4 pair.after_state=grasping非法且未证实held_away；4错误帧ID（资格3、生成1）；1资格无目标证据；2资格逻辑矛盾；1盲答缺转换证据。89语义隔离全部盲答证据等级不足，未来可先短路以减少审核请求。当前批次保留完整归因，不回改冻结输出。
- 直接查看33候选全部引用前后图板，支持粗粒度工具拾取，部分运动模糊/遮挡已逐条记录。核对全部33问答/选项一致；这是源知情AI审核，真人0、连续视频0，不是独立gold。
- 中断后恢复1.883秒，1178个事件/审计/关键输出hash不变，无新增审计文件。10个冻结清单一致；首次辅助核验读取v17 manifest字段错误，改为source_hashes后通过，非代码内容漂移。6新＋6基线测试通过，7新增Python文件语法通过。
- 结果和下一步优先级见reports/impact_qa/evidence_v18_results.md；生成草稿、筛选候选、隔离原因分别保存。formal_release=false、independent_acceptance=false，官方val/test未用。


### v21 描述优先设计与静态验证（2026-09-20）

- 用户要求先设计，未运行模型/下载媒体/改变服务；新增生成QA=0。当前产物为六阶段prompt、3个虚构few-shot、配置、输出Schema及流程报告。不是已经上线的生成流程，7860/7861仍展示旧结果。
- 静态检查：Draft202012 Schema有效，3示例×3阶段=9对象通过阶段和顶层验证；示例引用有效、开放QA无MCQ字段；固定异常六属性与本地34个ATR案例的标签集合一致。校验记录及内容hash见reports/impact_qa/descriptive_v21_static_check.json。没有新增Python/SH源文件，故无新增代码语法检查对象。
- 设计参数尚未实测：目标原始解码帧全覆盖、每批8帧＋1参考帧、长边960；原生视频观察沿用v20的8fps目标/2fps上下文。三服务各1并发，输出预算3072–6144token，输入＋输出＋1024余量不超过32768；跨批实体与时钟须在实现阶段验证。
- 硬件沿用历史7×49140MiB、3×TP2 Qwen3.5-27B服务配置，本轮没有重新探测显存/CUDA。已有环境CUDA12.9；<=12.1仍未验证。静态JSON验证使用.venv-impact内jsonschema，无GPU调用。
- 失败归因：历史强制三选项/65词上限与本轮用户所需详细开放描述冲突，属于任务定义偏差，不能当模型能力结论。新方案分离开放描述与固定MCQ，首次视觉观察不给标签以减少诱导，后续出题接收视觉证据和GT核对记录；实际效果待试跑与人工核验。


### v21真实试点、容量和定向修订（2026-09-20）

- 预检torch2.10.0+cu129、CUDA12.9可用7卡；3个Qwen3.5-27B TP2服务8000/8001/8002 HTTP200，context32768，每服务1并发。卡0–5已分配41853–42191MiB，卡6约15MiB；<=12.1未验证。不是8B单卡测试。
- 源GT三个ATR配对事件6视角，1082原始目标帧全部解码保存；切23核心clip约2秒并加<=.25秒重叠。帧数一致、源PTS映射最大浮点误差1.35e-14秒；原始完整目标视频仅准备，不全量推理。
- 首8帧冗长合同5444输出token/169.27秒，存在背景重复与不可靠可见性/力度断言；紧凑版同8帧1394token/44.67秒，仍存在动作变化漏报，非准确率提升。
- 正式小样每视角选1核心clip，共327原始帧，44帧批次+22后续阶段=66请求，1223.33秒。327卡片结构通过、5详细描述、9开放QA草稿、4clip完整流程；2失败分别描述4096token截断、审核引用未见f0002947。输出预算frame3072/video3072/description4096/QA4096/audit4096，温度.1/top_p.8/seed20260920，关闭thinking。prompt最大17694。
- 冻结原始结果后附加64/128帧长窗：64前窗、60后窗HTTP/结构成功，但事件边界过宽/末端动作遗漏；128帧首回3072输出截断，精简引用复测923token却引用4个未采样帧拒绝。两次128帧输入均推理成功，无OOM。像素预算16777216，64帧672×384/8064visiontoken，128帧480×256/7680visiontoken；峰值42191MiB≈41.20GiB/卡，属于vLLM已分配显存，非增量。
- 定向修订56帧原生视频全送＋8图、移除完整虚构答案、去除旧卡片，3阶段161秒左右，得到2QA但仍不可靠扳手插入/时间引用，审核要求修订。多个因素同时变化，非受控few-shot消融。盲两帧15秒仍推断未见释放/拼接，未解决视觉误认。
- 合计75请求71结构成功/4错误，609378输入/124200输出token，最大prompt17731。71/75不是QA准确率。复查1clip待人工/5隔离，repair隔离，真人通过0。原始12条固定MCQ按完整ATR区间GT生成，均异常正例、非视觉候选，不配给较短clip。
- 实际复查看6×6帧核心图板、2×12长图板及若干全尺寸帧，AI审核而非真人/连续视频复核。发现46词few-shot复制、手别颠倒、无运动误判、动作/帧错位，postcheck记录核心区间越界和不完整审核。报告descriptive_v21_pilot_review.md。
- 5项合同测试通过；新增源文件语法通过，基线冻结源hash一致。7862审核UI复用SQLite，页面HTTP200/视频Range206/gradio load_case接口通过，未真实浏览器交互测试。既有7860/7861未改。

### 长视频QA构造文献调研（2026-09-20）

- 完成8项重点工作及7项补充工作的方法对比；保存官方论文HTML/文本、arXiv查询和可访问官方仓库目录/README/源码快照。原文短摘录逐条与本地论文文本核对；详细路径见reports/impact_qa/long_video_qa_generation_survey.md。
- 联网工具返回404，改用直接HTTP访问arXiv官方API/原文与GitHub；部分链接超时/404，保留fetch_manifest中的失败状态，不等同于资源不存在。Python环境无bs4，采用标准库HTMLParser提取文本，未安装依赖。
- 本轮为CPU端文献读取与文档更新，无GPU推理、训练或新QA；未改既有服务和prompt，没有新增视频下载。硬件、CUDA和显存未重新测量，沿用v21实测记录但不作为本轮实验数据。
- 没有新的QA质量指标。论文中的数据规模、人工耗时和过滤precision均为作者报告，不是本项目复现。下一轮需以人工事件参考和错误审核测试验证事件表/分层记忆，尚未运行。

### v22事件表实测与诊断（2026-09-20）

- 实施/结果见reports/impact_qa/event_v22_results.md；80实际请求、711148输入/31227输出token。原6clip复用15/17/19帧8fps原生视频＋8静态图；审核逐批附全量引用帧。3×TP2 Qwen3.5-27B、context32768、每服务1并发；温度.1/top_p.8/seed20260920。
- 首版6请求4端点字段冲突/2空白循环截断，已归档。改端点程序派生并显式提供Schema后，r1自动27请求全结构完成，5QA草稿/1隔离；代理复查5草稿均有重大问题，正式通过0。不是质量达标。
- GT核对仍把null解释成保持静态、把未知部件误认为气动扳手并称一致；字段作用域正确不保证模型语义正确。审核器测试27B正例4/6、错误误放1/6；8B正例1/6、错误误放1/6，且接受全部19候选事实。参考均代理看图非人工gold。
- GPU6单卡Qwen3-VL-8B复用旧启动脚本，32k/bf16/eager、客户端并发1；权重16.64GiB、KV18.91GiB、已分配38235MiB。初次遗漏已有LD_PRELOAD致CXXABI_1.3.15失败，复用scripts/start_impact_qwen3vl8b.sh修复。torch2.10.0+cu129/CUDA12.9，<=12.1未验证。
- 代理辅助22事件→6QA、16请求67.39秒；22事件保留不等于全部事件召回。两模型×6单帧盲看仍物体误认，27B部分帧避免插入幻觉但不足以证明方案已解决。
- 23clip实际采帧复现，1089hash核验；10合同测试通过，新增代码语法通过。92审核实例引用实际供给无缺失；11QA拼接/事件支持/无options检查通过。恢复0.274秒0请求。UI7863支持自动/辅助分支和v21对照，HTTP/API/Range检查通过，非浏览器实测。真人通过0。
- 局部质量前提未通过，长事件/分层记忆实验未启动；不以更多数据掩盖视觉事实错误。全部失败与隔离保留。
- 8B临时8003服务诊断完成后停止；原三服务和7863审核页面保留。v21源冻结哈希和v22最终资产哈希均复核一致。

### v23连续history试验（2026-09-20）

- 用户改变实验优先级后，执行403事件ego/front完整约14.5秒，各8核心clip，798原生帧索引划分无缺失/重复。每窗口原生video8fps/64上限，实际5–19帧，无额外静态图；最近2段＋滚动memory，完整局部账本持久化。局部阶段无ATR答案，GT仅末端出题提供。
- 3×TP2 Qwen3.5-27B，context32768，服务各1并发，同视频顺序、不同视角并行；温度.1/top_p.8/seed20260920，thinking关闭，输出2304/4096/3072。torch2.10.0+cu129/CUDA12.9，卡0–5约41853–42191MiB，<=12.1未验证。
- 首次20请求201.10秒，16描述＋2整合＋2QA，6开放题/4固定GT MCQ。视觉QA修订每视角完整事件64帧384×672，再2请求；总22请求166245输入/12504输出token，最大prompt17331，全结构完成。
- ego11/front9事件，整合ID覆盖20/20，各7continuation链接；保留ego末端工具移开。两视角8段各仅3种独特描述，存在history模板重复/早期方向继承风险，尚无人工事实召回率。初次答案ID泄漏已在修订中消除；front否定发生题仍违反正向约束，隔离1，待审5，正式发布0。
- 用户v22辅助17fd ego审核“通过”已读取，仅适用于该原记录。v23真人通过0。四历史合同测试与新代码语法通过，媒体/历史hash、前向引用、无局部GT、固定MCQ一致性检查通过。7864展示完整事件、局部输入/history和结果；旧7863保留。完整审核视频PTS误差<2e-14秒。
- 这是两段选定事件而非整条数分钟视频。真正长视频还需中间摘要与按ATR检索；现有一次整合遇超预算会显式失败，不静默截断。
- 恢复实测0新增请求/0.314秒，冻结源未变；原始成本保存summary_first_run.json。UI两视角各15输出、待审3/2题、视频Range206/1024字节通过；未真实浏览器交互测试。

### 审核界面统一端口（2026-09-20）

- 按用户要求将5个Gradio页面合并为一个进程、一个7863端口，默认history页面，其他轮次通过标签页切换；关闭7860/7861/7862/7864。旧各轮脚本启动入口也统一指向serve_unified_review.py。
- 复用原load/save与SQLite路径，不迁移或改写审核记录；无模型推理、无新增视频下载。界面源代码本次更新，实验生成代码保持冻结。检查记录outputs/impact_qa/unified_review_check.json；未真实浏览器交互测试。

## 2026-09-21 v24具体步骤QA

用户已保存v23 ego通过记录，但纠正QA目标。新增step_v24，不覆盖v23。Qwen3.5-27B沿用8000/8001（8002健康但本轮未占用），每服务并发1、TP2、max_model_len32768、temperature0.1、top_p0.8、seed20260920、输出上限4096。输入两视角各64帧原生video，附当前视角/当前区间GT和既有history。环境torch2.9.1+cu128，CUDA12.8，7张可见4090改装48GB（49140MiB），6卡使用约41853–42191MiB；未验证CUDA<=12.1兼容。

r0/r1/r2共6请求，126232输入/7931输出token；末轮2请求各45.55/58.92秒。最终6道可回答草稿、2道完成性待补证，全部新QA未人工审核，formal_release=false。r0存在内部标注措辞、工具题重复、从持物对象推断螺钉位置；r1仍残留annotated措辞及缺步骤名称引用；r2改进prompt与检查，保留全部原稿。当前B型试次无ASR，不强行将错误工具判为未完成安装。9个v24合同测试通过，验证极性、禁止泄露内部标注、描述题拒绝及引用/范围要求；不将这些结构测试当作语义准确率。

UI只监听7863，开放QA前置、详细描述折叠；旧v23通过记录保留，新QA独立合同未审核。HTTP200及load_case API15输出通过。新增完成性小样正在单独记录，不混算上述费用。

## 2026-09-21 completion_v24完成性对照

AL07EJ17_Reassembly_A_002_front的防振手柄末态对照：4800–5000帧（ASR=-1、6.7秒、模型53帧）与4800–5213帧（ASR=1、13.8秒、模型64帧）。源视频5214帧全部PTS验证30fps时间轴，裁剪帧数量／PTS及采样状态区间验证通过。不带GT观察后带视频＋GT生成，产出同一具体安装问句的一否一肯两答案。4请求39493输入/684输出token，观察9.65/9.81秒，生成10.84/10.78秒。服务8000/8001/8002沿用Qwen3.5-27B、TP2、并发1；CUDA12.8，7可见GPU，运行前检查通过。

质量限制：两例模型均无法独立视觉确认机械安装正确性；代理检查首中末帧，晚期终帧手已移开，模型终态遮挡措辞过宽。未编造错误原因或把部件状态当整机完成。仅作为GT支持、待用户视频审核的QA样本，不计视觉准确率或正式发布。语法检查与9项v24合同测试通过；视频播放与审核状态使用同一7863验证。

主step_v24的front正确性问题另外由代理将install the screw改为tighten the screw以消除终态歧义，保留原模型输出与explicit edits/source_cache_key于review_ready；该编辑不代表用户通过。

完成性UI联调出现一次客户端403：Gradio client将JSON证据字典的path字段误识别为可下载文件，尝试下载未开放的ASR原文件。仅在展示JSON中改名artifact_path，保留磁盘原始数据和媒体权限；重启同一7863后4样本API均通过，2新增视频HTTP Range206；旧通过记录未变，新QA均未审核。两个生成脚本断点恢复均0新增请求。该问题属于展示协议，不是模型或数据失败。

## 2026-09-21 VLLM服务重启

按用户要求停止批次后检查无残留run_batch_v25进程；使用scripts/start_impact_pool.py --services 3重新启动Qwen3.5-27B。8000使用GPU0-1，8001使用GPU2-3，8002使用GPU4-5；每服务TP2、max_num_seqs4、模型上下文32768、显存利用率0.85，启动命令由scripts/start_impact_vllm.sh执行。三端口/v1/models均HTTP200且模型名impact-qwen35-27b。首次10秒文本请求超时，模型加载完成后重新以90秒超时请求成功：8000返回impact-qwen35-27b、finish_reason=length、内容OK。重启后请求代码不变，具体路径见本记录回复。

## 2026-09-23 v26 GT-only revision and Qwen3.8 recovery

- 用户审核旧 v26 结果后确认动作题过度呈现时间区间和原子序列，缺少完整的“工具—部件—装配/拆卸行动”概述。本轮把 `action_sequence` 首事实改为整体操作摘要，随后保留全部 TAS-B 原子动作；答案不再输出时间区间前缀。生成 prompt、自动复核 prompt、紧凑 GT payload 和 7863 展示逻辑同步更新。
- 代码验证：`python -m unittest tests.test_component_v26 -v` 共 24 项通过；Python syntax check 通过。GT-only `component_v26_gt_r1` prepare-only 完成：112 front 视频索引、92 有 ASR、12 选定视频、23 clip、4 个无 ASR 视频、622 个小于 1.5 秒 ATR 错误排除。A arm 只读标注，`prepare_media=false`，未向模型发送视频。
- 硬件环境仍为 7×NVIDIA RTX 4090、每卡 49140 MiB；本轮启动服务前尚未占用 GPU。7863 由 `.venv-review` Gradio 长会话恢复，绑定 `0.0.0.0:7863`，当前页面只显示 GT-only 最新 QA。
- Qwen3.8-27B 本地 tree 清单为 32 个文件、18 个 safetensors 分片。当前 1–13 分片已完整，已完成分片做过 SHA-256 匹配；14–18、`model.safetensors.index.json`、tokenizer 和视频预处理配置尚未完成。`outputs/impact_qa/qwen38_integrity.json` 明确记录 `complete=false`。第一次 Xet 下载返回 401，改为 `HF_HUB_DISABLE_XET=1` 普通 Hub 断点下载；持久会话 PID 5760 正在续传，不能在完成前启动 vLLM。
- 失败归因：服务器重启同时终止了旧 Qwen3.5 vLLM、7863 和旧 batch 会话，导致旧 `component_v26_r1/progress.json` 停在 38 个 arm 完成、4 个 running 的历史状态；旧结果没有删除或覆盖。当前恢复优先级是完整模型→两个 TP2 服务（8000/8001、每服务 `max_num_seqs=8`）→4 clip GT-only 冒烟→人工检查→23 clip 扩展。

### 2026-09-23 v26 GT-only recovery completion

上面的模型/服务条目记录的是恢复开始前的中间状态；恢复已完成。`outputs/impact_qa/qwen38_integrity.json` 现在为 `complete=true`，32 个正式文件全部检查通过，18 个 safetensors 分片逐一 SHA-256 一致。两个服务以 Qwen3.8-27B、TP2、bf16、32768 context、每服务 `max_num_seqs=8` 启动在 8000/8001；`/v1/models` 和最小 JSON 请求均返回 `impact-qwen38-27b`。本机 preflight 为 7×RTX4090 48GB、torch 2.10.0+cu129、CUDA 12.9；CUDA≤12.1 未验证。

GT-only A arm 使用 `prepare_media=false`，模型请求只含 GT 事实和问题计划，未传视频。4 clip smoke 先完成，随后全量 23 clip 完成：23/23 arm completed、46/46 generate/review 请求 `ok`、无 contract repair、解析错误或 API 错误。154/154 开放式问题为自动复核 `keep`；题型计数为 action_sequence 23、step_completion 25、tools_parts 38、observed_order 22、duration 46。固定 GT-MCQ 40 条（七选项定义与 deterministic correct IDs）存于 `fixed_mcq.jsonl`。总 token 229,822（prompt 177,893；completion 51,929），请求总记录耗时 2,386.7 秒；端点 8000/8001 分别处理 27/19 个请求。

离线全量合同审计确认 23 个 action_sequence 均以 overall 摘要开头，包含 GT 要求的工具/部件短语，后续 fact_id 顺序与全部原子事件完全一致；公共答案没有秒数/时间戳前缀。该结果是自动合同与模型复核候选，不是人工正确率或正式发布结论。7863 已更新为 `http://10.112.70.171:7863`，选择 clip 可播放对应的 23 个审核视频（视频仅供人工审核，不进入本轮模型输入）；`progress.json` 标记 `human_review=pending`、`formal_release=false`。

## 2026-09-23 v27 服务恢复、r5 冒烟与时长区间修订

- 服务按用户要求重启：`scripts/start_qwen38_vllm.sh` 运行 Qwen3.8-27B 两个 TP2 实例，8000 使用 GPU0–1、8001 使用 GPU2–3；每实例 `max_model_len=32768`、`max_num_seqs=8`、显存利用率 0.85。模型预热约 155 秒；权重就绪后两端 `/v1/models` 均返回 `impact-qwen38-27b`，并行最小对话都返回 `READY`。环境为 `.venv-impact`、torch 2.10.0+cu129、CUDA 12.9、7×RTX4090（每卡 49140 MiB）。预热后服务卡占用约 40799–40823 MiB/卡，4–6 号卡空闲；未验证 CUDA≤12.1。
- 7863 审核页恢复为 QA 页面，Gradio 使用 `.venv-review`，绑定 `0.0.0.0`；`http://127.0.0.1:7863/` 与本机网卡地址 HTTP 200。页面读取 video+GT 结果，按 clip 展示开放题与异常 MCQ，并在人工选择 clip 后生成原片片段。模型 API 只绑定本机 127.0.0.1:8000/8001。
- r5 数据预检与 v27 r4 相同：112 个 front 视频索引、92 个有 ASR、62 个可用训练视频；挑出 6 个视频/12 个 clip，622 条小于 1.5 秒 ATR 异常过滤。r5 前 4 clip 完成，14/14 请求 `ok`（4 select、2 个盲视觉异常检查、4 generate、4 review），共 141194 prompt token、9123 completion token，请求耗时合计 679.74 秒；8000/8001 分担 8/6 个请求。无 OOM。
- 4 clip 生成 20 条开放式候选：overall 4、component completion 4、observed order 4、duration 7、detailed operation 1。两段入选的 ≥5 秒 ATR 异常都经盲视觉检查后未找到足够区间内证据，没有导出异常 MCQ；不可见 GT 异常不被强行转成视觉题。自动复核 20 条全标 `keep`，但全部仍 `human_review=unreviewed`、`formal_release=false`，自动复核不计人工通过率。
- 人工核对输出文本与参考事实发现 duration 边界缺陷：同一拆卸目标同时来自一段 47.8 秒 episode 与覆盖 157.4 秒的 component-state group，造成题目相同但答案时间冲突；一条 assembly 标签还将 `install` 重复写进 target（“install operation for install rotor assembly”）。四道 observed-order 的生成答案逐字匹配计划中的 GT 时序；detail 样例覆盖 11 个动作。r5 原始产物保留，失败归因为 episode/state-operation 重叠与动作标签未规范化。
- r6 已修订：优先使用完整 component-state 完成区间，重叠且目标相同的 episode 不再另出时长题；episode 标签动词从部件目标中移除；新增计划级重复重叠目标拒绝。12 个试点 clip 的 36/36 API 请求均成功，61 个 open 候选中模型选择 58 个（overall 12、detailed 9、completion 12、order 11、duration 14）；自动复核 57 keep、1 held（详细操作时间顺序冲突）。8 个固定 MCQ 候选均被视觉选题阶段以“缺少明确区间内证据”排除，最终 0 MCQ。所有 QA 仍待人工审核；没有把自动复核结果算作人工通过。
- 全量 annotation census（离线，只读，不调用模型）：112 个 front 视频均有可用媒体、完整双手 TAS-B 覆盖和组件操作边界；严格 train-only 范围为 62 视频、405 个含有效 TAS-B 动作的组件 clip（assemble 194、disassemble 211）。这些 clip 可构造 2,186 个开放题候选：overall 405、detailed 394、completion 664、order 330、duration 393；ATR ≥5 秒固定 MCQ 候选 80。其余 50 个非 train-exclusive/跨 split 视频另有 346 clip、1,929 open 和 61 MCQ 候选；若将所有 split 混在一起为 751 clip、4,115 open、141 MCQ，不作为主生成范围，以免破坏 split 隔离。
- 若保留 r6 当前每视频最多 2 clip 的采样逻辑，对 62 个 train 视频是 123 clip、677 open 候选、45 MCQ 候选；这与所有组件操作全量切分（405 clip）是不同的范围。当前在线 r6 仍是 6 视频/12 clip 试点配置，全量生成尚未开始。试点的模型筛选比例不能可靠外推，所以 2,186/80 是 GT 支持的候选上限，不是预计最终保留数。
- QA 未进行连续源视频逐帧人工审核；上述为文本与 GT 结构对照。7863 页面 HTTP、Gradio endpoint 元数据及视频 Range 播放验证通过；真人逐题审核仍待完成。

## 2026-09-23 v27 r7：开放QA生成职责与提示迭代

用户明确要求 open-end 问题和答案都由 Qwen生成，不由代码写公共Q/A。新流程将代码职责限定为内部候选题型/主题、结构化GT事实、类型约束和来源ID；Qwen在看完整clip+GT后筛题，并在 `v27_generate` 对每个入选候选同时生成公共问题和答案。输出的真实问句/答句来自 API 缓存中的 Qwen response；自动校验/repair不代写公共问答。MCQ仍固定由ATR GT确定答案，模型只判断视觉证据。

硬件/模型沿用当前服务：2个 Qwen3.8-27B vLLM API，localhost:8000/8001，每实例 TP2、max_model_len=32768、max_num_seqs=8；运行环境 `.venv-impact`，torch 2.10.0+cu129 / CUDA 12.9，7×RTX4090 48GB。没有重启模型服务。数据预检仍为112个front视频索引、92有ASR、62 train-eligible；6视频/12 clip试点manifest，排除622段小于1.5秒ATR错误。全量训练范围405 clips未启动。

r7p1 首轮取前4 clip，4次选题成功、4次生成中2次首轮因合同失败，两个 repair仍失败；失败原因是 overall 逐字强制所有方向/紧固件名称，以及 duration 把3个组件的聚合状态时间误当单项操作时长。输出和缓存完整保存在 `outputs/impact_qa/component_v27_video_gt_r7p1/`，未覆盖。

r7p2 改为只要求整体回答简要命名装配/拆卸、至少一个工具和1–3个主要对象；不要求枚举每个紧固件/方向名称。时长候选限定在完整位于clip内的单一TAS-B操作episode，≥5秒，同一动词/目标重复时只取最长一段；使用episode的GT窗口，而不是多组件聚合状态窗口，问题不得无依据声称“完成”。生成few-shot区分整体摘要、阶段步骤、否定完成性、不同操作顺序及时长边界。

验证：r7p2 Python语法检查通过；`tests.test_component_v26` + `tests.test_component_v27` 共37项全部通过。prepare-only 重建12 clip与59候选（51开放、8固定MCQ）；检查前10项输入结构，open candidate仅有topic/约束/GT source事实，未预写public question/answer。实际模型跑4 clip，4 select +4 generate +4 review =12 API请求，12次均ok；累计输入121,604 tokens、输出8,175 tokens、请求记录累计时长400.68秒。结果4/4 clip completed、18 open QA（overall4、detailed2、completion2、order3、duration7），自动复核18/18 keep；模型没有为缺少明确ATR视觉证据的样本强行生成异常MCQ。所有QA `human_review=pending`、`formal_release=false`，自动keep不计为人工通过。

代理文本/GT核对：整体答案均简洁且包含工具/主要对象；详细答案描述主要阶段，没有逐条复述手部动作；顺序题比较不同组件操作；时长值对应单一TAS-B episode的GT区间。样本小，尚未连续播放逐帧做人审，不能据此声称人工质量达标或推出全量通过率。r7p2文件在 `outputs/impact_qa/component_v27_video_gt_r7p2/`，完整Q/A和自动复核见各 `results/*_V.json`，API request/response见 `api_cache/`。

7863审核页面已在原单一端口重启并指向r7p2；本机 `http://127.0.0.1:7863/` HTTP 200，Gradio配置确认展示12个clip选项，其中已完成样本排序在前。网卡访问地址 `http://10.112.70.171:7863`。人工审核仍待完成。

## 2026-09-23 r7p2 全数据集（all-splits）生成与收尾记录

- 人工抽查阶段覆盖已生成的4个r7p2 clip及全部18条QA：每个clip检查64帧模型输入采样、画面证据、对应GT与Qwen自动复核。未发现事实冲突或误答阻断项；一条“adapter plate again”略显重复但与GT的分阶段拆卸对应。此轮为抽样帧对照，不代表对源视频每一帧的人工审片或正式验收。
- 按用户新指示取消train-only边界，使用全部112个front视角可用视频；manifest含751个组件clip（assemble349、disassemble402；拆卸clip可按ASR组件状态变化形成独立操作窗）。保留每clip的 `annotation_splits`、`atr_splits`、`asr_split`。对跨split视频计数为非互斥归属：TAS-B/TAS-S train 99、val 19、test13；ATR train97、val13、test13；ASR train64、val10、test18。过滤622条小于1.5秒ATR事件。
- prepare-only 形成2,826个内部开放题候选：overall751、detailed614、completion972、order71、duration418；141个固定GT-MCQ异常区间候选（不是最终保留数）。前10条样例字段只含候选题型/主题、GT支持和约束，无公共question/answer；由Qwen视频+GT选题后生成开放式Q/A。每个clip的实际问题数由模型判断，不能把候选总数报成已生成数。
- 预检环境 `.venv-impact`、torch 2.10.0+cu129、CUDA 12.9、7×RTX4090 48GB；CUDA可用、设备数7。8000/8001为TP2 GPU0–3；新8002为TP2 GPU4–5；三端均Qwen3.8-27B、max_model_len32768、max_num_seqs8、gpu-memory-utilization0.85。8002健康后单端8路并发文本请求全部返回 `READY`（约11–15秒），GPU4/5显存约40.1GiB/卡；GPU6空闲。CUDA≤12.1未验证。
- 全数据脚本语法检查通过，v26/v27合同回归44项通过。client每端8 semaphore槽，pipeline worker24。输出目录 `outputs/impact_qa/component_v27_video_gt_r7p2_all_splits/`，保存冻结配置、全量manifest、逐clip原子结果、输入媒体映射、API请求缓存和汇总JSONL；最终 `progress.json` 为 `full_finished`。
- 四轮可恢复执行累计记录2,290次模型请求，输入19,873,555 tokens、输出1,147,018 tokens。首轮末有5个生成合同失败及10个准备失败；修复短视频时序补帧、具体工具名筛选和最多3轮生成修复后，长clip的64帧上限仍暴露异常优先帧与均匀帧叠加超限问题。修正后751份媒体manifest全部≤64帧，32条ATR异常的专项clip端到端检查覆盖全部异常中心，无缺失证据。
- 对具体工具名已有约束的clip，移除GT事件中的泛称 `tool` 对逐字匹配的冗余要求；4个开放QA合同失败在后续修复轮成功。32个事件同时进行MCQ视觉核验会超过结构化输出token上限，现每8个事件分批、每事件最多2个证据帧与20词描述；最终批次成功完成。
- 最终覆盖751/751个clip：728 completed、23 held、0 pending、0 preparation error。生成2,394条开放QA：overall 728、detailed 248、completion 929、order 71、duration 418；Qwen逐题视频+GT自动复核为2,348 keep、46 major hold。所有QA仍为 `human_review=unreviewed`；这46条保留在审核页并标记held，不计入可接受输出。
- 固定GT-MCQ候选141条；6个clip被题型选择器选中，合计38个ATR异常事件进入盲视觉核验，均无足够直接视觉证据，因此0条MCQ公开导出。保留相应选择排除记录和视觉核验结果，不能将141候选数报告为生成MCQ数。
- 最终完整性核查：manifest与结果各751条且clip ID一一对应；2394条QA、2394条review、751份媒体manifest；所有GT来源与帧证据引用均通过结构检查，所有帧数≤64。人工抽查过4个试点clip/18题，并针对32异常clip查看64帧联系表；这不是751个源视频的逐帧人工审核。全局 `human_review=pending`、`formal_release=false`。
- 8000/8001/8002三项模型接口及7863页面均HTTP健康；7863全量clip下拉项751个。审核地址 `http://10.112.70.171:7863`。主要查看文件：`progress.json`、`questions.jsonl`、`reviews.jsonl`、`fixed_mcq.jsonl`、`results/*_V.json`、`runs/*.json`；人工审核完成前不发布为正式数据。

### 开放式 QA 数量偏少原因审计

- 复算 `questions.jsonl`：751个clip共2,394条开放QA，均值3.19/clip，中位数3；23个clip为0题。逐clip题数分布：0题23、1题111、2题62、3题252、4题182、5题76、6题20、7题25。自动复核保留2,348条（3.13/全部clip），46条hold不计入保留数；人工审核仍未完成。
- 候选到导出：2,826个开放候选（overall751、detailed614、completion972、order71、duration418），模型最终选中并生成2,394条。候选排除432条，其中detailed_operation 366（占排除数84.7%，占该题型候选59.6%）、step_completion43、overall_operation23；observed_order与operation_duration候选全部通过。数量下降来自适用性/视觉支持筛选，不是 API 或服务失败。
- 主要逻辑错配：`v27_questions.py` 在 `action_count >= 2` 时构造详细操作候选，但题目主题/prompt要求按多个 operation phases 概述。614个详细候选中443个只有一个高层阶段；其中360个被筛掉，理由通常是单阶段不支持“multi-phase”摘要；另有5个双阶段候选被筛、1个9阶段候选超过8阶段预算。模型保留的248条详细题中，125条来自双阶段，35条三阶段，另有单阶段83条。原子动作数与高层阶段数的资格标准不一致，是平均数偏低的主要可修复原因。
- 题型本身的 GT 资格也有限：顺序题只有71个候选（需同clip内两个不同、完整且不重叠的组件操作）；时长题418个候选（单个明确操作episode至少5秒）；完成性题972个候选分布在542个clip（需同视角组件状态发生变化）。不满足GT条件时不会补题。
- 异常MCQ单独统计，不属于开放QA均值：141个GT候选中6个进入视觉异常核验，38段ATR区间均未达到直接视觉证据标准，最终导出0条。另有23个clip的overall候选因clip太短或动作证据不足而未选；完成性43条未选主要是末帧与GT冲突或证据/题意重复。
- 下轮只建议调整详细操作题：允许一个高层操作阶段内、至少两个有意义的工具-部件动作生成简洁过程题，并在prompt中明确不要求跨多个阶段；保留GT与视觉证据门槛，先做分层pilot，不为提高均值放宽顺序/时长条件。

### r7p2 incremental r1 supplemental detailed QA（2026-09-24）

- 未修改 `component_v27_video_gt_r7p2_all_splits` 原始目录。新配置、prompt、候选、逐候选结果和合并文件均保存于 `outputs/impact_qa/component_v27_video_gt_r7p2_incremental_r1/`；每个增量候选最多为每个clip追加1条，并保留 `source_candidate_id` 与父输出目录。
- 从原始未选详细候选中筛出360个单阶段候选：每个候选只有一个高层操作阶段，但该阶段至少有2个有意义工具/部件动作；不放宽视觉证据门槛。24个clip试跑得到23条QA且23/23自动keep；随后完成全部360个候选。
- 全部增量结果：360/360候选有终态；34个被视频+GT选择器判定为视觉支持不足而跳过；326条补充QA，其中315条自动keep、11条自动hold；0条最终错误。4条最初因缺少 `bearing plate assembly` 全称被合同拦截，增加精确名称重试后补齐，其中1条经过一次repair成功，其余3条在首次repair成功。
- 合并结果 `merged_questions.jsonl` 共2720条（父版本2394＋增量326），无重复question_id，父版本与增量ID无交集；合并自动保留2663条、自动hold57条，751个clip平均3.62条QA。开放题题型分布变为overall728、detailed574、completion929、order71、duration418；新增题全部为 `detailed_operation`。`merged_reviews.jsonl` 与合并问答一一对应。
- 质量检查：增量每条均通过结构化GT词项、证据帧、问题格式和Qwen自动复核；pilot人工文本抽查23条，未发现逐帧手部动作罗列问题。所有增量题仍为 `human_review=unreviewed`，正式发布关闭；11条hold不得视为人工通过。
- 7863服务已重启为父版本＋增量合并展示，端口健康返回HTTP 200；审核页面仍使用单端口 `http://10.112.70.171:7863`。

### clip时长分布盘点（2026-09-24）

- `clips.jsonl`中边界生成的全部765个clip：均值38.00秒、中位数23.87秒、最短0.033秒、最长702.8秒；实际纳入全量manifest的751个clip：均值38.69秒、中位数24.73秒、最短0.033秒、最长702.8秒。
- 751个已纳入clip的时长分箱：0–1.5秒89、1.5–3秒11、3–5秒4、5–10秒47、10–20秒173、20–30秒99、30–60秒217、至少60秒111。也就是说，短于3秒有100个（13.3%），短于1.5秒有89个（11.9%），短于5秒有104个（13.8%）。
- 这100个短于3秒的manifest clip全部是assemble，没有disassemble；79个由 `asr_completion_plus_2s` 边界产生，21个由 `source_video_end` 产生。最短片段约一帧，属于边界尾片段，通常不足以支持可靠的操作理解。
- 合并QA中，短于3秒的100个clip里有77个各产生1条QA、23个没有QA；因此当前流程虽有视觉选择保护，但没有把clip时长本身作为硬过滤条件。若用于正式训练/评测，建议新增 `clip_duration >= 3s` 门槛，或将同一组件的边界尾片段合并后再出题；保留原始clip作为审计数据，不直接作为高质量QA样本。

### 2026-09-24 v28短clip切分修复与冒烟

环境预检：`.venv-impact`、torch 2.10.0+cu129、CUDA 12.9、CUDA available=True、7张RTX 4090；8000/8001/8002均返回Qwen3.8-27B模型标识。未修改父目录 `component_v27_video_gt_r7p2_all_splits`。

实现文件：`impact_qa/clip_repair.py`；配置 `configs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix3.json`；索引入口 `scripts/run_component_v27_r7p2_all_splits_clipfix3.py`；审计入口 `scripts/audit_clip_splits.py`。原始边界先写入 `raw_clips.jsonl`，修复映射写入 `clip_repair_map.jsonl`，输出片段使用 `v28_` 前缀。

结果：原始765个clip（assemble363、disassemble402）中113个短于3秒，最短0.033秒；修复后652个clip（assemble250、disassemble402），有效TAS-B manifest 651个。113个短片全部并入相邻区间，97个最终片段带合并标记；没有拆卸窗口扩展，也没有因无法达到3秒而丢弃。修复后全量最短4.467秒、均值44.589秒、中位数30.400秒；manifest最短4.467秒、均值44.646秒、中位数30.400秒。112/112装配分区通过首尾和相邻连续性检查，修复后没有低于3秒片段。

标注覆盖对照：有效TAS-B动作完全包含数从9984/12163增至10037/12163；ATR raw error完全包含数从1391/1674增至1397/1674，未增加未重叠错误。新增 `clip_split_audit.json`/`.md` 保存原始与修复时长箱、覆盖和结构断言。

模型冒烟：新切分前4个clip使用完整视频＋GT流程，4/4 clip completed、0 preparation error，生成22条开放候选（overall4、detailed3、step_completion7、observed_order2、operation_duration6）；13次请求中12次成功，1次因缺少精确部件名触发合同修复，修复后成功，4次自动review均成功。总prompt 131,756、completion 11,291 tokens，请求累计489.70秒。所有样本仍 `human_review=unreviewed`、`formal_release=false`；这只是切分和流程冒烟，不是人工质量通过。

失败归因：一次首轮生成遗漏 `screw adaptor topleft`，说明合并后的较长装配区间仍可能增加完成性答案的名词覆盖压力；合同修复有效解决，但全量前仍应抽查合并区间的题目数量、答案长度和跨组件语义。长片段（修复manifest中111个至少60秒，最长706.97秒）未按固定时长拆分，下一轮应依据新的组件/动作边界单独设计长片切分，不能用固定时长切出短尾片段。

阈值敏感性：相同规则下最小5秒会得到647个manifest clip，最短5.1秒；相较3秒版本只再合并4个片段。这4个当前保留的3–5秒片段均有明确TAS-B收尾动作（安装后放置/存放/放回工具或部件），不是无动作的单帧尾部，因此本轮采用3秒作为去除病态短片段的门槛，5秒作为可选的更严格训练筛选门槛。

全量启动前清理：删除已被新版替代且不被当前runner/7863引用的 `component_v27_video_gt_r1`、r2、r3、r4、r5、r6、r7、r7p1、r7p2、r7p2_train_full，共约161 MB；保留旧 all-splits 父目录（7863当前依赖）、incremental r1 和新版 clipfix3。删除清单及大小记录在 `outputs/impact_qa/cleanup_v27_superseded_20260924.json`，所有脚本、配置和研究记录保留。

### 2026-09-24 v28 clipfix3 全量模型生成

- 配置：`configs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix3.json`；模型 `impact-qwen38-27b`；8000/8001 为 GPU0–3 上的两个 TP2 服务，8002 为 GPU4–5 上的 TP2 服务；每服务 `max_num_seqs=8`，客户端队列24 workers，完整 clip最多64帧、4 fps、768宽、32768上下文。运行前 CUDA、7张RTX 4090、三个模型接口预检通过。
- 范围：112个 front 视频，原始765 → 修复652 → 含有效TAS-B动作的manifest651；修复后manifest最短4.467s。所有651个clip都有 `result` 终态，`progress.state=full_finished`、`pending_clip_count=0`、`preparation_error_count=0`。
- 生成结果：`questions.jsonl` 共2312条开放式QA，overall651、step_completion923、operation_duration417、detailed_operation250、observed_order71；自动复核candidate2285、held27。固定ATR≥5秒候选141条；4条进入视觉检查但区间内均未确认具体异常行为，故导出MCQ为0，避免从不可见异常标签直接生成视觉题。
- 请求与重试：全量run记录1962次尝试，其中1924次 `ok`、38次合同校验失败后重试；失败集中在生成阶段缺少精确GT部件/工具短语或整体操作词，最终全部由修复重试或其他有效结果收敛，未留下准备错误。全量run累计约18,023,804 prompt tokens、1,052,437 completion tokens；API错误不是服务崩溃，而是生成合同触发的可恢复重试。此前4 clip smoke的13次请求另存于同目录旧run记录。
- 完整性审计：新增 [`audit_component_v27_full.py`](scripts/audit_component_v27_full.py)；`full_run_audit.json/.md` 报告重复题目0、未知clip0、未知证据帧0、媒体断链0、合同问题0。3个因清理旧r1而断链的媒体缓存已从源视频重新物化到新版 `media/` 并更新 `inputs/`/`media_manifests/`。
- 审核页：7863进程已重启，环境变量指向新版 clipfix3且禁用旧增量目录；本机HTTP 200，Gradio choices核实651个clip，状态显示651/651、2285 candidate/27 held。页面仍只提供人工审核候选，所有题的 `human_review` 为 `unreviewed`，`formal_release=false`。
- 质量状态与失败归因：27条hold中22条为step_completion、4条detailed_operation、1条overall_operation，主要原因是模型答案与片内最终状态/操作阶段冲突；这批题没有被删除，供人工复核。模型自动keep不被计为人工准确率，正式数据发布仍关闭。
- 回归测试：清理旧试点目录后，历史测试默认的12-clip r7p2 manifest会缺失；没有恢复旧QA/模型缓存，而是用保留的 `scripts/run_component_v27_r7p2.py --prepare-only` 重建 `outputs/impact_qa/component_v27_video_gt_r7p2` 测试夹具。`tests` 116项全部通过；7863仍读取新版 clipfix3目录。

### 2026-09-25 v28 clipfix4 尾巴过滤

- 人工审核指出 `KJ03JM25_Reassembly_A_003_front` 的4.467秒尾片段和 `KJ03JM25_Reassembly_A_002_front` 的4.933秒尾片段只是视频末尾收尾，缺少有意义的安装动作。离线核对确认两者均为 `source_video_end`，没有有效 ATR 异常、没有 TAS-B 高层组件 episode，只有 recovery/存放/放置/转移等动作。
- 新规则仅过滤同时满足以下条件的尾巴：`source_video_end`、无有效异常、无组件操作 episode、且没有核心安装/拆卸动作（insert/mount/attach/tighten/remove/detach 等）。因此含真实操作或有效异常的短片不受影响。规则实现为 `source_end_cleanup_tail_reason`，排除记录写入 `tail_excluded.jsonl`。
- 新版 `component_v27_video_gt_r7p2_all_splits_clipfix4` manifest 为648个 clip，排除3个尾巴：上述两个 KJ03片段，以及同规则识别出的 `KI03AR28_Reassembly_B_005_front` 5.167秒工具收纳尾巴。其余片段复用 clipfix3 已完成的模型结果，未产生新的API请求。
- 新版QA为2309条（overall648、step_completion923、operation_duration417、detailed_operation250、observed_order71），2282 candidate、27 held；完整性审计硬问题0、媒体断链0、证据帧错误0，最短剩余manifest clip 4.80秒。`clip_split_audit` 与 `full_run_audit` 均已重写。
- 7863已切换到 clipfix4，HTTP 200，下拉列表648项；被过滤的两个KJ片段后缀 `68eefae1`、`a8e39d5a` 已不再出现。117项回归测试通过。
## 2026-09-25：IMPACT 对象知识块与 A/B 配置核验

硬件/环境预检：`.venv-impact` Python 3.12.14；torch 2.10.0+cu129；CUDA 可用，7 张设备可见；FFmpeg 9.0.1。此任务只做离线资料构建和视频帧抽取，没有启动 VLLM、没有训练、没有批量重生成。

来源与产物：官方固定 commit `4fed5faa5f05f7aece55712e458defa1f372b248` 的 `2anglegrinderconfig.svg`（Git blob SHA1 `0a56f418588b92fadb923bf0b5d1bd0877ca4205`）、本地 `Manual_Book.svg`、论文 `papers/IMPACT.txt`、PSR component names、112 份 front TAS-B、92 份 ASR；从 8 个 GT 定位点取 front/top 帧，并另取 A 型缺 ASR 文件首帧，共34帧。`scripts/extract_impact_object_evidence.py` 保留视频路径、时间戳、TAS-B pointer、关系和图片 SHA256。

离线指标：覆盖 19 个 TAS-B 名词、17 个规范 ASR 实例、4 个旧 ASR 标签，词表缺失 0。ASR 原始 `state_changes` 11121 行；按 `impact_qa.v26_data.changes` 比较相邻 `state_sequence` 后为 3231 个组件变化、1355 个变化帧。A/B 文件名计数为 A=93/B=19，论文为 A=92/B=20；缺 ASR 的 A 文件是 `KE03ER16_Disassembly_A_001_front`，作为未解决差异保留。TAS-B 工具 pick_up 统计：A 一字4/十字158/Torx249/扳手112，B 一字34/十字54/Torx4/扳手21；这些是分布，不是正确性标签。

质量与限制：`scripts/build_impact_object_knowledge.py` 生成完整、A、B 三个 prompt，结构化 JSON、中文报告和 source/audit manifest；Python 编译、JSON 解析、SHA 校验、证据 GT pointer 验证均通过。报告明确工具颜色只作视觉线索，M4_nut_plate 是位置化 M4 螺母，B 不继承 A 的状态图；保留 TAS-B M4/M6 冲突和 B 拨杆标签冲突。知识块没有接入现有 QA runner，未报告 VLM 质量提升；下一实验应使用同一分层 clip 做无知识块/适用 A/B 知识块对照。

### 2026-09-26 7863审核服务恢复与全量题量复核

- 使用 `.venv-review`（Gradio 6.28.0）恢复 `scripts/serve_component_v27_review.py`，PID 221993，监听0.0.0.0:7863；配置指向clipfix4并禁用旧版增量合并。初次预检发现 `.venv-impact` 不含Gradio，改用既有审核环境后启动成功，未安装新依赖。
- 本机与网卡地址 HTTP 200，Gradio下拉648个clip；调用load_v27_clip实际返回QA和视频，视频Range请求206。访问地址 http://10.112.70.171:7863。
- 直接逐行统计新版全量112个源视频、648个clip、2309道开放式QA：整体648（keep647/hold1），详细过程250（246/4），完成性923（901/22，其中Yes496/No427），顺序71（71/0），时长417（417/0）；共2282自动keep、27hold，全部仍为human_review=unreviewed，待处理clip为0。
- MCQ有141道固定GT候选，正式问题JSONL导出0；4道进入独立视觉复核后均以blind_visual_check_did_not_support_abnormal_operation排除。候选正确选项按多标签计数：Correct0、Temporal99、Spatial52、Handling59、Wrong part12、Wrong tool10、Procedural39，不能将标签频次相加当题量。
- 快照保存在 `outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix4/qa_counts_20260926.json`；旧切分版本和增量未重复计数。本次无新增模型请求，也未改动生成结果。

### 2026-09-26 clip-level MCQ候选与ATR异常长度审计

- 审计范围为当前 clipfix4 全量 manifest：112 个源视频、648 个 clip。原始 ATR 异常标注 1674 条，其中按 `minimum_error_seconds=1.5` 过滤后保留 1052 条，622 条短于 1.5s 被排除。
- 当前 MCQ 规则是：异常区间必须完整包含在 clip 内，且单段时长至少 5s；满足条件的 141 个 clip 各生成 1 个固定 GT 候选。当前 `questions.jsonl` 正式导出的 MCQ 为 0：4 个候选进入独立视觉核验，4 个均未得到区间内可确认的异常视觉证据。当前代码不会为其余 clip自动生成 Correct MCQ。
- 648 个 clip 分类：完整有效异常且至少 5s 为 141；完整有效异常但仅 1.5–<5s 为 179；有效异常跨 clip 边界、未完整包含为 75；只有 <1.5s 原始异常相交为 123；无原始异常相交为 130。故不能把剩余 507 个 clip 全部标成 Correct。
- 原始 ATR 时长分布（秒）：<1.5 为 622，1.5–<3 为 346，3–<5 为 276，5–<10 为 247，10–<20 为 120，20–<30 为 29，30–<60 为 26，>=60 为 8。过滤后有效标注总数 1052，最短 1.5s，中位数 4.133s，均值 7.340s，最长 193.633s。
- 141 个候选中的多异常处理：86 个含 1 段，55 个含多段；分布为 2 段27、3段5、4段9、5段3、6段1、7段3、9段1、11段2、12段1、15段2、32段1。所有段保存在 `qualifying_errors`，异常类型取标签并集；VLM逐段核验，最终题目（若通过）在 `abnormal_segments` 中逐段记录时间、类型和证据帧，没有通过视觉核验则整题丢弃。23 个多异常候选的区间彼此有重叠。
- 拆分 clip 使用独立组件窗口并带上下文重叠：相邻重叠 195 对、涉及 56 个视频；完整有效异常在 clip 中出现 922 次但对应 839 个唯一 event_id，>=5s异常出现 338 次但对应 322 个唯一 event_id。详细机器可读报告：`outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix4/anomaly_length_distribution_20260926.json`。

### 2026-09-26 多异常段 MCQ 分组方案离线模拟

- 141 个固定 MCQ 候选 clip 的时长为 14.067–706.967s，中位数 59.8s、均值 94.021s；338 次合格异常出现对应 322 个唯一 ATR event_id。异常段两两关系为：50 对时间重叠、4 对间隔 0–0.5s、13 对间隔 0.5–1s、1055 对间隔超过1s。
- 采用“时间重叠或间隔不超过0.5s合成 episode、保留原始 event_id 子段”的离线模拟。原候选的 episode 数分布为：1段90、2段27、3段8、4段7、5段2、6段1、7段1、8段1、9段1、11段2、26段1；0.5s阈值只比纯重叠规则额外合并4个近邻段。
- 对拆分窗口重复出现的 event_id 先选 focused canonical clip（异常时长/clip时长比例更高且 clip 更短）。141个候选变为135个canonical parent clip，其中126个含1–4个episode，9个含超过4个episode；后9个均为长clip。按“普通parent clip一题、长clip每episode一个局部evidence window题”估算，视觉筛选前约212个MCQ单元（126+86），不代表最终导出数量。
- 推荐的多异常题目策略：1–4个episode保留一条clip-level MCQ，选项类型取episode标签并集，`abnormal_segments`逐段保存时间和证据；超过4个episode不在一条自然语言答案中枚举全部区间，改用局部窗口的episode-level MCQ。每个episode独立盲视觉核验，不能用GT标签或一个模糊帧替代直接证据。当前clipfix4生成结果未修改，模拟状态为 `simulation_only_current_outputs_unchanged`。
- 完整性约束补充：clip-level题若声称“选择所有异常类型”，必须覆盖所有合格episode；只确认部分episode时不能把可见子集作为完整clip答案，只能降级为带 `parent_clip_id` 的 episode-level题或保持hold。
- 模拟报告：`outputs/impact_qa/component_v27_video_gt_r7p2_all_splits_clipfix4/mcq_anomaly_grouping_simulation_20260926.json`。下一步需独立版本实现并先做小规模人工审核，不直接覆盖当前结果。

### 2026-09-26 grouped_v1 实施及第一轮

环境：`.venv-impact` torch 2.10.0+cu129、CUDA可用、7卡可见、vLLM0.18.0；GPU4/5各49140MiB，TP2服务8002，使用约42943MiB/卡；max_model_len32768、max_num_seqs8，客户端并发4。模型目录Qwen3.8_27B的索引涉及18个shard且均存在；仅检查存在性，没有宣称下载哈希完整验证。vLLM实际识别架构Qwen3_5ForConditionalGeneration，模型名为既有本地别名impact-qwen38-27b。前一次nohup启动未留下存活进程，本次subprocess start_new_session启动成功。

离线：648个clip→141个候选clip→135个canonical parent→212个单元（126 parent、86 episode），覆盖322个唯一ATR事件，无重复/丢失/时钟/标签并集错误。进一步范围检查发现208个单元须限定手和时间段，4个可用整clip措辞。新增9项合同测试全部通过。2fps、最多30秒观察窗口、上下文3秒，逐源帧标签及时间映射，媒体SHA256及服务端采样帧映射核验。

R1：12个异常单元（14个事件）+4个正常窗口，32个API请求；16/16完成，运行失败0；严格视觉类型核验通过0/14，MCQ自动保留0/12；正常负对照被观察器误判为异常0/4。机械审计硬错误0。抽查contact sheet确认front视角的零件/螺丝细节很小，动作本身不一定外显为异常。GT Wrong tool的真实例子对应TAS-B hand_loosen_screw：看见徒手松螺丝不等于能独立证明应当使用哪种工具，故uncertain合理，不能为了题量编造正确工具。

故障归因与R2设计：盲观察缺少正常工具/部件参照，且把“未独立识别异常”设为永久否决会将GT出题混同重新标注。R2保留盲事实观察、补充已有A/B领域知识和精确TAS-B上下文；仅当事实一致且具体类型判据有依据时通过，不因标签存在而接受。增加正常片段注入B/D假标签的审计负对照，检查GT诱导型幻觉；假标签仅用于对照，绝不导出为数据题。

GT语义审计：322个唯一事件中149个多标签、70个由多个源动作段合并、110个无非null动作名；ATR与同手相交TAS-B标签并集不一致0。43个事件的各类别并非持续覆盖整个ATR区间，因此后续需按TAS-B保留逐类型子区间，防止给C类引用实际只标B类的帧。报告 `mcq_grouped_v1/gt_semantics_audit.json`。

### grouped_v1 R2–R4 与独立结果审计

- R2（同12异常单元+4正常窗口）：补A/B知识及动作上下文、区分事实观察与异常判定；36请求，16/16完成，完整视觉类型支持仍0/14事件。正常窗口故意注入Temporal/Handling候选标签时，审核器误接收0/4。该假标签只用于检查锚定偏差，未导出为题目。
- R3（同样本）：4fps、20s观察窗、最多80帧、768宽；操作区裁剪为原图归一化[0.2,0.3,0.8,0.95]并保留原图嵌窗，逐类型TAS-B区间映射。38请求，16/16完成；7个GT动作支撑候选，完整视觉类型支持0。该7个只是action-grounded，不等于异常原因确认。
- 发现并纠正自评过度乐观：同一例手工松螺丝被盲观察写成用改锥，带GT审核写成未用工具，却自评supports_facts；左右手稳定/旋转的归属也出现布尔字段与理由冲突。增加独立事实critic，先看有上下文局部视频，后看仅目标异常区间并强制报告performing_hand。R3共14次critic请求；不同范围下接受数2和3，不把二者当独立标注员一致性或真人通过率。
- R4（新增8异常单元、10事件；正常对照改为4个不同参与者）：26请求，12/12完成、0运行失败；4个动作支撑候选、0完整视觉类型确认；盲观察与假标签注入误接收均0/4。6次exact critic请求后3个模型候选仍需独立检查。20个异常单元非独立视频holdout，名字r4_holdout仅指未参与前3轮的单元，不代表正式测试集。
- 直接查看R3/R4的chronological contact sheets，逐项审计全部11个动作支撑候选，检查问题、答案、左右手、工具使用、区间和具体类别时间。该审查者是Codex，不是人类；`independent_frame_audit.json`明确标记human_review=unreviewed。
- 新问题：513个event-label组合中24个类型支撑<1.5s，40个<5s；涉及20个候选单元。例：`mq_d98511091c22135d`的Temporal仅16帧=0.533s；`mq_c105936e99e64dc1`的Spatial仅15帧=0.5s，Wrong tool为214帧=7.133s。采用保留原GT并hold整题的保守修复，不把短类型静默删除后冒充完整答案。
- 最终：20个不同异常单元/24个事件、7个不同正常窗口；152个成功API记录（观察68、带GT审核64、事实critic20），运行错误0。14项合同测试和语法检查通过；离线候选仍212、唯一事件322，硬错误0。正式视觉确认MCQ为0；仅1个GT依据明确且动作可见的示例进入`review_examples.jsonl`（Temporal类别仍未独立视觉确认），其余10个候选在`final_held_audit.jsonl`逐项说明。之前2309开放QA和clipfix4输出均保留。
- 决策：未达到“可批量自动生成可信异常视觉理由”的质量门槛，没有扩大到全部212个单元。GT标签不是待模型改写的答案，但GT存在也不等于原因可见；缺失参照、手/工具归属不稳时应保留待审。最终入口默认最新prompt，旧round配置/代码变更须使用新round名；API成功缓存、媒体SHA和源帧映射可复用。`final_pilot_summary.json`和`final_report.md`保存结果。


### 2026-09-26 grouped_v2 native_r1：各视角原生标注与稳定区间

环境沿用TP2 GPU4/5的8002服务，7卡CUDA可见；torch2.10.0+cu129，客户端并发4，max_model_len32768，temperature0，seed20260926。这里实际运行CUDA12.9，不声称兼容<=12.1。视频均来自已下载原始MP4，采样4fps、宽960，最大20s；front操作区放大并保留全图，top/ego首轮完整画面。帧映射/CFR及服务端解码索引有硬校验。

6个历史失败异常操作族 +2个正常对照操作族，原生动作/时间匹配后20个视角样例（front8/top8/ego4），其中15个异常、5个Correct；3个异常不足5s，仅作诊断。3个ego匹配被拒绝，未强制搬用front GT。40/40 API请求成功，20/20结果完成，结构审计硬错误0，GT答案和来源/帧时钟校验通过。自动动作支撑11/20，严格类型原因解释0；11不是准确率，也不是发布量。

全量648父clip中的唯一稳定异常区间1520，其中<1.5s653、1.5–<5s542、>=5s325；>=5s且有非null动作211。统计单位已由ATR记录改为标签稳定区间，不能直接与旧322 ATR事件相减比较。暂不全量执行模型审核。

Codex直接查看多个front/top/ego帧图发现：SS右手持有工具但尖端多次指向远离工件方向，模型却写用工具尖端拧；NA左手稳定壳体却被ground阶段认可成转轴。这是语义核验失败，不能靠高置信度放行。R2保留原始R1及代码快照，扩大手部/接触区，增加尖端关系字段、针对性few-shot和有限语义矛盾拦截；不改GT答案。


### grouped_v2 native_r2/r3 与本轮收尾

R2同20视角样例40请求完成，自动动作支撑12，原因确认0；R3仅top8样例16请求完成，自动动作支撑3，原因确认0。全部96请求成功；三轮实际输入10–44帧、4fps（源帧时间另存），采样后容器可能有微小尾长差异，题目时间始终使用原生GT帧号/fps。宽960、像素预算8388608、temperature0、TP2并发4。详实token和帧范围见review_export/final_audit.json。

R2错误归因：固定top裁剪框漏掉画面上方操作区；few-shot在LE ego诱导出不存在改锥；部分字段称held_without_use但文字说工具在桌上。R3拓宽top画面并将全景置于主图旁，保留8例全量对照，不按通过状态挑选轮次。Codex检查20个最新样例帧图，保留11个GT+事实候选（异常7/Correct4），9个hold；无一达到完整异常原因确认，正式发布0。该数字不是准确率；真人审核未进行。

前端沿用7863，添加MCQ测试页，提供原始帧率片段和实际模型输入；20条逐例审核记录单独保存。原开放QA 2309条未重新生成或修改。源码句法检查及22项相关回归测试通过。当前不启动全量异常解释生成，先补具体GT工具适配与状态前置条件。

7863最终切换到mcq_grouped_v2/review_export并已实测：本机及10.112.70.171均HTTP200；下拉开放QA648项、MCQ20项；ego及top两个MCQ API返回原片和采样视频，4次Range请求均206/1024字节，Codex备注可见；旧开放QA视频接口正常。最终目录包含11个gt_candidates和9个held，全20项可审阅；所有原始迭代输出未覆盖。

### 2026-09-27 六类异常语义与判据专项审计

本轮CPU JSON分析与PyAV源视频抽帧，无模型推理/训练、无新增QA、GPU显存分配和模型超参数不适用。预检：560份TAS-B输入存在、六例JSON及视频可读、PyAV/Pillow/numpy可用；三份脚本py_compile通过。代码复用impact_qa.common读写和路径。输出仅新建anomaly_taxonomy_audit目录及参考prompt，既有2309开放QA和20个MCQ审阅样例保持原状。

来源：官方commit 4fed5faa5f05f7aece55712e458defa1f372b248，GitHub完整树、论文HTML与TeX源码、ATR说明/映射/实现、PSR图与挖掘程序、图示、发布清单和issue；49个下载源文件SHA已保存。web工具返回404，改用HTTP直接读取官方来源；HF直连超时后使用镜像，未把网络失败当作资料不存在。TeX有未启用旧稿块，统计和引用以正式正文及实际v1.1文件为准。

统计：560份TAS-B、67,492段；front112份、13,512段，1,944段含异常类型，其中391段多标签；ATR Split1双手三分区总7,797条。front类别段数Temporal939/Spatial689/Handling332/Wrong part44/Wrong tool77/Procedural311；多标签重复计数。无类别顺序不一致。没有逐段原因字段。所有非null异常动作名都有normal同名样本，保存30组对照。

六例上下文视频按等间隔每例12帧，共72帧，窗口10–31秒，保留源帧与PTS、原图和contact sheet。Codex直接查看全部六张图，人工审核状态unreviewed。独立case_dossiers保留15个目标原子段、目标手相邻动作、另一只手动作、ASR状态差分、原文件SHA与pointer。来源存在性、类别计数、正常对照断言通过，脚本正常退出。工具类例子3.067秒，明确只作诊断，不混入≥5秒优先生产集合。

结果：Wrong tool例可用GT+采样图说明十字改锥→收回→一字改锥→正常松螺丝的局部纠正过程；其余五例具体原因未确认。这是六个定向案例的证据结论，不是类别识别准确率。根因：公开六类只有名称与标签，无操作rubric；旧prompt若用空握/徒手/滑脱等通用模式强行解释，可能过宽或过窄。官方procedure_graph为ASR统计挖掘，102条边的目标均recover_ok，不能当完整手工SOP。新reference prompt显式区分GT、事实、工作解释和未知，尚未做模型复测或生产接入。完整报告、字段/来源审计和JSONL已保存。

### 2026-09-28 下一轮判据研究覆盖分析

执行：.venv-impact/bin/python scripts/audit_impact_rule_discovery_coverage.py；CPU JSON处理、无GPU任务/模型请求/新媒体生成。preflight核验112个front标注存在；复用impact_qa.mcq_native.native_trial/stable_runs和common读写。脚本py_compile通过，类别原子段计数与昨日独立审计一致、稳定区间ID无重复。normal对照按文件型号线索/装拆/手/动作初筛，只标可用性，未宣称视觉等价或真实同部件。

1809个唯一稳定异常区间；含各类861/671/322/42/64/266，类别间重复。单类有动作区间Temporal280、Spatial322、Handling155、Wrong part9、Wrong tool26、Procedural115；其中≥5s为85/4/45/2/5/19。Spatial中265个<1.5s，说明用生产长段门槛做分类语义研究有覆盖偏差；这不证明这些短标注质量，未改变生产过滤。Wrong part全部42区间分布16次执行/10参与者，保留多标签，不强行拆成单类原因。

输出followup_coverage.json、rule_discovery_pool.jsonl、前10条预览与next_round_design.md。提出按参与者隔离规则发现/检验、normal和相近其他异常对照、源视频上下文/多视角核验、GT/事实/原因分层评价。上述为待执行设计，不是已完成视频审查或准确率结果。原有QA与review输出未改写。

### 2026-09-28 多视角视觉补查 anomaly_multiview_v2

执行环境：.venv-impact，torch2.10.0+cu129、CUDA runtime12.9、torch.cuda.is_available=True、7张可见GPU；nvidia-smi报告各卡RTX4090、49140MiB。PyAV18.1.0、Pillow12.3.0。现有4/5卡服务显存约41715/43211MiB，本轮只CPU解码/JSON审计，未调用该服务或新分配模型显存；未测试CUDA<=12.1兼容性。temperature/token budget/分类accuracy不适用。

样本：7次执行/5参与者、12组目标、front/top/ego共36窗口，6个既有front疑点+6个新增front目标。前3s后6s上下文，每窗4帧前文+12帧目标+4帧后文；3个无唯一同名ego动作对应的窗口仅作近似观察。原生fps front/top30、ego24.917；按实际流rate及PTS解码，未将ego套30fps。候选选择及前10条输入已冻结。

视觉审核：Codex直接检查36张序列图，720条帧记录/714唯一源帧；另10张细节图复用60帧；SS07EL13_Disassembly_B_005正常store_screw的ego94.434–95.316s全部22源帧补查，4张密集图，新增10唯一帧，总计724唯一源帧。不是人类专家审核，不是所有视频逐帧检查，不是新的独立留出评估。本轮API请求0、新正式QA0、新确认官方通用判据0。

结果：normal持改锥进入Box 4经三视角支持；另有不拿改锥、直接将紧固件放桌面的Spatial实例。带盘轴与分离后轴的同名存放不符合等状态对照。SS例支持Box 2→Box 3手部转移，但密集帧仍遮挡螺丝，未升级为已证实的同物体纠正。3组局部对应存在标签差异、3组动作差异，交集部分重叠；ER长store_screw在top多Handling，两个front/top normal候选在ego没有相同正常标注。不能据定向样本估计全数据错误率。

失败归因与修正：初始同手normal筛选在LE06执行为空，预检抛出空集合错误；改为明确标记另一只手的存放参考，不伪装成严格对照。一次在预检失败后尝试的renderer因无冻结cases而退出，未生成错误样本；后续冻结成功才生成。检查图标题时发现近似窗口也被写为native target，现已改成approximate review window并保留header_revision记录，源帧和GT未动。连续帧不能解决手指遮挡，这是可见性限制而非采样不足；保留unknown。

验证：21原生GT文件SHA及302个上下文原子段的pointer/内容一致；36窗口范围、视角/手、目标段筛选、引用帧/作用域及PTS审计通过，最大源PTS与标注时钟差5.684e-14s，不代表跨摄像头同步。六份新建/修改Python文件py_compile通过；普通抽帧与密集抽帧重跑命中缓存。脚本共用native_trial/common，新增source_frames工具供连续源帧提取。输出report.md、direct_review_notes.json、visual_reviews.jsonl、crossview_differences.json、audit.json、code_manifest.json。prompt v3为独立参考，未宣称已接入生产或已有质量提升。

### 2026-09-28 剩余五类判据逐类核验 remaining_rules_v1

执行：inspect_remaining_anomaly_rules.py按类顺序渲染；inspect_anomaly_rule_followups.py定向补查；audit_remaining_anomaly_rules.py来源、覆盖、帧钟和缓存审计。复用native_trial/stable_runs、map_interval、source_frames及evidence_audit，新增review_frames公共渲染器。案例/前10条/选择fingerprint冻结，原GT与生产QA未覆盖。环境torch2.10.0+cu129、CUDA12.9可用7GPU、PyAV18.1.0/Pillow12.3.0；nvidia-smi报告RTX4090各49140MiB，4/5卡占用约41715/43211MiB。本轮CPU解码3workers、每流2decode threads，模型请求0/新正式QA0；没有测试CUDA<=12.1。模型温度、token budget、分类accuracy不适用。

样本：原26异常+5normal候选，追加2个短Handling诊断目标，共33目标/23执行/13参与者。Wrong tool5、Wrong part8、Handling8、Procedural6、Temporal6（包括normal）。62基础窗口+10补查窗口，直接查看72张序列图，1519帧条目/1512唯一源帧；3张局部连续帧放大图、12完整帧复用。短Handling top目标26/28连续帧全覆盖；其余为稀疏或加密采样，不宣称所有视频逐帧审核。GT可见，Codex非人类审核。

参数：基础前4/目标10/后4；>30秒目标16帧；Wrong part/Procedural前后15/18秒，其余6/12秒。补查6窗口目标24–32帧，前后2/3秒各4帧；2短目标各视角尽量目标全帧。源fps front/top30、ego24.917，以实际流PTS记录。约1.5秒过滤和≥5秒生产选样不是类别定义，研究短例不自动进入生产。

结果：3条Wrong tool局部链、2条Handling控制失误候选；Wrong part方向/身份/目标混淆及2条动作对象疑点（wp7/t4）；pr1返工事实更完整但前置因果未确认；Temporal长段实际仍有工作，未支持统一时长阈值。这些是定向案例结论，不能估计准确率/全量错误率。新prompt v5和rules.json是独立参考，未测试模型质量提升。

失败归因：首次h4 ego目标315–351秒超过141.47秒源视频，预检报media_or_interval并中止；复核媒体与原生标注后明确缺失视角，选择front回退并冻结原因。h6 ego同名匹配误选前次44.789–46.033秒正常取件，直接帧审否决对应，保留语境但不作漏标证明。密集帧仍可能遮挡内部接触，不能用模型信心填原因。

验证：68份源GT/1295唯一segment的SHA和原始字段/指针通过；72窗口范围/引用作用域/每视频PTS通过，最大时钟差5.684e-14秒，不代表跨摄像头同步。1591张基础/补查缓存图片复跑未改写。代码语法检查通过，代码SHA清单、首次10条输入/输出、逐例JSONL/报告完整。剩余缺口明确保留：Wrong part全池未完成，Procedural/Temporal规范边界及Handling允许落台条件未确认。

### 2026-09-28 front_rule_coverage_v1：全量代理规则与front诊断

执行架构：front_rule_metrics.py负责数据/条件/metrics；audit_front_rule_coverage.py做CUDA/PyAV预检、来源、冻结、前10条及渲染；summarize_front_rule_evidence.py做独立重算、四规则合并、时长敏感性、工具阶段实验、CSV和源证据审计。复用common/native_trial/evidence_audit/review_frames，31例与所有源帧断点缓存，原GT不修改。

环境：torch2.10.0+cu129、CUDA12.9 available=True，7张可见GPU；nvidia-smi报告RTX4090各49140MiB、driver610.43.02，4/5卡已有41715/43211MiB占用。本轮CPU统计/解码3workers、每流2threads，API请求0/新增正式QA0，无新增推理显存；CUDA<=12.1未测试。av18.1.0。抽样seed20260928、各层内尽量不同执行；31诊断窗口24执行，GT可见；前后6/8秒各4帧，目标≤12秒10帧、>12秒16帧，612唯一源帧。不是独立精度评估或人类专家审核。

全量112front/13512原子段，异常1944、异常类别标记2392；六类计数939/689/332/44/77/311，顺序T/S/H/WP/WT/P。43条件。四强条件触发352、正确类别264，GT类别precision75.0%/recall11.0368%；任意异常295/352=83.8068%，异常原子段recall15.1749%。hand_spin96/111，Spatial前loosen62/96，NULL≥8s90/123，重装dismount16/22。工具pickup25/636；阶段参考＋推断工具不匹配4/29。持件8秒27/436，另一手GT工作≤10%后15/49；推断持工具徒手H9/104、T8/104。真实accuracy未估计。

时长参数：NULL5/8/10/15/20/30秒；hold0/5/8/15秒；另一手WORK词集合覆盖≤10%；工具状态最近刷新≤60秒在段起点检查，事件内实际持有未验证。≥1.5/5秒原子段子集分别7898/2780，各分母重新计算。Spatial前loosen命中从62变4/0，说明短段排除对类别偏差巨大；该检查不等同生产稳定异常区间过滤。

失败归因与处理：初读TAS-S时使用TAS-B的action_labels键，改用实际segments/label；同名hold/NULL没有可靠进展语义，保留代理局限。选择器n=0仍进入循环会改变后续随机选择，修正后保留已冻结样本，不悄悄更换审核对象。工具持续时间描述原写≤60s过强，改成“段开始距刷新≤60s、持有未确认”。修订描述后首次汇总严格等值校验按预期拒绝旧metrics，重新运行原始统计后全部一致；数值与冻结rows/cases不变。在线web调用返回404，使用已保存官方论文/图示，不宣称新联网成功。没有据粗阶段匹配失败否定工具接口知识，也没有据GT正常认定视觉绝对正确。

验证：112TAS-B SHA/13512唯一原段、204TAS-S/ASR源SHA；43规则逐行命中与metrics重算；31review目标/源指针/帧引用与作用域；612源帧PTS最大误差0s（仅front时钟，非同步证明）；render缓存重跑全部未改写。三份新建/修改Python语法通过；audit.json保留代码SHA与硬件快照。输出report.md、metrics.csv、duration_sensitivity.json、four_rule_union.json、visual_reviews.jsonl、front_task_stage_rules_v1.txt及核心文档。真实语义规则性能需后续独立裁决，本轮不把候选prompt当生产已验证版本。

### 2026-09-28 front_mcq_expansion_v1：front异常候选扩展与协作审核

目标：按用户要求尽量保留可疑异常，暂不自动发布答案。输入112个front视频的全部1809个连续异常稳定区间，加7个已冻结的候选条件命中；不再用旧pilot的≤20秒上限或生产≥5秒门槛排除。得到1977个事件候选，501个同视频/邻近事件上下文组，覆盖112视频；GT事件1809，额外无GT异常标签规则候选168。候选类别计数：Temporal988、Spatial703、Handling405、Procedural271、Wrong tool64、Wrong part42（同一事件可多类）。目标事件时长<1.5秒781、1.5–5秒701、5–20秒429、20–60秒58、≥60秒8；最长133.5秒。播放组时长至少45秒，中位54.63秒，最长163.5秒，采用时长分层交错，不再短片优先。

架构：front_mcq_expansion.py冻结events/groups/options/questions；front_mcq_media.py保留源时间、目标加密采样、64帧上下文、每目标8–32帧和原始PTS；run_front_mcq_expansion.py使用两个Qwen服务8000/8002，per-service-concurrency8、workers16，缓存请求/视频/结果，失败可重跑；front_mcq_page.py和front_mcq_collaboration.py为7863协作审核。每题保留GT_option_ids、candidate_option_ids、model_supported_option_ids、visual_evidence、source_interval_s、playback_interval_s、human_review；formal_release=false。

硬件/服务：现有8002 Qwen3.8-27B，TP2、max-num-seqs8、bfloat16、max-model-len32768；新增8000同配置。torch2.10.0+cu129、CUDA12.9、7GPU可见；本轮统计与解码CPU，模型API并发。7863为0.0.0.0:7863，允许源视频和候选媒体路径。未改变旧QA。

冒烟：5组、15题、15个视觉解释成功；模型输出含facts/progress/checks，Temporal否定必须经过“visible state change/productive support”自动门控。结果中198 uncertain、35 conflict、9 supported、6 error、其余待生成；其中模型支持类型初始仅Temporal9，说明不能把GT候选自动变成人工答案。视频媒体解码回读96/96帧映射一致；6人并发claim/独立意见/冲突/stale revision/Correct互斥测试通过。一次模型证据帧越界被validator拒绝并保留error，归因是严格引用检查，不放宽约束；全量会自动重试。

输出：outputs/impact_qa/front_mcq_expansion_v1/{selection.json,events.jsonl,groups.jsonl,questions.jsonl,results,media,progress.json,collaborative_reviews.jsonl,claims.json,run.log}。这是候选审核集，不是发布集；API错误、证据不足、GT与视觉冲突必须人工处理。页面默认优先显示已有视觉依据，长短目标交错；每组下列出同clip所有MCQ，视频旁优先显示当前题目与GT/视觉依据，支持通过/不通过/证据不足并自动领取下一题。

收尾（front_mcq_expansion_v1）：501/501组成功，1977/1977题有视觉说明；模型支持至少一类39题（Temporal38、Handling1），反证264题、证据不足1674题。末轮3组目标帧引用错误改用逐事件/类别枚举的JSON schema重新看视频，全部成功；没有直接删掉越界引用冒充校验通过。源审计112份TAS-B/2112唯一动作、1809 GT事件全部ATR覆盖；53566帧条目/52795唯一源帧、每目标至少8帧、视频SHA/目标scope/PTS检查通过。模型实际输入70–232帧/组，pixel budget16777216；501媒体缓存可复用。

服务扩展：恢复8001于GPU2/3，已有进程约3GB占用保留；三服务各8并发、24workers、4CPU解码worker。切换前完成结果保留，取消的未结束请求不计入最终题目成功数。最终nvidia-smi报告0/1各41965MiB、2/3各45162MiB、4/5约42447/43943MiB（含原有其他进程），driver610.43.02。508个已保存API记录中504成功、4失败，含试点/重试，prompt8485291/completion508863；不等同508个有效视频组，也不包括未保存usage的取消请求。

抽查：两个初始语境序列图和3个定向目标序列图；发现fx_e2f671bebf79e9f3的“仅扶握”概括遗漏红黄工具附近实际操作、fx_9628d3839bf320ec遗漏料盒处理、fx_7361666b7565c7be的“红色适配板”身份说法不可靠。原输出保留，codex_checks.json与UI复查提醒标出；不能把39个模型支持当39个已确认真异常。

协作界面收尾：8人并发领取/写入不会丢失独立意见；同人修订保留历史，分歧聚合、跳过领取、版本变更拒绝、Correct互斥均在临时目录验证，未伪造真实人工记录。HTTP 7863内网地址200；真实视频/题目API、当前题目切换、长目标筛选、独立证据区测试通过。第一次直接调用空dropdown题目API被Gradio拒绝，按UI正常顺序先加载group再选question通过；不是题目数据损坏。浏览器二进制下载超时，未执行浏览器截图；CSS已在服务配置生效，未声称完成截图验收。期间审计读到生成中的旧导出快照，改为显式partial并在生成结束后重跑，最终status=complete、remaining=[]。最终产物约9GB，原GT/旧QA/现有人审记录不覆盖。

### 2026-09-28 修复已审核题目重复展示

用户反馈“通过下一题”后仍能看到已审题。真实追加记录核验：ldq于UTC14:04:30、14:05:13、14:05:39提交3次pass，前两次为fx_436cfe892cf69358、第三次fx_3c53e84221f74d19；按当前revision去重为2道已审，1975道未审。没有丢失审核数据。根因：claim跳过已审，但initial固定首题、refresh直接回当前、clip/子题列表不读审核记录；提交后无下一题时还回退已审本题。另外日志发现BrowserState初始事件入参为空，改为浏览器localStorage恢复昵称后链式执行初始队列。

实现：统一filtered_questions+review_index（按当前题目revision聚合所有审核员意见），默认“未审核”，已审/分歧/全部另入口。所有列表/首次加载/刷新/切clip/选题/提交共享过滤；耗尽时清空而非回退。提交立即显示时间/题ID/答案/结论并刷新已审计数，追加记录flush+fsync。同clip可能多题共用视频，题目列表明确状态和区间。两题库标签明确1977道异常MCQ与历史2309道开放QA/648clip；历史开放题统计923完成性、648整体、417时长、250详细过程、71顺序，candidate2282/held27。

验证：.venv-review Python3.14/Gradio6.28.0 CPU界面修复，无GPU或新模型请求。test_front_mcq_review_queue.py在临时目录重现并验证initial、刷新、clip/子题过滤、保存回执、多人共享状态、历史入口、耗尽、题目revision变化；所有assert通过，四份Python语法通过。重启7863实际API：初始化和刷新返回未审fx_c9ef8d10000cf557，切已审回显ldq的B,D,G，切回未审不重复。3条原记录SHA重启前后完全一致，测试未写生产人审意见。记录见review_queue_fix_preserved.json、review_queue_fix_verification.json；没有浏览器截图验证。
### 2026-09-28 7863播放判断区间高亮

实现：front_mcq_timeline.py用scope.playback_interval_s生成HTML；独立JS监听视频时间/拖动/加载事件，MutationObserver处理Gradio组件替换与切题；CSS显示范围色块、当前时间及区间前/内/后提示。判断段起点包含、终点不包含；进入判断段时绿色边框与色条只表示时间位置。绑定question/group及实际视频src，防止换视频期间展示旧媒体的高亮。提供从起点和起点前3秒播放按钮，支持可操作进度条。无新推理请求或视频转码，未改变题目与标签。

验证环境：.venv-review Python3.14、Gradio6.28.0；Firefox156.0.1 headless、geckodriver0.37.1，1440×1100窗口，CPU浏览器测试，无新增GPU任务。1,977题结构化区间有效；Python编译和node语法检查通过；原审核队列回归通过。真实页面以用户示例fx_c9ef8d10000cf557检查31.16666667起点和64.53333333终点，区间前/内/后、绿色边框、起点播放、提前3秒、滑条定位均通过。实际下拉切到fx_879a904c48ec1a9c后，区间更新为60.30–77.53秒、左手，定位中点后正确变绿。检查inside/after/switched三张截图。审核记录原3条SHA保持1291c918c7a2ee3a5fa3761ea8cdb84fecc71ca12ea91ed79b4f647e5edd5668，无测试审核写入；http://10.112.70.171:7863返回200。

浏览器测试归因：初始脚本假定题目标签为label元素，实际Gradio用span与input aria-label；另JS.click()没有触发选项的完整交互。改用真实DOM的aria-label和WebDriver点击，最终完整通过；服务代码不依赖上述测试选择器。结果与截图保存在outputs/impact_qa/front_mcq_expansion_v1/timeline_browser/verification.json及同目录PNG，失败DOM仅作调试记录。
### 2026-09-29 用户授权清空当前MCQ人审

输入：front_mcq_expansion_v1/collaborative_reviews.jsonl共8次ldq提交、7道不同题，均为pass；claims.json存在，旧human_reviews和human_review_history不存在。取得collaboration.lock后逐字节备份原意见与领取状态，保存SHA/题库SHA及理由，再用临时文件+fsync+replace清空活动ledger和claims。备份目录review_archives/reset_20260929T101652+0800，清空后0已审/1,977未审，题库SHA不变，未覆盖GT、开放QA或模型依据。

环境：沿用.venv-review Python3.14/Gradio6.28.0；本轮CPU文件操作和只读API，无GPU任务/新模型请求，不重启服务。实际7863 /front_mcq_progress 与 /initialize_front_mcq 返回1,977未审、0已审、0分歧；无测试审核写入。此为用户指定的审核重置，既有历史验证日志保留其当时计数，不回写成新状态。

复核：读取论文§3.1–3.2、发布README与既有规则报告，直接查看fx_d68d994f397213b8的20.533与25.333秒两张front缓存帧；只支持接触区域被遮挡的可见性限制，未进行完整视频重审，也未认定GT错标。web工具404；后用直接HTTP取得官方README和arXiv原文均200，未据网页获取失败声称作者无标注手册。完成review_criteria_reset_20260929.md及核心记录；所提盲审界面、60–100例校准与作者询问尚未执行。
### 2026-09-29 拆装参考及实时审核辅助部署

实现：review_reference_v1.json保存六类定义/排除条件及A/B带证据边界的拆装参考；front_mcq_guidance.py复用v28r_object_knowledge、native_trial和common，加载front原TAS-B/TAS-S与ASR真实state_sequence，不用重复state_changes行。序列按源fps换算clip局部半开区间；ASR仅在声明范围有效，无标注明示未知。独立JS依附现有视频timeupdate/seek事件更新双手动作、当前步骤、对象适用工具、完整/相关状态；HTML折叠流程、工具、部件和六类核验点。当前对象与粗步骤不同则提示差异并优先对象参照，不把粗步骤绑定到泛称screw。

环境：.venv-review Python3.14、Gradio6.28.0，Firefox156.0.1/geckodriver0.37.1，1440×1100 headless截图；纯CPU UI工作，新增GPU请求0，未修改现有vLLM。全1,977题验证：A1545/B432，有ASR1532/无ASR445；316个来源文件SHA、半开区间、动作/步骤翻译、B无虚构ASR、状态值/长度均通过。测试写首10条摘要至guidance_verification.json。源码Python/node语法通过，test_front_mcq_review_queue.py回归通过，测试人审均用临时目录。

真实浏览器最终通过：目标起止高亮、起点/提前3秒/进度定位、同视频切题、切换A/B视频、双手动作与步骤匹配、B明确无ASR、A跨状态变更、参考折叠。guidance_browser/verification.json保留结果与4张截图，人工查看A/B截图确认布局。题库、人审ledger、claims SHA与guidance_before.json一致，http://10.112.70.171:7863返回200。保持单7863服务，原QA/标注不修改。

失败归因：Gradio morph复用DOM节点导致旧guide payload未失效，改为比较data-guide原文并监听该属性，换题不再显示旧对象/等待错误。浏览器网络调试钩子错误使用fetch.apply(this)造成测试端连接中断，已完全移除，未为此修改生产请求机制。自动化Ctrl键/clear交互造成筛选不稳，改为输入框input事件过滤后WebDriver真实选项点击；修复测试函数名被element局部变量覆盖。另发现原泛称screw/M4_nut名称携带A配置/适配板身份，实时动作显示改为实例未明/位置未定；旧ASR四个螺丝名保留映射待核。web工具404，依据已有带SHA的一手手册与今日已核验论文资料，不声称取得新的B专用手册。

### 2026-09-29 7864独立3D装拆示意

交付apps/impact_assembly_3d，Three.js 0.160.1本地依赖和MIT许可，15个组件组/14步A装拆、三类工具示意；B仅结构观察，动画按钮禁用。纯静态HTTP服务绑定0.0.0.0:7864，浏览器承担WebGL，新增GPU推理请求0、无CUDA依赖；现有7863/QA/vLLM未改。服务PID与日志在outputs/impact_qa/assembly_3d。70秒为模拟时长，0.5/1/2倍速、任意进度、逐步、分解、透视和点选，不声称精确机械模型。

验证环境：Python3.14/httpx、Firefox156.0.1/geckodriver0.37.1，Xvfb 21.1.4本地解包、LIBGL_ALWAYS_SOFTWARE=1；1500×1050和430×930窗口。脚本check_assembly_3d_browser.py通过WebGL2初始化、播放前进/暂停稳定、逐步/定位、装拆、Phillips/Torx/wrench映射、B禁用流程、手机无横向溢出、页面JS异常0。人工查看初始/装配/工具截图，调整名称避让；Python和JS语法通过。结果verification.json和截图保留，浏览器检查不产生人工QA审核记录。

失败归因：服务器Firefox headless无法创建GL上下文，改用隔离Xvfb显示+软件GL，未修改GPU推理服务。WebDriver立即截图会捕获软件渲染尚未呈现的前一帧，截图前增加1.2秒等待再看实际终态。另修正拆卸文字不可复用安装指令、螺丝往复摆动改连续转动、Torx批头不能画作内六角、窄屏播放条换行。工具转向/圈数仍仅示意，无已校准线程规格；不将浏览器通过等同于物理正确性验证。

### 2026-09-29 B型3D动画补全

新增model_b.js独立B几何/12步和拆卸文本，共11可点选组件组；补上原静态模型漏掉的两颗壳体连接螺丝，区别A的适配板M4螺母。按项目图建银灰壳体/轴承板、转子铜色换向器/支承法兰、远端适配板与细手柄，A组件实例独立保留。共用播放器支持B安装60秒/拆卸反向、暂停、进度、速度、分解和视角；?model=B直达，页面源模块加版本参数避免旧缓存，右栏加入项目原图。未调用VLM或改7863/QA。

输入核查：官方项目页curl200，图在本地固定commit有SHA；web工具404/GitHub raw超时，使用核验存档。放大图明确两组螺丝，top149秒见十字在开盖壳体区域操作；top208秒遮挡，未作保持螺母动作结论。保持螺母扳手仍为图示六角接口推定，B轴承板一字仅按已有视频样例，不编造排他工具规范。图形、路径、螺丝槽口、紧固深度与适配板保持均说明是示意。

验证：静态服务HTTP与PIL/httpx预检通过，Node两个JS模块/Python语法通过；Firefox156.0.1/geckodriver0.37.1，Xvfb21.1.4+软件GL，无GPU推理资源使用。浏览器验证A/B暂停稳定、B十个组件均实际移动、12步正反端点位置一致、wrench/Phillips/flat工具可见、B无A拨杆/M4组合、远端位置、原图加载、直达B、A/B/A回归、430像素无横溢出。client_errors=[]，verification.json及截图在b_animation_v2；人工查看B终态和两类改锥操作截图。结果是交互和结构映射通过，不是机械仿真精度评测。原A源码已备份revisions/a_only。

环境处理：shell无ffmpeg，改用已安装/home/ldq/miniconda3/envs/ffmpeg/bin/ffmpeg提帧；未新装系统包。SVG放大使用已安装librsvg/cairo，不修改推理环境。

### 2026-09-29 A/B完整安装参考视频

select_complete_assembly_videos.py复用common/source_frames/merged_intervals，遍历全部55份front Reassembly（不分训练/验证/测试）；四split ATR按手/起止/标签去重。A45/B10零异常各0；选中各自最短且异常较低的ER07AD15_Reassembly_A_004_front=132.233333s、NA07GE21_Reassembly_B_005_front=153.366667s。A原子异常5行/ATR4段/时间并集6.333333s=4.7895%；B2行/2段/3.466667s=2.2604%，包含全部短标记，不应用1.5s或5s过滤。55trial每手异常时间并集与ATR相符。A最终17组件ASR全1；B无ASR，主要阶段与结束标注齐全。抽源帧A22/B21，人工查看阶段联系表，首尾和组件渐进安装可见；未进行连续逐帧机械质量认证。

媒体1280×720、H264、30fps，A136555617字节/B165338957字节。原片软链接，不复制重编码或剪掉异常。videos.html+videos.js+assembly_videos.json在7864展示，两段互斥播放、阶段/异常定位和GT时段高亮；三维首页加入口，原7863和QA/vLLM未改。服务器由python http.server改为同7864的Starlette1.6.0/uvicorn0.53.0静态服务以支持Range；媒体首1024/末1024字节HTTP206均与源文件比对一致。server.pid记录新进程。

预检：sop Python3.12、PyAV18.1.0/Pillow12.3.0和FFprobe可用；UI .venv-review Python3.14/httpx可用；无GPU推理任务/CUDA依赖。Python新脚本和JS语法通过。Firefox156.0.1经Xvfb显示测试A/B实际播放前进、主要阶段定位、异常高亮、末尾解码、移动无横溢出；A/B 3D页面WebGL初始化仍通过。browser/verification.json及截图保存，查看A异常时段截图确认布局。完整文件和标注SHA/first10_precheck/排名存complete_videos目录，人工审核记录未写。

失败归因：最初要求ATR逐类别区间与TAS-B完全一致，在AL07EJ17_Reassembly_A_003右手Spatial发现ATR3760–4044段继承多类，而原Spatial仅3760–3784。22trial有此分组扩展，改为核对每手所有异常时间并集，展示精确类别时间仍使用原TAS-B，不宣称ATR派生是独立GT。

### 2026-09-29 A/B中英文拆装文字交付

复读A官方手册渲染、review_reference_v1及B独立动画证据，输出两型号各6安装步骤/5拆卸步骤的中文和英文版本。文档人工核对工具映射及中英文不确定性一致；A内部螺母避免M4/M6强行归一，B远端适配板保持和轴止转等不补造。无新模型实验、无代码变更、无需GPU/CUDA检查，未改变7863/7864服务和QA数据。

### 2026-09-29 MCQ SOP视觉核验：过滤、预检与试跑

独立输出mcq_sop_visual_v1，原1977题中GT异常1809/规则候选168。严格目标时长<1.5秒筛掉781题，1196保留（GT1082/候选114）；invalid/no_segment/out_of_range均0。15条恰好1.5秒保留，源帧校准防浮点误差，时长先按帧差计算避免小数消去误差；九组测试通过，涵盖多段任短整题剔除、帧率/时间轴、漏标非法越界、泄漏与输出合同。spatial保留254/671=37.85%，显著低于不含spatial题72.76%；多标签且trial相关，探索性比例检验不当作最终统计推断。

环境：沿用3个vLLM TP2服务8000/8001/8002，GPU0–5 RTX4090各49140MiB，每服务maxseqs8/maxlen32768/mm32图，权重目录Qwen3.8_27B实际config=Qwen3_5ForConditionalGeneration。torch2.10.0+cu129/CUDA12.9，7GPU可见；并非CUDA<=12.1环境，不安装/变更框架。PyAV18.1.0/transformers4.57.6。preflight.json保存设备占用和服务models响应。225份有关标注SHA、111视频size/mtime与原题SHA冻结。

输入8/12/16目标帧（按<4s/<20s/其余分段），前后各最多2图，最长边960另加时间条，像素上限589824；temperature0、top_p1、seed20260929、enable_thinking=false、max_tokens1800、严格JSON、三次重试；3服务各并发8，解码4线程。SOP按A手册/B图及已有证据重建，PSR51项/17组件没有依赖边且flags全false；不假称官方完整拓扑。目标手沿用原题，另一手作为上下文。

试跑8项覆盖A/B×装/拆各最短/最长，全部有效返回：3 normal、5 insufficient。查看3正常项各首中尾9帧：工具撤出归置、持件靠近支撑对象可见，没有因此证明未采样时刻正常。首条小件身份仍非完全可辨，模型normal不是机械规范认证。没有把试跑8项当作准确率评测。

失败归因与修正：vLLM结构化解码不支持uniqueItems，API去掉该关键字而本地保留去重校验；最初模型把目标29.17秒区间改写成0–1.5秒，增加末尾硬范围提醒、schema时间上下界/目标帧枚举，时间越界结果拒收。失败版本归档revisions/schema_api_r0和time_contract_r1。8002一条曾因旧多模态缓存失配HTTP500，reset_mm_cache接口因非开发模式不可用（404），正常换服务断点重试后成功；未重启推理服务。

本轮抽帧参数复查：原片均front30fps，多图输入，无固定视频fps。精确时长档位应574/556/66；实际source浮点相减使恰好4s的fx_e465541f6196fd4d取8帧，真实档位575/555/66，仍满足用户8–16要求；下版按源帧时长直接分档。客户端960×572，图像处理实测grid[1,36,60]、merge2，每图540视觉tokens，20图10800；长133.5秒段最大间隔8.9秒，不能据稀疏图像证明持续正常。详见audit/sampling_rules.json。全量启动的短shell nohup进程退出，改用持久执行session，实际runner PID3380012；独立monitor脚本监督续跑、汇总和完整性审计，不改变协议。
