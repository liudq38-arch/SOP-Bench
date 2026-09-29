# 资产清单与下载范围

首轮核查日期：2026-09-17，媒体增补：2026-09-18。根目录 `/home/ldq/project/sop`。首轮仅获取论文/标注；用户后续授权 QA 试制后，已复用并验证 IMPACT ego 媒体。下方原首轮尚未获取状态需结合本段更新阅读。

**IMPACT 媒体更新：** ego 压缩包 `/data_1/ldq/dataset/impact/downloads/v1.1/videos/IMPACT-v1.1-videos-ego.zip` 已完成，15,323,188,764 bytes，官方 SHA-256 和 ZIP CRC 通过；112 个视频解压到同数据根的 `IMPACT-v1.1/videos/ego`，`datasets/impact` 为项目入口符号链接。详见 [下载校验](impact_qa/download_validation.json)。用户另外运行的其他视角/模态下载独立继续，其完成状态不混入本轮 ego 验收。现有模型权重复用，未新增下载。

## 1. 可直接使用的标注

| 资产 | 本地路径（相对根目录） | 规模/体积 | 版本、来源与状态 |
|---|---|---|---|
| CC4D 步骤、错误、图和划分 | `cc4d_annotations/` | 非 Git 资产 7,738,304 bytes，约 7.38 MiB | 复用既有文件；提交 a8a920a；与历史副本逐文件哈希一致，官方 HEAD 相同 |
| EgoErrorVQA 发布标注 | `annotations/egoerrorvqa/` | 9 JSON，2,558,258 bytes，约 2.44 MiB | 新下载；提交 5403cdd；全部 Git blob hash 校验通过 |
| IMPACT 标注压缩包 | `annotations/impact/IMPACT-v1.1-annotations.zip` | 8,485,262 bytes，约 8.09 MiB | 新下载；v1.1；SHA-256/ZIP CRC 通过 |
| IMPACT 解压目录 | `annotations/impact/IMPACT-v1.1/` | 7,216 文件，458,673,739 bytes，约 437.43 MiB | 包含逐帧标签导致解压体积较大，不含大型媒体 |
| EgoOops 原始标注 | `annotations/egooops_upstream/` | 9 文件，172,305 bytes | 新下载；提交 ec0746d；50 videos / 538 segments |
| Assembly101 错误标注包 | `annotations/assembly101_mistake_annotations.tar.gz` | 47,204 bytes | 新下载；提交 6f3a953；完整 mistake benchmark，不是完整细动作标注 |
| Assembly101 错误标注目录 | `annotations/assembly101_mistake_upstream/assembly-101-assembly101-mistake-detection-6f3a953/` | 328 CSV，3,964 条记录 | 实際目录名以解压结果为准；无表头 CSV |
| EPIC-Tent 原始标注包 | `annotations/epic_tent_upstream.tar.gz` | 3,307,801 bytes，约 3.15 MiB | 新下载；提交 1e784a9；完整官方 annotation 仓库 |
| EPIC-Tent 标注目录 | `annotations/epic_tent_upstream/youngkyoonjang-EPIC_Tent2019-1e784a9/` | 35 文件，15,435,890 bytes；29 人 | 1,261 条动作、626 条错误、29 份逐帧动作标签 |

