# 全库问句形式与特征统计

Deterministic question-text feature coding, multi-label and not an official/manual semantic taxonomy. Counts refer to question wording, not error-type frequencies or correctness. Answer content and source labels are not used for question-feature assignment.

| 来源 | 片段 | QA | 唯一问句 |
|---|---:|---:|---:|
| CC4D | 960 | 1857 | 1143 |
| Assembly101 | 446 | 859 | 352 |
| EgoOops | 215 | 418 | 147 |
| EPIC-Tent | 184 | 426 | 105 |

| 非互斥文本特征 | 全库 | CC4D | Assembly101 | EgoOops | EPIC-Tent |
|---|---:|---:|---:|---:|---:|
| correctness_words | 1459 (40.98%) | 544 (29.29%) | 505 (58.79%) | 183 (43.78%) | 227 (53.29%) |
| attachment_installation | 1051 (29.52%) | 10 (0.54%) | 760 (88.47%) | 33 (7.89%) | 248 (58.22%) |
| explicit_step_completion | 124 (3.48%) | 36 (1.94%) | 68 (7.92%) | 0 (0.0%) | 20 (4.69%) |
| result_or_extent | 545 (15.31%) | 206 (11.09%) | 266 (30.97%) | 12 (2.87%) | 61 (14.32%) |
| omission | 87 (2.44%) | 7 (0.38%) | 70 (8.15%) | 0 (0.0%) | 10 (2.35%) |
| unnecessary_action | 104 (2.92%) | 15 (0.81%) | 81 (9.43%) | 0 (0.0%) | 8 (1.88%) |
| before_after_context | 658 (18.48%) | 469 (25.26%) | 10 (1.16%) | 45 (10.77%) | 134 (31.46%) |
| explicit_order_sequence | 36 (1.01%) | 7 (0.38%) | 9 (1.05%) | 18 (4.31%) | 2 (0.47%) |
| normative_order_explicit | 24 (0.67%) | 5 (0.27%) | 9 (1.05%) | 9 (2.15%) | 1 (0.23%) |
| error_diagnosis | 424 (11.91%) | 170 (9.15%) | 95 (11.06%) | 63 (15.07%) | 96 (22.54%) |
| tools_explicit | 69 (1.94%) | 63 (3.39%) | 0 (0.0%) | 6 (1.44%) | 0 (0.0%) |
| quantity_measurement | 249 (6.99%) | 233 (12.55%) | 0 (0.0%) | 16 (3.83%) | 0 (0.0%) |
| duration_temperature | 207 (5.81%) | 203 (10.93%) | 0 (0.0%) | 4 (0.96%) | 0 (0.0%) |
| location_orientation | 212 (5.96%) | 10 (0.54%) | 94 (10.94%) | 36 (8.61%) | 72 (16.9%) |

## 句式

```json
{
  "how": 1,
  "polar": 2163,
  "what": 1325,
  "other": 5,
  "why": 66
}
```

## 示例索引

examples.json 保留每项每来源最多 5 个不同问句及原答案、原始标签、精确 JSON 索引；all_qa_coded.jsonl 保留全量逐题编码，可复核规则边界。
