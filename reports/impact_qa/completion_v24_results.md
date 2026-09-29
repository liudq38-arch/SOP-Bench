# 具体安装完成性：同一手柄的前后状态对照

2026-09-21，延续用户要求的EgoErrorVQA式具体操作问题。此补充试验的目标是验证有明确GT时能否生成肯定/否定完成问答；不测试长视频history的额外收益。

同一源视频AL07EJ17_Reassembly_A_002_front，30fps、5214帧。ASR的anti_vibration_handle在4937帧进入-1（misassembled），5176帧变为1（correctly assembled）。精确裁剪两个窗口：4800–5000（6.7秒、模型53帧）和4800–5213（13.8秒、模型64帧），各自仅提供结束时有效的本视角状态。未来状态不进入早期样本。源视频完整PTS与ASR时间轴一致，裁剪逐帧数量和PTS验证通过，模型采样均覆盖目标状态有效区间。

共同问题：By the end of the clip, have I correctly installed the anti-vibration handle?

- 早期答案：No, the anti-vibration handle is not correctly installed by the end of the clip.
- 晚期答案：Yes, the anti-vibration handle is correctly installed by the end of the clip.

流程为不带GT的视频观察，再带同一视频、观察结果和ASR结束状态生成QA；每条带ASR源文件hash、JSON pointer、原始帧区间、视频hash和完整请求。它不是仅凭视频自行识别GT。两条均为pending_review，formal_release=false，未新增MCQ。

视觉限制：模型两例均选择cannot_independently_confirm，不能独立验证螺纹啮合等。代理查看各例首／中／末三帧：黑色手柄操作与终态可見，但无法仅凭接触页确认机械正确性；晚期终帧手已移开，模型笼统称终态被手遮挡不够准确。保留原始观察与限制，不能拿该观察作更细机械原因解释。ASR的-1不能自行扩展为用错孔、滑丝、扭矩不足，也不必然意味着操作者已结束操作后犯错；问题严格限定在视频截断时的安装状态。

4请求，39493输入/684输出token；两观察请求9.65/9.81秒，两QA请求10.84/10.78秒。Qwen3.5-27B，沿用3个TP2服务各并发1，temperature0.1/top_p0.8/seed20260920，observe最大1536、QA2048。环境与主v24相同，实际CUDA12.8；不声称12.1兼容。原生video_url传本地文件，8fps且最多64帧，实际解码manifest留存。

在现有7863当前步骤QA页面的样本下拉框新增两个完成性对照，复用同一端口。旧用户通过记录保留，新样本独立审核，正确/错误标签仅供审核人查看。

最终验证：4样本API读取通过、两个新视频Range206、原v23通过记录保留且新题均未审核；两个runner断点恢复均0新增请求。9项合同测试、全部改动Python语法检查通过。审核界面仍只有7863一个端口。GT支持与纯视觉可回答性仍是两项不同要求，后者待人工核验，不能把这一对样本计作视觉判断已通过。
