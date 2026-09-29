import collections
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.assets import read_json


def trial_id(value):
    name = Path(value).stem
    for suffix in ["_front", "_left", "_right", "_top", "_ego"]:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def main():
    root = Path("annotations/impact/IMPACT-v1.1")
    ann = root / "annotations"
    files = sorted(p for p in root.rglob("*") if p.is_file())
    report = {"files": len(files), "bytes": sum(p.stat().st_size for p in files)}
    json_count = 0
    for path in files:
        if path.suffix == ".json":
            read_json(path)
            json_count += 1
    report["parsed_json_files"] = json_count
    tasks = {}
    for task in ["TAS-S", "TAS-B", "AF-S"]:
        source = ann / task / "annotations" if task == "AF-S" else ann / task
        records = [read_json(p) for p in sorted(source.glob("*/*.json"))]
        view_counts = collections.Counter(r["view"] for r in records)
        trials = {trial_id(r["video_id"]) for r in records}
        samples = []
        invalid = []
        phases = collections.Counter()
        phase_frames = collections.Counter()
        segments_by_hand = collections.Counter()
        for record in records:
            for segment in record["segments"]:
                start = segment.get("start_frame", segment.get("f_start"))
                end = segment.get("end_frame", segment.get("f_end"))
                if not (0 <= start <= end < record["meta_data"]["num_frames"]):
                    invalid.append({"video_id": record["video_id"], "segment": segment})
                if task == "TAS-B":
                    hand = segment.get("entity", "unknown")
                    segments_by_hand[hand] += 1
                    phases[segment.get("phase", "missing")] += 1
                    phase_frames[segment.get("phase", "missing")] += end - start + 1
                if len(samples) < 10:
                    samples.append({"video_id": record["video_id"], **segment})
        tasks[task] = {
            "json_files": len(records), "trials": len(trials), "views": dict(view_counts),
            "participants": len({t.split("_")[0] for t in trials}),
            "configurations": dict(collections.Counter(t.split("_")[-2] for t in trials)),
            "segment_count": sum(len(r["segments"]) for r in records),
            "invalid_segment_ranges": invalid,
            "fps_values": sorted({r["meta_data"]["fps"] for r in records}),
        }
        if task == "TAS-B":
            tasks[task].update({
                "action_vocab_sizes": sorted({len(r["action_labels"]) for r in records}),
                "segments_by_hand": dict(segments_by_hand),
                "phases_by_segments": dict(phases),
                "phases_by_frame_counts_across_views_hands": dict(phase_frames),
            })
        Path(f"reports/impact_{task}_first10.json").write_text(json.dumps(samples, indent=2))
    asr = [read_json(p) for p in sorted((ann / "ASR/annotations").glob("*.json"))]
    tasks["ASR"] = {
        "json_files": len(asr), "components": sorted({len(r["components"]) for r in asr}),
        "state_events": sum(len(r["state_sequence"]) for r in asr),
        "state_values": sorted({v for r in asr for e in r["state_sequence"] for v in e["state"]}),
        "split_summary": read_json(ann / "ASR/splits/split1_summary.json"),
    }
    tasks["PSR"] = {
        "event_categories": len(read_json(ann / "PSR/labels/procedure_info_IMPACT.json")),
        "conversion_summary": read_json(ann / "PSR/labels/conversion_summary_split1.json"),
    }
    report["tasks"] = tasks
    splits = {}
    for directory in sorted({p.parent for p in ann.rglob("*.bundle")}):
        for number in range(1, 5):
            parts = {}
            for part in ["train", "val", "test"]:
                path = directory / f"{part}.split{number}.bundle"
                if path.exists():
                    parts[part] = [l.strip() for l in path.read_text().splitlines() if l.strip()]
            if not parts:
                continue
            sets = {part: set(values) for part, values in parts.items()}
            trial_sets = {part: {trial_id(v) for v in values} for part, values in parts.items()}
            splits[f"{directory.relative_to(ann)}/S{number}"] = {
                "file_counts": {k: len(v) for k, v in parts.items()},
                "unique_trial_counts": {k: len(v) for k, v in trial_sets.items()},
                "file_overlaps": {f"{a}/{b}": len(sets[a] & sets[b]) for a, b in itertools.combinations(sets, 2)},
                "trial_overlaps": {f"{a}/{b}": sorted(trial_sets[a] & trial_sets[b]) for a, b in itertools.combinations(trial_sets, 2)},
            }
    report["splits"] = splits
    Path("reports/impact_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"files": report["files"], "bytes": report["bytes"], "json_files": json_count,
                      "tasks": {k: {a: b for a, b in v.items() if a != "split_summary"} for k, v in tasks.items()},
                      "split_trial_overlap_counts": {k: {a: len(b) for a, b in v["trial_overlaps"].items()} for k, v in splits.items()}}, indent=2))


if __name__ == "__main__":
    main()
