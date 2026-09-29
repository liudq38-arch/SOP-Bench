# v11：视觉与GT共同支撑的QA生成

已实现并运行：生成器同时接收原始视频帧、原始GT记录、由代码推导的GT参考答案、时间范围和公开流程；模型生成自然问题和简短答案，再分别进行GT语义核验与不带GT的视觉回答。GT参考答案是从结构化标注转换得到的约束答案，不是IMPACT原本就提供的自然语言QA。

## 具体输入与生成方式

```text
ASR / TAS-S / TAS-B原始GT
  → 适用题型检查、时间对齐、源文件哈希与JSON指针
  → 单题事实约束 + GT参考答案 + 同一时间范围的视频帧 + 公开流程
  → VLM生成开放问答、MCQ问句
  → GT语义核验：问题、生成答案、选项是否与原事实一致
  → 独立视觉回答：只给问题、帧、时间和公开流程，不给GT
  → 研究代理查看源记录、画面与生成结果，保留/暂缓
```

生成器可以自然改写答案，不能改变命题、对象、极性和截止时刻。画面不清楚时输出可见性不足，不用GT假装“看到了”。MCQ三个选项由代码按同一维度构造，正确项来自GT，再置换位置；不让模型自行修改答案。独立视觉回答不是唯一过滤器：模型可能识别失败，也可能答案正确但理由错误，必须具体复核。

|题型|GT依据|允许结论|禁止外推|
|---|---|---|---|
|组件安装状态|ASR组件索引＋精确帧状态|该组件在末帧的安装状态|扭矩、隐藏公差、整机完成、未知接收部件|
|未安装|ASR=0|该组件尚未安装|装错、漏步或操作者犯错|
|动作进行中|TAS-S区间跨过末帧＋该组件尚未正确装配|截止末帧仍在安装|把ASR=-1改成操作异常|
|实际顺序|TAS-S具名动作的真实区间|哪个先发生，含真实反向命题No|把观察顺序当作唯一合法顺序|
|工具|TAS-B动作名、手和对象|此次拾取的工具；必要时退到较粗工具类|把拾取工具推成正确工具、凭颜色猜刀头|
|动作时长|动作闭区间＋30fps|该标注动作的实际时长|规范时长或未经定义的连续动作边界|
|动作异常类别|TAS-B具名动作＋手＋phase＋六维属性|该动作对应的原生异常属性|具体物理机制、原因和修复方法|

每条contract保存完整原始记录、文件SHA-256、JSON pointer及计算依据，共核验59个来源引用。缺乏权威关系的安装接收位置、强制顺序违规、漏步和纠正因果本批不生成。公开流程保留，挖掘图不作为规范GT。[原始输入](../../outputs/impact_qa/gt_v11_inputs/contracts.jsonl)、[首十条预检](../../outputs/impact_qa/gt_v11_inputs/first10.jsonl)。

任务区分依据来自官方说明：ASR预测组件状态，PPR按左右手分别预测阶段，ATR是异常段上的多标签属性；它们不是互换标签。原文短句“independently for each hand”和“multi-label diagnosis”对应这一范围。[官方BENCHMARK](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md)；[本地快照](../../sources/impact_docs/BENCHMARK.md)。本流程是本项目的工程设计，不声称为原论文提出的方法。

## 已执行与实际结果

- 两题冒烟完成；v11完成24/24题意、24开放问答＋24MCQ，未发生API最终失败。文本语义机器核验24/24通过，但不解释为语义正确率。
- 生成器自己标记12 clear / 12 uncertain；无GT视觉回答8 answerable / 16 uncertain。8个自称可回答里，3个工具题只答“红柄螺丝刀”，未回答GT要求的Phillips刀头类型，所以8不等于8个正确答案。
- v11.1针对6题修改：3道工具题改问工具大类，仍由原GT的具体工具蕴含；3道state=0题去掉“correctly”，直接问是否安装。6/6文本核验通过，无GT回答6/6自称可回答。部件状态题的理由仍有错认，不能用这个6/6宣称全部通过。
- 我直接查看18张不同图板，共253个不同原帧，并阅读24道开放题、24道MCQ和对应审核输出。最终按题意保留15个开发候选；3个部件身份待确认、3个时长边界待明确、3个异常可见性待补证据。对应开放/MCQ共享这些处置；没有额外运行独立MCQ答题。
- 最终开放答案为7 Yes / 7 No / 10描述性答案，11种不同问句。上轮为21 Yes / 3 No、7种问句。本轮任务组成改变，因此这里只比较分布，不能视为严格受控质量提升实验。

