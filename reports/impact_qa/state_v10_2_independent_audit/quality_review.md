# v10.2 QA逐题质量复审

结论：部分题目可以保留用于小规模SOP问答开发，但本批尚不足以作为正式异常理解训练集或评测集，不建议沿用当前取样与生成方式直接扩量。主要问题是状态标签与操作异常的混淆、动作对象失准、视觉证据不足，以及题目和答案分布单一。不是所有问题都能靠润色prompt解决。

## 审查范围与方法

本次审查最新v10.2的24道开放题、12道MCQ，未重新审核旧v7–v9全部数据。逐题核对原始ASR状态、TAS-S粗动作、TAS-B双手动作，并直接查看三个原视频的22张图板，共205个不同源帧。概览每5秒抽帧；12个窗口各查看末6秒的8个时间点（末尾额外加密）。审查裁剪坐标为原1280×720画面的[400,330,850,640]，未增添源像素。

这是研究代理的源标注知情复审，不是真人签署或盲审，也不是连续播放全部视频。本轮没有再调用生成/审核VLM。抽帧间的短暂动作及遮挡下细节仍可能遗漏。因此下文“保留”均指开发候选，不等于已通过正式验收。原始候选保留，所有真人审核字段仍为pending。

可复核资料：[逐题CSV](per_question_audit.csv)、[逐题JSONL](per_question_audit.jsonl)、[原帧清单](frame_manifest.json)、[客观检查](objective_checks.json)、[6条改写建议](revision_proposals.jsonl)。

## 逐题处置

|处置|开放题|MCQ|主要内容|
|---|---:|---:|---|
|保留为开发候选|12|6|适配板完成、手柄连接，以及去重后的适配板→轴承板、锁紧杆→手柄顺序|
|改写动作对象|3|0|“安装齿轮箱外壳”没有可靠动作关系依据，应对齐实际转子安装步骤|
|改写任务语义|3|0|轴承板仍在安装，改成截至末帧是否完成，不能扩成操作错误|
|补视觉证据|3|3|轴承板state=1有源标注支持，但局部接合细节不足以独立检验正确性|
|暂缓异常用途|0|3|ASR=-1的原生状态题映射正确，不能直接作为发生操作错误的证据|
|去重|3|0|同trial两个重叠窗口询问同一适配板→轴承板事实|
|合计|24|12||

这不是人工正确率。24道开放题和12道MCQ的状态数值均与源ASR相符，但字段一致不保证自然语言语义和视频可回答性。

## 具体判断

### 1. 可以保留的典型题

“Had I correctly installed the anti-vibration handle into the gearbox housing by the end?”

三个视频末段都能看到侧手柄的旋拧及最后连接结果，ASR也为1，问答对象清楚，可以保留作为简单安装关系候选。这里的“正确”限于原生装配状态，不能推导出达到规定扭矩、内部连接完全合格等画面不可验证的工程要求。

适配板先于轴承板、锁紧杆先于侧手柄的观察顺序也有时间线支持。题目所说“as shown in the supplied guide”应保持为图示顺序对照，不能解释成其他顺序必然违规。已有锁紧杆题修订从“整套locking lever assembly”缩小到“locking lever”，本轮保留该修订。

### 2. “尚未完成”不能直接升级成“操作错误”

原开放题：“Had I correctly installed the bearing plate by the end?” / “No, the bearing plate was not correctly installed by the end.”

对应MCQ答案：“Incorrectly installed.”

|视频尾号|目标末帧/秒|ASR|末帧所在TAS-S|该TAS-S异常字段|
|---|---|---|---|---|
|002|2882 / 96.067|-1|insert_bearing_plate_assembly，2754–3600|false|
|003|3016 / 100.533|-1|insert_bearing_plate_assembly，2869–3768|false|
|004|3007 / 100.233|-1|insert_bearing_plate_assembly，2892–4302|false|

三个窗口都在首次出现-1后15帧（0.5秒）结束，画面仍是定位、置入螺钉或使用螺丝刀。003、004的末帧双手动作均标normal；002右手tighten_screw为normal，左手null带temporal anomaly，不能称002双手均正常，更不能把左手空动作异常归因为轴承板装错。跨层标注并不矛盾：ASR描述组件状态，TAS描述动作/过程，两者不是同一个问题。

原开放答案并非数值错配，但作为异常理解负例容易诱导“操作者犯错”的过度解释。建议改成：

> Q: Had I finished installing the bearing plate by the end of this clip?
>
> A: No, I was still working on its installation when the clip ended.

