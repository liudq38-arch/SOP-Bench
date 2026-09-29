import collections
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.assets import read_json, sha256


def inspect_cc4d():
    root = Path("cc4d_annotations")
    complete = read_json(root / "annotation_json/complete_step_annotations.json")
    errors = read_json(root / "annotation_json/error_annotations.json")
    valid = set(complete)
    rows = [dict(recording_id=rid, **step) for rid, record in complete.items() for step in record["steps"]]
    error_rows = [dict(recording_id=record["recording_id"], **step) for record in errors for step in record["step_annotations"]]
    categories = collections.Counter(error["tag"] for row in error_rows for error in row.get("errors", []))
    missing_times = [row for row in error_rows if row["start_time"] < 0 or row["end_time"] < 0]
    invalid_times = [row for row in error_rows if row["start_time"] >= 0 and row["end_time"] < row["start_time"]]
    repeated = {rid: len(rec["steps"]) - len({s["step_id"] for s in rec["steps"]}) for rid, rec in complete.items()}
    splits = {}
    for path in sorted((root / "data_splits").glob("*.json")):
        data = read_json(path)
        sets = {k: set(v) for k, v in data.items()}
        splits[path.name] = {
            "counts": {k: len(v) for k, v in data.items()},
            "duplicates": {k: len(v) - len(set(v)) for k, v in data.items()},
            "unknown_ids": sorted(set.union(*sets.values()) - valid),
            "overlap": {f"{a}/{b}": len(sets[a] & sets[b]) for a, b in itertools.combinations(sets, 2)},
        }
    manifest = []
    history_root = Path("/home/ldq/sop_work/cc4d_annotations")
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        digest = sha256(path)
        history = history_root / path.relative_to(root)
        manifest.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest, "matches_history": history.exists() and sha256(history) == digest})
    Path("reports/cc4d_asset_manifest.json").write_text(json.dumps(manifest, indent=2))
    Path("reports/cc4d_first10.json").write_text(json.dumps(error_rows[:10], ensure_ascii=False, indent=2))
    return {
        "recordings": len(complete),
        "activities": len({r["activity_id"] for r in complete.values()}),
        "persons": len({r["person_id"] for r in complete.values()}),
        "environments": len({r["environment"] for r in complete.values()}),
        "recording_is_error": dict(collections.Counter(str(r["is_error"]) for r in errors)),
        "complete_step_rows": len(rows),
        "error_annotation_rows": len(error_rows),
        "complete_has_errors_rows": sum(bool(r.get("has_errors")) for r in rows),
        "error_rows_with_tags": sum(bool(r.get("errors")) for r in error_rows),
        "error_tag_instances": dict(categories),
        "negative_time_rows": len(missing_times),
        "negative_time_tag_sets": dict(collections.Counter(str(sorted(e["tag"] for e in r.get("errors", []))) for r in missing_times)),
        "invalid_nonnegative_times": invalid_times,
        "recordings_with_repeated_step_id": sum(v > 0 for v in repeated.values()),
        "task_graphs": len(list((root / "task_graphs").glob("*.json"))),
        "splits": splits,
        "asset_bytes": sum(r["bytes"] for r in manifest),
        "all_assets_match_history": all(r["matches_history"] for r in manifest),
    }


def inspect_ego():
    root = Path("annotations/egoerrorvqa")
    procedures = read_json(root / "procedure.json")
    cc_ids = set(read_json("cc4d_annotations/annotation_json/complete_step_annotations.json"))
    result = {"procedure_count": len(procedures), "files": {}}
    totals = collections.Counter()
    union_videos = collections.defaultdict(set)
    for path in sorted(root.glob("*.json")):
        if path.name == "procedure.json":
            continue
        data = read_json(path)
        mode = "open" if "qa_pair" in path.name else "mcq"
        dataset = path.name.split("_qa")[0].split("_answer")[0]
        video_ids = {str(r["video_id"]) for r in data}
        union_videos[dataset].update(video_ids)
        keys = [(str(r["video_id"]), r["start_time"], r["end_time"]) for r in data]
        labels = collections.Counter()
        correct = 0
        for row in data:
            if mode == "mcq":
                value = row["close_end_answer"]
                normalized = value if isinstance(value, list) else [value]
                labels.update(normalized)
                correct += any(v.lower() == "correct" for v in normalized)
            else:
                correct += not bool(row["is_error"]) if "is_error" in row else row["error_label"] == "correct"
        qa_count = sum(len(r.get("qa_pairs", [])) for r in data)
        entry = {
            "mode": mode, "clips": len(data), "qa_pairs": qa_count,
            "correct_clips": correct, "error_clips": len(data) - correct,
            "unique_videos": len(video_ids), "tasks": len({r["task_id"] for r in data}),
            "missing_procedures": sorted({r["task_id"] for r in data} - procedures.keys()),
            "invalid_times": [i for i, r in enumerate(data) if not (0 <= r["start_time"] < r["end_time"])],
            "duplicate_clip_keys": len(keys) - len(set(keys)),
            "null_action_annotation": sum(r.get("action_annotation") is None for r in data),
            "labels": dict(labels),
            "multilabel_rows": sum(isinstance(r.get("close_end_answer"), list) and len(r["close_end_answer"]) > 1 for r in data),
        }
        if dataset == "captaincook4d":
            entry["unmatched_cc4d_recordings"] = sorted(video_ids - cc_ids)
        result["files"][path.name] = entry
        totals[f"{mode}_clips"] += len(data)
        totals[f"{mode}_qa_pairs"] += qa_count
        Path(f"reports/{path.stem}_first10.json").write_text(json.dumps(data[:10], ensure_ascii=False, indent=2))
    result["totals"] = dict(totals)
    result["union_unique_videos_by_dataset"] = {k: len(v) for k, v in union_videos.items()}
    result["asset_bytes"] = sum(p.stat().st_size for p in root.glob("*.json"))
    return result


def main():
    report = {}
    for name, inspect in [("cc4d", inspect_cc4d), ("egoerrorvqa", inspect_ego)]:
        try:
            report[name] = inspect()
        except Exception as error:
            raise RuntimeError(f"annotation validation failed in {name}: {error}") from error
    Path("reports/annotation_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for name in ["cc4d_first10", "captaincook4d_qa_pairs_updated_first10"]:
        print(name, json.dumps(read_json(f"reports/{name}.json"), ensure_ascii=False))


if __name__ == "__main__":
    main()