## 看得见的改进

**完成进度题**

Q: Had I finished installing the bearing plate by the end of this clip?

A: No, I was still working on installing the bearing plate when the clip ended.

依据是动作仍在当前时间段内进行及组件状态尚未正确装配；不再把这类样本称作装错。没有增加松螺丝、错误朝向等无来源解释。

**实际顺序的否定题**

Q: Did I attach the adapter plate before working on installing the rotor assembly?

A: No, I worked on installing the rotor assembly first, then attached the adapter plate.

003的最后一段转子安装止于856帧，适配板首次附接始于945帧；问的是实际先后，没有把安装外壳当成安装转子，也没有创造规范顺序违规。

**工具粒度调整**

Q: Which tool did I pick up with my right hand in this clip?

A: I picked up a screwdriver with my right hand.

原始GT为pick_up_phillips_screwdriver，但画面刀头不清。降到GT蕴含且可见的工具大类后，三个案例都得到视觉与GT支持。不把刀头识别不清误报为源GT错误。

## 仍未解决的点

1. 安装状态中的小部件身份。v11.1的004独立视觉回答虽然说No，理由却称正在安装轴承板，而源动作是适配板；还把末帧持物/收工具说成正在用工具。保留其原始回答作为失败记录，不能当视觉证据写进数据。需要可靠的部件图示、物体对应或其他同步视角。
2. 时长。原GT拾取时长为1.3/1.8/1.2秒，计算正确，但帧采样与人对“伸手—抓取—提起”的边界定义可能不同。未先定义评分容差与动作边界前，三题暂不作为严格视频时长评测题。
3. 异常理解。三个handling错误均有原生动作GT，但现有帧不能清楚支持具体错误表现。这轮已消除由ASR=-1直接制造动作异常的逻辑，尚未解决异常视觉证据缺口。不能从只有handling标签的样本生成“为什么错、如何修复”的具体答案。
4. 本批仍只有同一参与者三个执行，异常类别也只有handling。工具类答案也都为螺丝刀，顺序真值都为转子先于适配板；Yes/No更平衡不等于所有语义类别已经平衡。MCQ A/B/C为7/11/6，后续扩样必须同时检查语义类别和位置分布。

## 媒体、复现与产物

原片1280×720/30fps/H.264。每题输入13–19张原始全幅JPEG帧，窗口2.5–81.233秒；不是把每帧组成新视频后声称连续观察。采样含GT动作边界，所以这是标注辅助的分段QA协议，不是无分段原始视频端到端评测。评测输入去掉GT事实、答案、源路径和题型，媒体文件名用哈希；仍须明确边界采样利用了标注。

Qwen3.5-27B，三组TP2服务，每服务并发4，总并发12；实际7张49140MiB GPU。temperature=0.1、top_p=0.8、seed=20260918、thinking关闭；生成650、源核验700、视觉回答750 max_tokens。含冒烟与修订共96次API调用，最大输入19076tokens，请求延迟中位数16.10秒（含并发环境影响，不是独占吞吐）；环境torch2.10.0+cu129，未验证CUDA<=12.1兼容。v11恢复运行复用缓存。v7的16个冻结文件哈希不变。

- [最终开放候选24条](../../outputs/impact_qa/gt_v11_final/open_candidates.jsonl)、[MCQ候选24条](../../outputs/impact_qa/gt_v11_final/mcq_candidates.jsonl)。
- [优先开发候选15条](../../outputs/impact_qa/gt_v11_final/priority_open_candidates.jsonl)、[暂缓9条](../../outputs/impact_qa/gt_v11_final/held_open_candidates.jsonl)、[逐题代理处置](../../outputs/impact_qa/gt_v11_final/agent_review.jsonl)。
- [v11审阅页](../../outputs/impact_qa/gt_v11/review.html)、[六题修订审阅页](../../outputs/impact_qa/gt_v11_1/review.html)。最终JSONL已合并六题修订，旧页面保留原始版本。
- [无GT评测输入48条](../../outputs/impact_qa/gt_v11_final/evaluation_inputs.jsonl)、[输入/代码来源](gt_v11_provenance.json)、[请求统计](gt_v11_runtime_metrics.json)、[校验结果](gt_v11_release_validation.json)。

下一次扩量优先选择有明确可见异常的动作段，补正常对照及不同异常属性；对GT粒度超过视觉证据的题先降低问法粒度，不能降低到仍无法验证时就暂缓。所有候选仍待真人审核，无正式准确率或泛化结论。
