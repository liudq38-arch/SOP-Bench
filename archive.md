# 已排除的线索与获取失败记录

- 医学图像配准、机器人力控、IMPACT-HOI/IMPACT-Scribe 等同名或近名工作不是本次三篇对照对象。
- 历史 SOP 项目中的 QIC 指标、约束图实验和“15 vs 1”等概括未直接作为论文结论使用；没有删除历史文件。
- web 搜索工具持续 HTTP 404，改用官方公开 API、官方网页和论文。
- arxiv.org 无版本 PDF 下载多次中断，随后经 export.arxiv.org 成功获取 EgoErrorVQA/IMPACT，通过正式 NeurIPS 地址获取 CC4D。
- `archive/failed_downloads/CC4D.pdf.part` 是未完成下载，不能用作论文；正式完整版本在 papers/CC4D_NeurIPS2024.pdf。
- raw.githubusercontent.com 部分正文下载不稳定，改用 GitHub Git Blob API 固定 commit 下载并校验哈希。
- IMPACT 下载曾遇到 CDN DNS/连接超时；最终常规镜像请求下载完成，校验匹配。诊断期间尝试公共 DNS 查询，不需要修改系统 DNS 配置；没有执行系统网络配置修改。
- 初次用 csv.DictReader 读 Assembly101 时发现源文件无表头，初步计数作废；改用固定 7 列 schema 的 csv.reader，允许末尾 remark 缺省，最终 3,964 行。最终报告使用修正后结果。


## v15未采用方案（2026-09-19）

- transition8减少token，但额外开发一致包含拾取证据不清，33回归有2冲突。初始Picture编号失败版本保留于outputs/impact_qa/gt_v15_tools/transition8_initial，未猜测ID。
- endpoint8与inventory8未可靠修复两个邻近工具混认，均有旧成功回退；端点高分辨率图仅作为有用审核资产保留。
- pairboard仅开发37一致/7弃答/2冲突，去掉中段信息后回退，不扩展到33回归。
- 本地Qwen3-VL-8B-Instruct相同10开发冒烟5一致/1弃答/4证据格式失败，部分失败响应还错认工具。未扩大、未放宽校验，停止任务自建8003服务释放GPU6。
- gt_v15_strategy_selection.json是开发后临时选型记录；跨视频回归揭示不足，最终由gt_v15_final_strategy.json的时间排序＋直接证据复查流程取代。全部原输出保留；详细依据见reports/impact_qa/gt_v15_results.md。
