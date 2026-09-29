# 实际媒体与模型输入核查

核查对象：IMPACT v1.1 ego、当前本地 Qwen3.5-27B。本报告区分源视频、审阅片段、图片输入和原生视频输入，不能混用它们的帧数。

## 源视频

112 个 MP4，均为 MPEG-4 Part 2（ffprobe codec_name=mpeg4）、1920×1080，avg_frame_rate=24917/1000（24.917 FPS）。完整录制长度 105.470–1027.010 s，中位数 201.308 s；帧数 2628–25590，中位数 5016。逐文件信息及 packet PTS 保存在 media/*.json。

TAS-B 动作段起止帧按包含右端点解释，结束秒数使用下一帧 PTS（末尾则视频时长）。因此段跨度不是实际持续施力、旋转等活动时间；不使用固定 25 FPS 简单除法替代实际时间轴。

## 本次 80 个事件（不是全库时长分布）

| 划分 | 数量 | 最短目标段/s | 中位数/s | 最长/s | 短于 2 s | 短于 5 s |
|---|---:|---:|---:|---:|---:|---:|
| development | 20 | 0.642132 | 2.086929 | 13.725569 | 10 | 15 |
| pilot | 60 | 0.642132 | 1.504997 | 18.782357 | 34 | 51 |

全部 80 事件来自不同原始执行。审阅片段额外保留前后各 3 s，因此审阅视频 development 为 6.642–19.726 s，pilot 为 6.642–24.782 s；这些上下文不等于目标动作本身。

## 已运行的图片输入

v1/v2：上下文±3 s、均匀最多 24 张 JPEG，宽 672；短段约 2 帧/s，长段受 24 帧上限影响更稀疏。初始 80 事件总计 1392 图。

v3：目标段 8–16 图，前后上下文各至多 4 图，总数不超过 24，显式 TARGET/CONTEXT 标记。避免引用段外，但目视复核仍发现误读。

v4/v5：仅目标段，均匀 12 个全帧（896×504），其中 4 时刻再从原视频提取局部图（归一化 x=.05,y=.25,w=.9,h=.75，缩放宽 1024，保留宽高比）。每事件 16 张 JPEG，只有 12 个不同采样时刻。API 为多个 image_url，不是原生 video_url。局部图未创造新的时间信息。精确抽帧定位仍有一源帧左右的取整边界。

## 原生视频对照中的真实帧数陷阱

三段 target-only MP4 重新编码为 H.264、1024×576、24.917 FPS、无音频。原始请求只设置 mm_processor_kwargs.num_frames=16，没有设置解码器 media_io_kwargs。

| 目标段时长/s | MP4 帧数 | vLLM 默认解码帧数 | HF 是否再采样 | 实际视觉帧数（含 temporal padding） | 视频 token |
|---:|---:|---:|---|---:|---:|
| 0.722398 | 18 | 18 | 是 | 16 | 4608 |
| 1.083598 | 27 | 27 | 是 | 16 | 4608 |
| 3.170526 | 79 | 32 | 否 | 32 | 9216 |

已通过本机 vLLM 0.18.0 VideoMediaIO 和模型随附 Qwen3VLVideoProcessor 复算，不是仅从 token 猜测。证据：native_decoder_check.json、native_processor_check.json。原因：解码器默认 num_frames=32；长片已预采样，metadata.do_sample_frames=false，后续 num_frames=16 不再执行。短片完整解码后再由处理器采为 16。

本地实现依据：`.venv-impact/lib/python3.12/site-packages/vllm/multimodal/media/video.py` 和 `vllm/model_executor/models/qwen3_vl.py`；处理器 temporal_patch_size=2，因此 grid_t=8 对应 16 个视频帧，不能把 grid_t 当实际帧数。

## v6 验证方案

原生目标段视频 + 4 张同时间局部图；请求同时设置：

```json
{
  "media_io_kwargs": {"video": {"num_frames": 16, "fps": -1}},
  "mm_processor_kwargs": {"num_frames": 16, "do_sample_frames": false}
}
```

先在解码层显式选 16 帧，再禁止隐式二次抽帧。这 16 个视频时刻和 4 个裁剪时刻可能不同，因此不能统称为 20 个独立视频帧。原生 video token 与 image token 分别计入总上下文，统一 32768 token 限额。首 10 事件解码预检见 v6_native_precheck.json；是否作为最终版本以 prompt_iterations.md 的冻结记录为准。

没有把整条几分钟录制送入当前单动作 QA 生成器。原生视频改善个别难例不等于所有微动作可识别；后续比较须固定片段、解码帧数与输出协议。
