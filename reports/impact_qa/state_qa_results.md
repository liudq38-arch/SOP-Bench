# IMPACT 安装与顺序 QA：v10 开发结果

已完成三轮开发，最终v10.2为12/12窗口成功、24对英文开放题、12道安装状态MCQ。所有数据仍为pending_human_review。建议从[代理审阅页面](../../outputs/impact_qa/state_v10_2/review_agent.html)查看视频、问答、来源和待核事项。

## 结果与迭代

| 版本 | 窗口完成 | 开放题 | 自动保留/需证据 | 发现的问题 |
|---|---:|---:|---:|---|
| v10冒烟 | 4/4 | 8 | 7/1 | 4个类型字段错填；一条把螺丝-1写成未装0，自审也漏检；答案出现标注口吻 |
| v10.1 | 10/12 | 20 | 14/6 | 两个规划输出把规则id写进证据id，程序拦截；组件状态声明与来源一致 |
| v10.2 | 12/12 | 24 | 18/6 | 改为代码选题，无类型/状态/引用结构错误；仍需逐题语义与视觉检查 |

这些是同模型审核统计，不是准确率。三个版本输入、规划方式和证据均有变化，也不是严格的提示词单变量消融。

最终开放题：安装完成9、部件—接收对象安装关系3、图示顺序对照12；Yes/No=21/3。12道MCQ按ASR三态生成，本批答案来源为9个正确安装与3个错装状态，未包含state=0正例；答案位置A/B/C各4，不等于语义类别均衡。

研究代理逐条读24题并检查12张精确帧图及官方示意图：15条保留候选、3条范围修订、6条需补视觉证据。3条修订把“整个锁紧杆组件已安装”收窄为直接状态支持的“锁紧杆已安装”；原文、自审和修订分别保留。6条都是轴承板末态问题：源标注支持答案，但局部遮挡/分辨率限制使当前画面不足以独立判定精确安装状态。代理没有完整播放每段视频，也没有把看图检查称为真人审核。

## 实际英文样例

**安装到指定部件**

Q: Had I correctly installed the anti-vibration handle into the gearbox housing by the end?

A: Yes, the anti-vibration handle was correctly installed into the gearbox housing by the end.

依据：同视角末态ASR=1，官方示意图与研究代理画面核对提供手柄→壳体关系。关系映射仍待真人核验。

**尚未正确安装**

Q: Had I correctly installed the bearing plate by the end?

A: No, the bearing plate was not correctly installed by the end.

依据：窗口末态ASR=-1，不虚构螺丝未装、松动或方向错误。此例仍需更清楚的视觉证据或真人确认。

**按提供的图示检查先后**

Q: Had I installed the adapter plate before starting to insert the bearing plate, as shown in the supplied guide?

A: Yes, the adapter plate was correctly installed before I started inserting the bearing plate.

依据：适配板状态变为1的时间早于轴承板插入动作开始。此题比较图示顺序，不宣称其他所有装配顺序都是错误。

## 真实输入与运行配置

三个Model-A front视频来自同一参与者的三次执行，原片H.264、1280×720、30fps，5214/5126/5623帧；15963帧全部解码PTS与ASR帧号/30一致。front ZIP为31,487,236,951 bytes，官方SHA-256校验通过，仅按需解压三个成员并通过解压CRC。

12窗口长度37.267–106.367秒，中位数74.400秒，包含前序步骤，区别于此前几秒的手部微动作。审核输入：1024×576 H.264片段固定16帧＋6张1280×720精确锚点＋2张同帧工作区裁剪。裁剪仅放大现有像素，不产生更高的原始细节。

Qwen3.5-27B，三组TP=2 vLLM服务，单服务并发4，总并发12，上下文32768；torch2.10.0+cu129、7张49140MiB GPU，使用6张，另1张空闲。不是CUDA<=12.1环境。温度0.1、top_p0.8、seed20260918，关闭thinking，生成预算2200、逐题审核1500tokens。

v10.2共36次API调用（12次生成、24次审核），省去每事件一次LLM规划调用。审核请求最多23668输入tokens；生成/审核请求延迟中位数31.53/27.85秒，包含服务并发等待，不能相加当成整批耗时或报告为独占速度。[运行统计](state_qa_runtime_metrics.json)

## 文件与验证

- [代理审阅后的24候选](../../outputs/impact_qa/state_v10_2/agent_reviewed_candidates.jsonl)：含3条明确标识的代理修订，全部待真人审核。
- [优先审阅的18候选](../../outputs/impact_qa/state_v10_2/agent_priority_candidates.jsonl)：15原候选＋3范围修订，不是已通过人工验收的数据。
- [需更清楚视觉证据的6候选](../../outputs/impact_qa/state_v10_2/agent_needs_visual_evidence.jsonl)。
- [12道状态MCQ](../../outputs/impact_qa/state_v10_2/state_mcq_candidates.jsonl)：原生ASR三态扩展。
- [开放题评测输入](../../outputs/impact_qa/state_v10_2/agent_evaluation_inputs.jsonl)、[MCQ评测输入](../../outputs/impact_qa/state_v10_2/state_mcq_evaluation_inputs.jsonl)：不含参考答案或执行真值；标识和媒体路径不含结果词。
- [逐题代理审阅记录](state_v10_2_agent_audit.json)、[最终验证](state_v10_2_agent_package_validation.json)、[来源快照](state_qa_provenance.json)。

验证涵盖：原片PTS/帧数、片段帧数、源JSON指针、逐组件逐帧状态声明、候选唯一性、评测字段和标识隔离、源文件存在、v7冻结哈希及新增代码语法。它不代替语义正确性评测。

当前只有7种不同开放问句，三个重复执行产生相同问题是预期现象，不能把24条计为24种问法。本批不评估泛化，也未覆盖真实违反必做顺序的案例；强制顺序/漏步题继续等待可靠的型号专属约束。后续扩样需加入不同参与者、未安装状态、真实顺序变化，并按trial划分开发和测试。
