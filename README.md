# SOP-Bench

面向**装配流程视频**的标准作业流程（SOP）一致性核验与**流程异常理解**基准。

本仓库把「视频动作标注 → SOP 约束图 → 异常理解 QA」组织成一条可复现的流水线：从公开装配/操作数据集的逐帧标注出发，反推各类异常的判定规则，再据此生成多层次的问答基准（封闭多选 + 开放问答），并附带人工审核台与评测器取证工具。

> 状态：研究进行中。数据集构建、规则反推与审核工具均已落地；部分结论仍待真人逐题签署。

---

## 1. 研究问题

现有流程视频 QA 基准存在两类系统性缺陷：

- **异常类别分布失衡**：多数基准的「错误」样本高度集中于少数显性类别（如取错零件、用错工具），而 **顺序错误（Order Error）** 与 **缺步（Missing Step）** 在封闭式多选题中被结构性忽略——模型即使完全不看图，仅靠语言先验也能拿到虚高分数。
- **证据供给与判定混杂**：开放问答缺乏细粒度定位证据，封闭问答缺乏过程性理由。

本仓库的出发点是：**先把每一类异常的判定规则从原始标注里反推清楚**，再让规则去驱动出题、审核与评测。判定层（逐帧/分段告警）不直接产生分数，而是作为理解层（QA）的**证据供给器**。

## 2. 数据来源

| 数据集 | 角色 | 提供内容 |
|---|---|---|
| [IMPACT](https://github.com/impact-handover/impact) | **主数据源** | 装配/拆卸执行视频（ego + front 双视角）、TAS-B/TAS-S 工序标注、ATR/PPR 逐帧异常标注、PSR 零件状态 |
| [CaptainCook4D](https://captaincook4d.github.io/captain-cook/) (CC4D) | 方法对标 | 4D 流程错误标注、任务图、错误类别定义 |
| [EgoErrorVQA](https://github.com/z1oong/EgoErrorVQA) | 评测对标 | 多选/开放两类协议、9 类封闭标签、人评 `Sim.` 指标 |
| EgoOops / EPIC-Tent / Assembly101 | 横向对照 | 错误片段标注与 QA 对 |

数据本体（视频、第三方标注、论文 PDF）**不随仓库分发**，请按 [`docs/DATA.md`](docs/DATA.md) 自行下载。仓库仅包含代码、配置、提示词、文档，以及我们自建的数据集产物。

## 3. 目录结构

```
.
├── impact_qa/            # 核心库：I/O、媒体采样、标注适配、QA 生成、审核协作、页面
├── scripts/              # 可执行入口：校验、构建、批处理、导出、服务启动
├── configs/              # 版本化配置（生成策略、媒体采样、模型参数）
├── prompts/              # 版本化提示词（观察 / 事实对照 / 生成 / 审核）
├── tests/                # 契约与回归测试
├── utils/                # 共享工具（读取、哈希）
├── apps/                 # 可离线打开的数据浏览器（3D 装配 / 视频对照）
├── reports/              # 校验报告、统计、审计记录（JSON + Markdown）
├── outputs/impact_qa/    # 自建数据集产物（JSONL 本体 + 逐条目记录）
├── cc4d_annotations/     # CaptainCook4D 官方标注镜像（MIT）
├── research.md           # 文献综述与证据链
├── plan.md               # 执行计划与数据流
├── experiment_log.md     # 环境与执行记录
└── archive.md            # 已排除线索与失败记录
```

## 4. 核心组件

### 4.1 异常判定规则（异常标注规则反推）

逐类反推 IMPACT 原生六类异常的可操作判据，并给出支撑证据与反例：

- **temporal** — 序列接缝判据：手持待装件却不进入安装动作，且前序动作为「取件」且持续 ≥3s。
- **wrong_tool** — 工具—工具 / 工具—手关系错位：该用 A 工具却持 B 工具，或用手指替代规范工具。
- **wrong_part** — 部件身份错配。
- **handling / spatial / procedural** — 见 `reports/impact_qa/` 下的审计记录。

官方六类定义、工具外观与规范工具映射（改锥颜色 ↔ 驱动类型）见 `reports/impact_qa/`。

### 4.2 QA 生成流水线

```
原始标注 ──► 逐执行视频隔离的事件清单 ──► 帧证据采样 ──► 无异常标签观察
        ──► 标注事实对照 ──► QA 生成 ──► 独立自动复核 ──► 审核页面 / JSONL / CSV
```

- 每阶段输出带缓存键（样本 + 模型配置 + 权重哈希 + 提示 + 媒体采样配置）。
- 冻结（`frozen.json`）后单次试制；配置、提示、源码哈希一并入冻结记录。
- 支持恢复：逐请求落盘，失败显式记录，不静默跳过。

### 4.3 审核台

`impact_qa/front_mcq_page.py` 提供 Gradio 逐题审核界面：播放定位窗口、显示题目与候选异常类型、填写视觉依据、多人协作台账（`claims.json` + `collaborative_reviews.jsonl`，含 revision 指纹与一致性达成）。

### 4.4 媒体采样与算力预算

长视频送 VLM 的实测结论（见 `reports/`）：

- **帧数几乎不占 token**，`video_pixel_budget` 才决定上下文占用（`tok ≈ budget / 2048`）。
- 因此保 2fps 是可行的，成本旋钮应作用于像素预算而非抽帧密度。
- 降级顺序：`pixel_budget ↓ → 并发 ↓ → 最后才降 fps`。
- 抽帧应在**离线**用 ffmpeg 预抽成小 mp4；让 VLM 端从 30fps 原片现抽会慢 6–7 倍。

## 5. 快速开始

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt      # 按需，仅生成/审核部分需要

# 1) 环境与数据预检
python scripts/preflight.py

# 2) 校验本地数据标注
python scripts/validate_impact.py

# 3) 启动审核台（默认端口 7863）
python scripts/serve_component_v27_review.py
```

模型推理依赖 vLLM 与多模态模型（Qwen3-VL / Qwen3.5 系列），需自行准备权重与显存；仓库不包含权重。

## 6. 复现约定

- 单一事实来源是**原始标注**；论文中的描述仅作背景，冲突时以标注为准。
- 每个实验目录保留 `frozen.json`（配置 + 提示 + 源码哈希）与审计记录。
- 中间产物按版本分目录（`*_v1`, `*_clipfix4`, …），不覆盖历史，便于回溯。
- 生成侧自动复核**不替代**人工签署。

## 7. 许可与引用

- 本仓库代码与文档：许可尚未确定（暂未附加 `LICENSE` 文件，公开引用前请先确认）。
- `cc4d_annotations/` 来自 CaptainCook4D 官方仓库，遵循其 MIT 许可（见该目录下 `LICENSE`）。
- 引用的数据集与论文版权归各自作者所有，仓库不再分发其原始媒体与 PDF。
