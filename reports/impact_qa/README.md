# IMPACT 异常理解 QA 试制工作区

本轮使用第一视角 RGB 和 v1.1 标注。所有自动候选均待人工审核；模型自审通过不代表人工验证、真实正确率或正式基准。

## 数据与研究

- [EgoErrorVQA 生成流程及迁移差异](egoerrorvqa_generation.md)
- [下载校验](download_validation.json)：已复用并校验 ego 包，112 个视频在 `/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/ego`，项目 `datasets/impact` 为索引符号链接。
- [事件预检](precheck.json)：20 开发、60 试制，共 80 不同执行；采样种子 20260918。
- [标注交叉检查](annotation_crosscheck.json)：PPR 一致；ATR 合并段与原子动作、TAS-S 与 TAS-B 的不同粒度不混用。
- [抽帧预检](evidence_precheck.json)：80 段审阅视频、1,392 帧初始证据。

## 服务与复跑

所有命令从 `/home/ldq/project/sop` 执行。模型权重使用已有 `/data_1/ldq/models/Qwen3.5-27B`。依赖锁见 `environment.lock.txt`；vLLM 0.18.0，torch 2.10.0+cu129，Transformers 4.57.6。不要在旧 sop 环境覆盖安装。

```bash
bash scripts/start_impact_vllm.sh
```

默认服务只监听本机 8000，GPU 默认 0、1；可通过 `IMPACT_GPU_IDS` 与 `IMPACT_API_PORT` 设置。双卡 BF16，TP=2，上下文 32768、max_num_seqs=4，禁用 thinking，每服务 API 并发 4。生成调用 temperature=0.1、top_p=0.8、max_tokens=2048、seed=20260918；它们是本试制设置，并非原论文生成参数。脚本只为服务加载 Conda 的 C++ 库以避免 SQLite 动态库不匹配。

```bash
.venv-impact/bin/python scripts/smoke_impact_service.py
python scripts/prepare_impact_qa.py
python scripts/audit_impact_event_labels.py
python scripts/prepare_impact_evidence.py
.venv-impact/bin/python scripts/run_impact_qa.py --split development --version v1
python scripts/summarize_impact_run.py --split development --version v1
```

开发阶段完成后，以最终冻结提示词版本运行 pilot，再导出审阅包；最终版本号以 `prompt_iterations.md` 为准。不可在未知版本冻结状态下把开发与试制重新混合调参。

每阶段缓存位于 `outputs/impact_qa/api_cache`；完整运行记录在 `outputs/impact_qa/runs/<version>/<split>`。请求失败重试最多三次，成功输出可恢复；重新运行同样参数不会重复调用已有成功请求。观察缓存不包含错误标签；生成事实对照阶段可访问参考标签，导出的 evaluation_inputs 不包含答案。

## 人工审核

生成完成后，打开 `outputs/impact_qa/review/index.html`。每项可查看目标视频、目标时间、目标手、帧证据、来源标注、提示词和自动意见，填写 accept/edit/reject 及理由，然后导出 `impact_human_reviews.json`。默认决策始终 pending_human_review。

如浏览器不支持本地视频相对路径，可从项目根运行：

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory outputs/impact_qa
```

再访问 `http://127.0.0.1:8765/review/`。编辑存储于浏览器 localStorage，需导出 JSON 才形成独立审阅文件。

```bash
python scripts/import_impact_reviews.py /path/to/impact_human_reviews.json --reviewer REVIEWER_ID
```

导入会检查 QA ID、提示词版本和来源 run hash，防止旧审核覆盖新题；修改和拒绝必须填写原因。只有人工提交接受的条目进入独立 human_accepted 输出，原始候选仍保留。

## 结果解释

类别题回答 phase 和全部适用的六类异常；不输出 A/B/C/D。normal/recovery 默认异常类型输出空列表，但原始向量仍保留在事件记录。类型 definitions 采用 IMPACT 原生含义，不假定设备说明书有未公布的明确阈值。

开放式问题围绕目标动作的执行理解。确切错误原因、标准工具、空间要求、操作活动时长和修复成功都必须有证据；标注区间秒数只是该动作段跨度。程序邻接是发生顺序，不能自动当作工程规范。

自动审核为同一模型独立调用，有共享偏差；最终机器通过率只能用于发现问题和安排人工审核，不能称为数据准确率。
