# IMPACT v1.1标注结构核验（2026-09-20）

依据本地官方v1.1包、此前下载的官方论文与代码。此次web工具返回404，直接获取GitHub亦未成功；未声称重新验证远端最新版本。源目录：`annotations/impact/IMPACT-v1.1/annotations/`。论文：[§3.2](https://arxiv.org/html/2604.10409v1)，本地原文`papers/IMPACT.txt`。官方[任务说明](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/docs/BENCHMARK.md)。

## 标注过程和范围

原文：“5 expert annotators over 7 months”；工业工程与工效学专家共同核验动作标签，11名独立验证者复核。论文流程为多视角标注、视角特定遮挡/阶段调整、任务标签构建、任务内时间一致性和跨任务对齐复核。数据112执行、13参与者、5视角；560视角文件不能当作560独立执行。

|层次|实际内容|发布形态|
|---|---|---|
|TAS-S|粗步骤时间段；26项mapping含NULL|560 JSON和560逐帧文本|
|TAS-B|每只手的原子动作、verb/noun、阶段及六异常属性|560 JSON；左右手各560逐帧动作文本|
|PPR|左右手normal/anomaly/recovery|左右手逐帧文本，来自TAS-B|
|ATR|异常片段六属性多标签|左右手T×6数组、T维有效mask、分段JSONL，来自TAS-B|
|ASR|17部件的-1/0/1状态时间线|92 front JSON，装配/拆卸各46|
|PSR|17部件×正确安装/错误安装/移除=51事件类|92执行的状态/事件CSV，train64/val10/test18|
|AF-S|预测手级下一原子动作的协议资产|由TAS-B派生，不是新增人工错误解释|

## TAS-B真实字段与例子

文件`TAS-B/front/MA07LF04_Reassembly_A_001_front.json`顶层有video_id、view、meta_data、view_start/end、anomaly_types、verbs、nouns、action_labels、segments。22动词、19名词、138动作词表项（含null，不是22×19全部组合）。动作段由action_label、verb、noun、start_frame、end_frame、phase、anomaly_type、entity组成；entity是操作者left/right手，而view是相机位置，两者不能混淆。

真实片段：action_label=37（insert_bevel_gear）、verb=11（insert）、noun=4（bevel_gear）、start_frame=419、end_frame=461、entity=left、phase=anomaly、anomaly_type=[1,0,0,0,0,0]。能确定左手插入锥齿轮时标为temporal异常，不能仅由这些字段确定“提前多少秒”或违反哪条具体依赖。

属性顺序为temporal、spatial、handling、wrong_part、wrong_tool、procedural，多热编码而非单选。名称可以作时间/时序、空间、操控、部件选择、工具选择和流程异常的概括；公开字段没有逐例自由文本错因、纠正说明、错误位置坐标或规范依赖ID。

`phase`区分正常/异常/恢复；恢复定义为解决前序异常的行为，但字段没有显式recovery_of事件指针。null动作也可为recovery，不能把action_label=0或六个属性全0直接解释为正常。

全量v1.1实测67492左右手跨视角片段：normal56482、anomaly9512、recovery1498。异常属性出现次数temporal4608、spatial3285、handling1779、wrong_part130、wrong_tool382、procedural1570；多标签且含多视角，不能相加为独立错误数。见[机器统计](annotation_schema_audit.json)。

## 重要核验：粗步骤异常字段不可用于判正常

TAS-S段字段id（出现序号）、label、f_start/f_end、has_anomaly、meta_activity。**全部560文件/21995段的has_anomaly均false，meta_activity均none。** 这两列在当前包中没有区分能力；无法据false宣称步骤无异常。源示例的TAS-B有异常而同执行TAS-S全false，是具体反例。必须基于TAS-B phase/属性及区间重叠另行汇总，记录推导来源，不将原字段改写为人工真值。

## 状态与完成事件

ASR components按id定义17个部件实例；state_sequence的每个frame给出完整17维向量，从该帧保持到下一记录前。-1错装、0未装、1正确安装，向量顺序必须用同文件components解码。state_changes是逐部件记录列表，含初始化和某些未变化值，不能把行数当真实转换数。`version:1.0`是包内该JSON字段的值，不应单凭此断言下载了错误数据发布版本。

示例在2673帧drive_shaft/bevel_gear/M6_nut为-1，在2778帧转1；PSR_labels_with_errors.csv在2673.jpg记录三个错误安装事件，在2778.jpg记录相应安装事件。ASR状态可支持截止时刻是否已装好，不能自动证明螺纹扭矩、接收部件、整机完成或操作者具体如何犯错。

PSR_labels_raw.csv为帧名＋17状态；PSR_labels.csv为成功安装/移除事件；PSR_labels_with_errors.csv还保留错误安装事件。component_names/procedure_info与ASR组件命名存在别名，例如screw_plate_topleft和screw_adaptor_topleft；不能依赖裸字符串连接。

论文PSR使用偏序前置关系；本地Gemini配置的procedure_graph.json元数据原文：“Edges are robust prerequisites mined from data.” 图由92记录挖掘，不是每段原子标注随附的独立工程规则。统计次序、图示顺序和必须遵守的规范依赖应分开，不用全数据挖掘图充当无泄漏的标准答案。

## 时间边界

原始JSON使用帧号。已对示例逐帧标签核验：419和461帧都是INSERT_BEVEL_GEAR，462变PLACE_BEVEL_GEAR；发布ATR JSONL的259–279段num_frames=21也支持端点包含。因此此类原始段按[start,end]解释，对应Python[start:end+1]；30fps示例覆盖[13.9667,15.4)秒，共43帧/1.4333秒。

这不自动改写历史QA内部名字为exclusive的派生字段；涉及精确时长必须先统一源与派生区间约定。不同视角fps不同：front等外视角通常30，ego原子JSON约24.917，TAS-S ego有24.92；不要直接复用同一帧号，应用对应视角文件并核视频PTS。状态题在时刻t取最后一个frame<=t的状态，禁止读未来状态。

## 对QA的实际支撑

动作/手别/标注时长取TAS-B；工具可能由noun或动作名直接编码，但并非每个动作都另有tool字段。实际先后由同执行动作/步骤起点计算；正确安装状态取ASR、完成事件取PSR；异常段和类型取TAS-B/PPR/ATR。空间坐标、具体错因、应采用何工具、接收部件与强制依赖并未在每段标准字段中完整给出，需要视觉和来源补充。GT可提供答案依据，但单个视角不一定足以看清，二者须分别审核。
