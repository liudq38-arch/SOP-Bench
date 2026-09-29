# ATR原生视频输入配置与实测（2026-09-20）

已实现视频URL请求与真实服务测试；新请求用`video_url`及`file:///home/ldq/project/sop/outputs/impact_qa/...mp4`，由同机vLLM读取，模型不自行访问路径。允许路径已在现有启动参数配置。每请求1视频；不重启现有三服务、不修改冻结api.py。外部客户端若与服务端不共享文件系统，应改用可访问HTTP URL或视频Base64，不能传客户端本机路径。

## 当前执行参数

|参数|目标动作|前后上下文|
|---|---|---|
|采样fps|8|2|
|每请求帧数上限num_frames|64|64|
|最长窗口|8秒|32秒|
|相邻窗口重叠|1秒|2秒|
|事件范围|ATR前1秒至后1秒|ATR前3秒至后20秒|

窗口过长切分，禁止把整个长视频压到64帧后仍声称8fps。fps控制目标采样密度而非严格周期采样：本机opencv后端算`N=max(1,min(原帧数,64,floor(duration*fps)))`，随后linspace覆盖首尾。短视频最低4帧由客户端显式兜底，非假设HF的min_frames总会生效。34视角准备92窗口（target52/context40），实际6–64帧，记录每一帧原始索引及本地/源视频时间。

原视频裁切后缩放宽960、保留比例，不裁工作区；H.264/yuv420p/CRF20，无音频。`mm_processor_kwargs.do_sample_frames=false`，避免解码后再被HF默认2fps抽一次；视频总像素预算`size.longest_edge=16777216`、`shortest_edge=4096`。这些值在该Qwen视频处理器中是时空像素预算，不是最长边像素数。处理器按帧数自适应空间分辨率，并做时空patch：temporal_patch_size=2、patch_size=16、merge_size=2。

64帧实测：解码64×540×960；处理后每帧384×672，grid=[32,24,42]，视觉token8064，与估算完全一致。其他已准备窗口最大估算8160。奇数帧可能因时间patch补齐，不能把视觉时间块数直接当解码帧数。

当前Qwen3.5-27B是TP2，每组2×48GB卡；服务max_model_len32768、max_num_seqs4、image上限32/video上限1。后者是输入媒体个数，不是视频帧数上限。transformers的max_frames默认768只是其采样器默认配置，不是“48GB一定能跑768帧”，也不是当前关闭二次采样后生效的限制。本方案以解码器64帧约束为准。

## 请求示例

```json
{
  "model": "impact-qwen35-27b",
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "问题、目标区间及GT（仅生成阶段）"},
    {"type": "video_url", "video_url": {"url": "file:///home/ldq/project/sop/outputs/impact_qa/atr_video_v20/clips/example.mp4"}}
  ]}],
  "media_io_kwargs": {"video": {"video_backend": "opencv", "fps": 8, "num_frames": 64}},
  "mm_processor_kwargs": {"do_sample_frames": false, "size": {"shortest_edge": 4096, "longest_edge": 16777216}},
  "max_tokens": 1600,
  "temperature": 0.1,
  "chat_template_kwargs": {"enable_thinking": false}
}
```

fps与num_frames在本机vLLM解码层可以同时设置，取较小约束；HF重新采样时二者互斥。本方案只在解码层设两者，HF不重新采样。不能把两层配置混用。视频自带时间戳进入Qwen视频序列；人工可播放的视频仍比模型实际采样更密集。

## 实测与质量限制

3配对事件×2视角，共12 GT生成窗口请求＋6无GT目标窗口请求。18次都获得模型JSON响应、无HTTP/OOM错误；15通过基本选项和时间字段校验，3因选项不足3个拒绝。初始134.85秒，最大输入12092token；这只是接口/候选试验，不是18条正确QA。存在第三人称问法、题型漂移和GT过度解释，尚未通过此前完整质量流程。

无GT时，扳手事件ego回答screwdriver、front回答small silver tool，说明视频输入仍会误认；另一螺丝刀事件ego能描述橙色手柄、front描述红色手柄。不能用自报grade或这3例宣称视频优于静态图片、ego优于front。窗口和像素预算不同也使其不是严格等预算消融。

额外并发探测：3服务×每服务2请求，总6请求同时输入64帧，全部成功，约8.19秒，显存采样最大42191MiB。该测试仅输出14token/请求（上限160），不代表长QA生成已通过同样并发压力测试。**当前长QA默认每服务1并发，总3；每服务2仅作为已通过短输出探测的配置。** 不直接恢复图片模式的每服务4。

推荐任务分工：视频用于动作过程与后续变化；小部件/刀头/接触点仍需按证据补高清图或局部视角，不能无限加帧而牺牲空间细节。正确工具、纠正时限依旧需要规范来源，传视频不会补出这些GT。该配置是当前验证可运行的起点，不称全局最优。

## 可复现产物

- 参数：`configs/impact_qa/video_v20.json`
- 视频输入与实际采样：`impact_qa/video_input.py`、`scripts/prepare_atr_video_v20.py`
- 实测：`scripts/test_atr_video_v20.py`、`scripts/check_video_concurrency_v20.py`
- 帧清单：`outputs/impact_qa/atr_video_v20/windows.jsonl`
- 结果：`outputs/impact_qa/atr_video_v20/probe_results.jsonl`
- 报告：`video_v20_precheck.json`、`video_v20_processor_check.json`、`video_v20_concurrency.json`

行为核验基于本机vLLM0.18.0、transformers4.57.6源码：`vllm/multimodal/video.py`的compute_frames_index_to_sample、`vllm/model_executor/models/qwen3_vl.py`的视频metadata与时间戳处理、`transformers/models/qwen3_vl/video_processing_qwen3_vl.py`的smart_resize/sample_frames。网页工具本轮返回404，未声称在线核验最新版文档。
