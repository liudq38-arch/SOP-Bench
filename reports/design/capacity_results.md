# Qwen3-VL-8B 单卡合成视频容量实测

日期：2026-09-18。单 GPU，BF16，FlashAttention2，batch=1，每帧 384×672，禁止自动缩小；短提示，生成 32 token。Torch 2.9.1+cu128、Transformers 4.57.6。视觉 patch 卷积改为同权重线性运算，16 个 BF16 patch 对照最大绝对差 0.00390625；没有宣称逐 bit 相同。

| 帧数 | 视觉 token | 总输入 token | 峰值 allocated GiB | 峰值 reserved GiB | 推理秒 | 状态 |
|---:|---:|---:|---:|---:|---:|---|
| 32 | 4032 | 4181 | 17.51 | 17.80 | 2.56 | ok |
| 64 | 8064 | 8357 | 18.67 | 19.19 | 2.98 | ok |
| 128 | 16128 | 16709 | 20.99 | 21.96 | 4.83 | ok |
| 256 | 32256 | 33441 | 25.63 | 27.52 | 9.39 | ok |
| 512 | 64512 | 66977 | 34.93 | 38.63 | 22.13 | ok |
| 768 | 96768 | 100513 | 44.24 | 46.54 | 39.97 | ok |

allocated 表示 PyTorch 活跃张量峰值；reserved 包含分配器保留内存，两者不能相加；CUDA 上下文等显存还可能不计入这些统计。CUDA 可见总显存 47.40 GiB。768 帧配置已接近容量边缘，增加分辨率、文本、裁剪、输出或批量会改变结果。

这只证明测试形状可运行，未穷举最大可用帧数。合成噪声不是 EgoErrorVQA 视频，不产生任何任务准确率结论。时间不含媒体解码和处理器步骤，也不含首次模型加载。生成 32 token 的测试不能直接当作生成 512 token 的完整任务基准。

首次原始 Conv3d 32 帧路径为 130.53 秒、allocated 17.51 GiB；原始后续探测因性能问题主动终止。优化探索轮发生过进程重叠，其延迟不用于此表。最终表来自确认停止后独立运行的 [JSONL](qwen3vl_profile_isolated.jsonl)。

复现：

```bash
/home/ldq/miniconda3/envs/sop/bin/python scripts/profile_qwen3vl_video.py --linear-patch --frames 32 64 128 256 512 768 --output reports/design/qwen3vl_profile_isolated.jsonl
```

脚本会跳过同输出文件中已成功的相同配置；重新计时时使用新的输出路径。