权威入口：[CC4D](https://github.com/CaptainCook4D/annotations)、[EgoErrorVQA](https://github.com/z1oong/EgoErrorVQA)、[IMPACT](https://huggingface.co/datasets/KratosWen/IMPACT)、[EgoOops](https://github.com/Y-Haneji/EgoOops-annotations)、[Assembly101 mistake](https://github.com/assembly-101/assembly101-mistake-detection)、[EPIC-Tent](https://github.com/youngkyoonjang/EPIC_Tent2019)。

### EgoErrorVQA 文件角色

| 文件 | 用途 |
|---|---|
| `captaincook4d_qa_pairs_updated.json` | CC4D 开放题：960 片段、1,857 QA |
| `assembly101_qa_pairs_updated.json` | Assembly101 开放题：446 片段、859 QA |
| `egooops_qa_pair.json` | EgoOops 开放题：215 片段、418 QA |
| `epic_tent_qa_pair.json` | Tent 开放题：184 片段、426 QA |
| `captaincook4d_answer.json` | CC4D 选择题：1,000 样本 |
| `assembly101_answers.json` | Assembly101 选择题：460 样本 |
| `egooops_answer.json` | EgoOops 选择题：215 样本 |
| `epic_tent_answer_sec.json` | Tent 选择题：182 样本 |
| `procedure.json` | 31 个 task_id 对应程序文本 |

共同的核心字段是 `video_id / task_id / start_time / end_time`，开放题附 `qa_pairs`，选择题附 `close_end_answer`，各来源的原生字段保留。`close_end_answer` 可能是字符串或列表。时间为派生秒字段，但部分异常或漏步条目不可直接用于裁剪。

### IMPACT 文件入口

- `annotations/TAS-S/{ego,front,left,right,top}/`：粗步骤 JSON，字段 `video_id, meta_data, segments`，段内 `f_start/f_end/label`。
- `annotations/TAS-B/{ego,front,left,right,top}/`：双手 JSON，段内 `start_frame/end_frame/action_label/verb/noun/entity/phase/anomaly_type`。
- `annotations/AF-S/annotations/`：短期预测使用的派生标注。
- `annotations/ASR/annotations/`：92 个 front 状态序列，`state_sequence` 和 17 部件字典。
- `annotations/ASR/splits/`：实际 64/10/18 的 S1 分区。
- `annotations/PSR/labels/`：完成事件字典、按分区组织的 CSV；应区分 `PSR_labels.csv`、`PSR_labels_raw.csv`、`PSR_labels_with_errors.csv`。
- `annotations/PPR/`、`annotations/ATR/`：逐帧阶段标签、多标签异常目标、mask、split 等。
- `metadata/NASA_TLX_anonymized.xlsx`：工作负荷问卷；本次未解读。
- `annotations/release_audit_v1.1.json`：作者发布的边界和字段修订日志。

另下载了 GitHub 的图/方法快照到 `sources/impact_code/`。特别注意其中 `procedure_graph.json` 是挖掘图，不是另一份人工标注真值。

## 2. 哈希及可复跑核验

- [CC4D 全文件哈希及历史一致性](cc4d_asset_manifest.json)
- [EgoErrorVQA 下载 URL、commit、SHA-256](ego_download_manifest.json)
- [IMPACT 下载与校验结果](impact_download_manifest.json)
- [EgoOops 下载清单](egooops_download_manifest.json)
- [Assembly101 下载清单](assembly_download_manifest.json)
- [EPIC-Tent 下载清单](epictent_download_manifest.json)
- [全部论文与文档快照哈希](source_asset_manifest.json)

IMPACT 原始地址为 Hugging Face，实际通过 `hf-mirror.com` 同路径镜像传输；大小和 SHA-256 与该发布的 `MANIFEST.tsv`、`SHA256SUMS`、LFS oid 一致。保留了这些清单到 `sources/impact_manifest.txt`、`sources/impact_checksums.txt`、`sources/hf_mirror_tree.txt`，未执行完整数据下载器。

在根目录可复跑：

```bash
python scripts/preflight.py
python scripts/validate_annotations.py > reports/annotation_validation.log
python scripts/validate_impact.py > reports/impact_validation.log
python scripts/validate_upstream.py > reports/upstream_validation.log
```

`python scripts/fetch_ego_annotations.py` 可基于已保存的官方 tree/commit 重新获取 VQA JSON，并对已有完整文件做哈希检查。所有核验都是 CPU 工作，不需要 torch。

## 3. 论文与来源快照

| 本地论文 | 原始来源 | 版本 |
|---|---|---|
| `papers/EgoErrorVQA.pdf`、`EgoErrorVQA_pdf.txt` | [arXiv 2608.24134](https://arxiv.org/abs/2608.24134) | v1，20 页；另有 HTML 抽取文本 EgoErrorVQA.txt |
| `papers/CC4D_NeurIPS2024.pdf`、同名 txt | [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/file/f4a04396c2ed1342a5d8d05e94cb6101-Paper-Datasets_and_Benchmarks_Track.pdf) | 正式会议版，54 页 |
| `papers/IMPACT.pdf`、`IMPACT_pdf.txt` | [arXiv 2604.10409](https://arxiv.org/abs/2604.10409) | v1，9 页；另有 HTML 抽取文本 IMPACT.txt |

CC4D 的辅助 HTML 为 v3，另保留 `papers/CC4D_v3.txt`；最终数值优先正式会议 PDF。不要将早期辅助版本无标识地覆盖成 v4。

`reports/*first10.json` 保存各主要输入的前 10 条示例。`reports/data_audit.md` 集中记录实际问题；统计中没有修改源文件。

## 4. 尚未获取或不在本次范围的内容

| 内容 | 状态与获取入口 |
|---|---|
| CC4D 大型数据 | 未下载；后续可用[官方 downloader](https://github.com/CaptainCook4D/downloader)选择录制与分辨率。EgoErrorVQA 示例使用 GoPro 360p |
| CC4D 10K 细粒度动作标注 | 论文声称有；本次 annotations 仓库内未定位到独立文件，状态是“未取得”，不是断言不存在 |
| EgoErrorVQA 媒体 | 未下载；Tent 只需 02/04/05/06；Assembly101 默认 e3，缺失时 e4，文件名以官方 README 为准 |
| IMPACT videos/depth/audio/gaze/features/sample | 首轮未下载；9 月 18 日 ego 已校验并解压（见上方更新）。其他视角/模态为用户另起下载任务，sample 已由该任务获取，本轮未重复下载 |
| Assembly101 全量细动作/粗动作标签 | 本次获取的是 mistake detection 标签；[完整标注仓库](https://github.com/assembly-101/assembly101-annotations)提供 Google Drive 链接，未额外拉取全部版本 |
| 模型权重 | 全部未下载；包括 VQA 两个裁判模型 |
| QIC 历史媒体 | 本次未读取/下载；历史脚本中的路径只作线索，不能据此声称媒体已核验可用 |

## 5. 许可信息（仅记录官方发布说明）

- CC4D 项目页说明 Apache-2.0。
- IMPACT 数据/文档 CC BY-NC-SA 4.0；官方新写的软件 Apache-2.0，第三方实现按各自许可。
- EgoOops CC BY-SA 4.0。
- Assembly101 CC BY-NC 4.0。
- EgoErrorVQA 当前仓库树未发现单独 LICENSE；文章的 CC BY-SA 4.0 不自动说明所有代码和派生数据的再分发条款。
- EPIC-Tent 当前 annotation 仓库树未发现单独 LICENSE；使用范围需查[原始发布页](https://data.bris.ac.uk/data/dataset/2ite3tu1u53n42hjfh3886sa86)，本次未将其认定为无条件再分发。
