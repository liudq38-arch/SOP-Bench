# MCQ时长过滤与SOP盲视觉核验

输入 1977；保留 1196；丢弃 781；丢弃原因 {'too_short': 781}。
已返回 8/1196，有效JSON与证据合同通过 8，待处理 1188。
Verdict: {'insufficient_evidence': 5, 'normal': 3}
模型异常类型: {'none': 8}
执行失败: {}
GT异常但模型normal: 2，详见normal_but_gt_anomaly.jsonl。

## 过滤后的类型构成

| GT类型 | 总数 | 保留 | 保留率 |
|---|---:|---:|---:|
| handling | 322 | 256 | 79.50% |
| no_GT_anomaly | 168 | 114 | 67.86% |
| procedural | 266 | 201 | 75.56% |
| spatial | 671 | 254 | 37.85% |
| temporal | 861 | 652 | 75.73% |
| wrong_part | 42 | 31 | 73.81% |
| wrong_tool | 64 | 46 | 71.88% |

低保留率提示：[{'type': 'spatial', 'gap_pp': -34.905277384173345, 'statistically_flagged_bonferroni': True, 'p_approx': 1.8831337020701922e-48}]
practical flag >=10 percentage points below questions without that type; exploratory two-proportion normal approximation with Bonferroni 6, not cluster-adjusted by trial

## 判定边界

GT异常和规则候选分开统计；所有原短标注保留计数。模型未接收原题、GT答案、异常类型、相位、旧审核或规则命中。输入包含有证据边界的SOP、显式换序组/连接前置、候选步骤部件工具、clip完整双手TAS-B、去标签的TAS-S提示和逐帧时间。PSR的51条状态操作不能独立构成偏序图，未伪造为官方依赖。
operational是本次输出类别，对应官方handling作分析；redundant是额外核验维度，未写回数据集。单一主因不等于官方多标签全量预测。confidence是模型自评，不是校准准确率。
normal仅表示给定目标的可见抽帧未见异常且支持合法动作，不证明整段连续视频/未采样时刻都正常。没有状态推进的判断必须有连续尝试证据，不能仅凭长间隔图像相似。
结果是待人工复核的模型意见；没有修改原MCQ、标注、审核记录或数据集。
