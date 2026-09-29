# EgoErrorVQA 风格对照与当前采用标准

用户已明确近期先满足 EgoErrorVQA 风格：简短的操作正确性、错误行为、纠正动作 QA。无需每题给完整 SOP 因果链，但依然不能虚构细节。

依据：EgoErrorVQA 附录 A 说明 “Our generation process is purely text-based”，以动作、错误描述等文本生成后再观看视频审核。因此写参考答案时可以使用源标签；这不意味着被测模型可以看到答案标签，也不意味着源标签自动证明具体物理原因。[原文](https://arxiv.org/html/2608.24134v1)；[本地流程研究](egoerrorvqa_generation.md)。

这次对照在既有 20 开发事件运行，输入原标注和研究代理之前看帧后整理的动作描述，没有使用 60 试制样本调参。不是纯自动视觉生成，也不是人工已验收数据。

v8 生成 35 对，存在标注腔、无依据的规范位置扩写、7 个事件漏审第二题。v9 逐题审核后生成 20 对，API 全部成功，引用/审核索引结构问题为 0；correctness=6、error_description=10、corrective_action=4。仍有少量“flagged”措辞以及“应该安装而不是放桌上”等无源依据的额外推断。

v9 自动审核 pass/revise/reject=3/3/14，不作为质量评分：逐条读取发现审核器常以“视频没有证明错误/恢复身份”为理由拒绝有原标签依据的参考答案，与本轮允许标注辅助的审核协议不符。另一方面，它又放过“应当在工件上使用螺丝刀”等无依据规范推断。保留原始返回，不通过改写统计掩盖这些问题。

## 适合先采用的问答形式

以下为 v9 原始生成原文，经研究代理结合原标注及已有看帧记录判断，可保留为候选；仍未获得真人签署。保留此判断和模型不同意见，不把模型 reject 自动当作标签错误。

1. TO08CO25_Disassembly_B_005_ego__left__0009，异常标签含 wrong_tool：
   - Q: Did I pick up the correct tool with my left hand?
   - A: No, I picked up an orange and yellow handled screwdriver, which is the wrong tool for this step.
   - 来源：wrong_tool 来自原始标注；拿起工具及外观来自目视记录；未指定正确替代工具。
2. KI05KO01_Disassembly_A_002_ego__right__0084，normal：
   - Q: Did I correctly separate the black circular piece from the body using my right hand?
   - A: Yes, I grasped the edge of the black circular piece with my right fingers and pulled it away from the body held in my left hand.
   - 来源：目标步骤正常来自原标注；抓边缘并分离来自看帧记录；不扩写整机状态。
3. NA07GE21_Reassembly_A_001_ego__left__0049，recovery：
   - Q: What corrective action did I perform with my left hand?
   - A: I picked up the small part from the work surface and moved it toward the assembly held in my right hand.
   - 来源：恢复身份来自原标注，动作来自看帧记录；没有宣称之前错误已解决。

## 采用边界

来源标签可支持该片段正常/异常/恢复及异常类别；简短视觉动作补足自然语言表达。问答不暴露“标注字段”，出处保存在独立字段。标签未指明的正确工具、目标位置、过早/过晚、具体力矩、修复成功不补写。无详细错误描述时不强行提出“为什么”的题。选择题继续采用原生阶段加六维多标签，保留与 EgoErrorVQA 类别式选择题相似的任务形式。

完整候选及自动意见：[ego_style_v9.md](ego_style_v9.md)。可机读文件：[candidates.jsonl](../../outputs/impact_qa/ego_style_v9/candidates.jsonl)。它们是开发对照候选，不是已确认真值或独立测试结果。后续采用此风格与事实边界，真人审核仍单独记录。
