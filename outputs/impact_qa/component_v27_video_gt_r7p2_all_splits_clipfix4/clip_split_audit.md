# Clip split audit: component_v27_video_gt_r7p2_all_splits_clipfix4

Minimum duration: **3.0s**. Raw clips: **765**; repaired clips: **652**; manifest clips: **648**.

| set | count | min (s) | median (s) | mean (s) | < minimum |
|---|---:|---:|---:|---:|---:|
| raw | 765 | 0.033 | 23.867 | 38.003 | 113 |
| repaired | 652 | 4.467 | 30.400 | 44.589 | 0 |
| manifest | 648 | 4.800 | 30.700 | 44.830 | 0 |

All repaired clips meet minimum: **True**; all manifest clips meet minimum: **True**.
Source-end cleanup tails excluded from manifest: **3**.
Assembly partition checks invalid: **0**.

## Thresholds for repaired manifest

```json
{
  "1": 0,
  "1.5": 0,
  "2": 0,
  "3": 0,
  "5": 2,
  "10": 46,
  "15": 136,
  "30": 320,
  "60": 537
}
```

## Coverage

```json
{
  "event_coverage_raw_manifest": {
    "total": 12163,
    "fully_contained": 9984,
    "partial_only": 953,
    "not_overlapped": 1226
  },
  "event_coverage_repaired_manifest": {
    "total": 12163,
    "fully_contained": 10025,
    "partial_only": 900,
    "not_overlapped": 1238
  },
  "error_coverage_raw_manifest": {
    "total": 1674,
    "fully_contained": 1391,
    "partial_only": 150,
    "not_overlapped": 133
  },
  "error_coverage_repaired_manifest": {
    "total": 1674,
    "fully_contained": 1397,
    "partial_only": 144,
    "not_overlapped": 133
  }
}
```
