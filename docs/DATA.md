# 数据准备

本仓库**不含**视频、第三方标注与论文原文（体积大且各有独立许可）。请按下表自行获取。

## 1. IMPACT（主数据源）

- 官方地址：<https://github.com/impact-handover/impact>
- 需要的内容：
  - 视频：`IMPACT-v1.1-videos-ego.zip` / `IMPACT-v1.1-videos-front.zip`
  - 标注：`annotations/` 下的 TAS-B、TAS-S、ATR、PPR、PSR、ASR
- 建议落盘位置（与项目约定一致）：

```
/data_1/<user>/dataset/impact/IMPACT-v1.1/
├── videos/{ego,front}/*.mp4
└── annotations/{TAS-B,TAS-S,ATR,PPR,PSR,ASR}/...
```

- 建立软链供脚本使用：

```bash
mkdir -p datasets
ln -s /data_1/<user>/dataset/impact/IMPACT-v1.1 datasets/impact
```

- 校验：

```bash
python scripts/validate_impact.py
```

## 2. CaptainCook4D

- 官方地址：<https://captaincook4d.github.io/captain-cook/>
- 本仓库已内置其官方标注子集于 `cc4d_annotations/`（MIT 许可），**视频需自行下载**。
- 校验：

```bash
python scripts/validate_annotations.py
```

## 3. EgoErrorVQA

- 官方仓库：<https://github.com/z1oong/EgoErrorVQA>
- 仅需标注 JSON（问题、选项、真值、视频时间戳），视频按官方说明获取。

## 4. EgoOops / EPIC-Tent / Assembly101

横向对照用，均为公开数据集，按各自官方页面下载标注即可。

## 5. 论文

调研引用的论文 PDF 未随仓库分发。需要时从 arXiv / 会议官网获取，清单见 `research.md` 的参考文献部分。

## 6. 模型权重

推理与生成使用 Qwen3-VL / Qwen3.5 系列多模态模型，通过 vLLM 提供服务。权重需自行下载，仓库不含。

参考启动方式（多实例、每实例双卡）：

```bash
# 具体参数见 scripts/ 下的服务启动脚本与 configs/impact_qa/*.json
```

## 7. 环境自检

```bash
python scripts/preflight.py     # 检查依赖、路径、GPU、端口
```

若预检报缺失，按输出提示补齐；不要跳过预检直接跑批处理。