这是针对本次画面与粗步骤边界提出的完成题改写，不是将ASR=-1在全库重新定义为“安装中”。MCQ原生三状态映射可保留为源标签任务，但这三题暂不纳入操作异常理解子集。要问具体装错哪里，必须新增明确支持该错误的证据；不能编造错误方向、错误螺钉或遗漏。

查看：[002末段](AL07EJ17_Reassembly_A_002_front/bearing_incomplete_last6s.jpg)、[003末段](AL07EJ17_Reassembly_A_003_front/bearing_incomplete_last6s.jpg)、[004末段](AL07EJ17_Reassembly_A_004_front/bearing_incomplete_last6s.jpg)。

### 3. 状态名被错误地扩写为动作名

三个原问题都问：“Had I installed the gearbox housing before starting to attach the adapter plate, as shown in the supplied guide?”

ASR确实给gearbox_housing=1，但该字段本身没有提供“把外壳安装到哪个部件”的关系。画面与TAS-S显示此前主要是在手持壳体中安装转子组件；TAS-S明确区分retrieve_gearbox_housing与install_rotor_assembly，没有本题所暗示的独立install_gearbox_housing步骤。

三个视频最后一段install_rotor_assembly分别结束于970、856、1077帧；第一段attach_adapter_plate分别开始于1040、945、1152帧。可以改为基于真实动作的开放顺序题：

> Q: Which did I work on first: installing the rotor assembly or attaching the adapter plate?
>
> A: I worked on installing the rotor assembly first, then attached the adapter plate.

这一改写只问实际先后，不暗示已证明转子所有部件正确安装，也不声称顺序唯一合法。具体标注段已保存于revision_proposals.jsonl，原题未被覆盖。

### 4. 已完成轴承板题仍需局部证据

三个正例末帧为3628、3782、4327，ASR均为1。密集抽帧显示最后紧固、移开螺丝刀及转入后续动作，支持“已结束该安装步骤”的粗判断；但小部件被手、工具或壳体遮挡，不能据此独立验收所有接合位置正确。因此3道开放题和3道对应MCQ继续暂缓。

应补同一时刻的已同步其他视角或截止末帧内更清晰的证据。后续安装成功不能反过来证明更早末帧已经安装成功；如延长视频改变问题截止时间，必须重新计算答案与窗口，不能只把未来画面补进原问题。

## 数据集层面的问题

- 开放题21 Yes / 3 No。恒答Yes的二元极性基线为87.5%；这不是开放答案语义准确率。12道顺序题全部Yes，无法检验是否真正理解顺序。
- 24题只有7种逐字不同问句，全部为Yes/No判断式。本小批可用于流程冒烟，但尚未覆盖简单的“哪里做错了”“刚才纠正了什么”等异常理解问法；不要求每题都做复杂因果推理。
- MCQ有9个“Correctly installed”、3个“Incorrectly installed”，没有state=0正确答案。即使A/B/C位置各4，始终选“Correctly installed”仍有75%的标签基线。
- 每个trial的bearing_done与bearing_incomplete顺序题完全复用相同断言，共3对重复。可保留媒体用于其他题，但同一事实只计一题；重叠窗口不能跨训练/验证集。
- 只有1名参与者、3次执行，无法说明泛化效果。候选规模小，以上比例不能外推为IMPACT全库的缺陷。

## 下一轮应改什么

1. 选题器先区分完成状态、安装状态、实际动作异常、图示顺序对照。读取源标签不等于已经建立跨任务映射。对这些类别采用不同证据门槛。
2. 正常安装进行中的片段用于完成进度题；从有明确目标动作异常及可见证据的事件生成异常题。PPR anomaly本身也不能自动补出错误的自然语言机制。
3. 动作名从TAS-S/TAS-B及实际画面核对，关系从明确来源核对，禁止仅由组件state=1自动构造“安装了该组件到某处”。
4. 先修订现有6题、去除3个事实重复，再扩充不同参与者、state=0、真实可支持的No与非判断式问法。若没有可靠顺序负例，就暂不生成，不能为平衡类别造错。
5. 在生成前检查采样和类别分布；在生成后检查源支持、可见性、措辞范围与重复。prompt只能约束表达，不能修复缺失视角和缺乏异常证据的选样。

本次判断取代上一轮“15保留、3范围修订、6待补证据”的较粗分流，用于后续候选选择；旧文件仍保留作历史记录，不能继续把旧priority文件当成最新审核通过集合。
