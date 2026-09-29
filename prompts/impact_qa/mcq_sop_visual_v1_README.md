# MCQ 片段视觉核验：Prompt 与输入约定

实际 system 原文：`mcq_sop_visual_v1_system.txt`；user 原文：`mcq_sop_visual_v1_user.txt`；输出合同：`mcq_sop_visual_v1_schema.json`。调用代码：`scripts/run_mcq_sop_visual.py`；完整配置：`configs/impact_qa/mcq_sop_visual_v1.json`。

## 路径占位符的本次填入

| 占位符 | 本次值 |
|---|---|
| DATA_ROOT | `/home/ldq/project/sop/annotations/impact/IMPACT-v1.1` |
| MCQ_PATH | `/home/ldq/project/sop/outputs/impact_qa/front_mcq_expansion_v1/questions.jsonl` |
| SOP_PATH | `/home/ldq/project/sop/outputs/impact_qa/mcq_sop_visual_v1/sop_reference.json` |
| VIDEO_ROOT | `/data_1/ldq/dataset/impact/IMPACT-v1.1/videos` |
| QWEN_ENDPOINT | `http://127.0.0.1:8000/v1`、`8001/v1`、`8002/v1` |

服务名 `impact-qwen38-27b`，本地权重 `/data_1/ldq/models/Qwen3.8_27B`。权重 config 实际声明 `Qwen3_5ForConditionalGeneration`，服务别名不是架构鉴定。

## User 模板如何填充

- `{SOP_JSON}`：按 Model-A / Model-B 及 assemble / disassemble 选一份完整 SOP，包括编号、稳定步骤 ID、连接前置、有条件换序组、部件工具和规则来源/未知边界。PSR 提供组件状态操作词表，没有官方依赖边；不将其重建为已获官方认证的唯一路线。
- `{CASE_JSON}`：当前 clip 时长、目标手、目标区间、阶段候选所需部件/工具、整个 clip 的左右手 TAS-B、去异常标签的 TAS-S 提示、图像时间表。所有模型可见时间使用完整 clip 起点后的秒数；目标不重新归零。动作与目标交集在 `target_overlap_s`。
- `{JSON_SCHEMA}`：完整输出合同；运行时加上合法 SOP ID、目标图帧号枚举及证据起止时间范围。服务端不支持的 `uniqueItems` 仅从 API 的解码约束中去掉；返回后仍按完整 schema 校验唯一性。
- user 文本后依次附：每帧的 `frame_index` / `clip_timestamp_s` / `role` 文本，以及该帧 `image_url` 的 JPEG base64 数据。最后重复本题硬时间范围和可引用帧号。不是把服务器本地路径交给模型。

每段少于 4 秒用 8 张目标图，4–20 秒用 12 张，20 秒及以上用 16 张，均匀采样目标内原始视频帧。段前后各最多两张（约 0.25 秒和 1 秒），超出 clip 的上下文不补造。图像最长边 960 像素，另加时间戳顶栏；服务图像像素预算上限 589824。长段可能存在较大的抽帧间隔，不能将间隔内状态视为已观察。

`temperature=0`、`top_p=1`、`seed=20260929`、`enable_thinking=false`、最多输出 1800 tokens、严格 JSON schema；每服务最多 8 个并发请求，3 服务共 24。解析/合同错误最多尝试 3 次，仍失败独立记录 `parse_failed`；API 错误与输入错误分别记录，不归为 normal。

不发送：原题问句、选项、答案、异常类别、异常/恢复相位、规则命中、旧模型判断、人工审核。题号与 trial ID 仅在输出/本地清单关联，模型不可见。schema 中列出所有候选类型只是定义输出空间，不是透露该题 GT。

`requests/*.json` 保存每条实际 system、展开后的 user、末尾时间提醒、图像路径及参数；`media/*/manifest.json` 保存源帧和 clip 时间映射；`raw_responses` 保存原响应。可由这些文件还原请求，无需在日志中重复保存大量 base64。

## 运行及断点续跑

在项目根目录执行：

```bash
.venv-impact/bin/python scripts/test_mcq_sop_visual.py
.venv-impact/bin/python scripts/run_mcq_sop_visual.py --prepare-only
.venv-impact/bin/python scripts/run_mcq_sop_visual.py --pilot --concurrency 1
.venv-impact/bin/python -u scripts/run_mcq_sop_visual.py --retry-failures
```

每段返回后立即原子写入 `results`。同一版本再次运行跳过成功项；`--retry-failures` 重试失败项。Prompt/代码/配置变更会触发版本保护，须另建输出版本或先将旧试跑结果移入 `revisions`；不得混合不同协议的输出。

## 输出解释

`kept_questions.jsonl` / `discarded_questions.jsonl` 保留原题全部字段并增加 `filter`；后者包括主原因和逐段问题。多段题任一段不合格则整题剔除。本次库只含单目标题，但过滤器也覆盖多段输入。

`verification_results.jsonl` 每段一行；成功项含用户指定的 10 个判断字段及 question/trial/segment ID、状态、模型版本、采样和请求信息。`normal_but_gt_anomaly.jsonl` 仅列原 GT 异常但模型判 normal 的项，不把无 GT 异常的规则候选混入冲突统计。`filter_statistics.json` 含逐类型/逐 trial/逐来源保留率；多标签题在各相关类型中分别计数，类型计数之和不等于题数。

`operational` 是这次模型输出的执行缺陷类别，与旧题库 `handling` 对照分析；`redundant` 为新增观察维度，不写入原六类标注。模型置信度不是实测准确率，核验结果须保留人工复核入口。
