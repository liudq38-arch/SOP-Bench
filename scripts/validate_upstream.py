import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.assets import read_json


def main():
    report = {}
    root = next(Path("annotations/assembly101_mistake_upstream").iterdir())
    paths = sorted((root / "annots").glob("*.csv"))
    rows = []
    widths = collections.Counter()
    for path in paths:
        with path.open() as handle:
            for row in csv.reader(handle):
                if row:
                    widths[len(row)] += 1
                    rows.append({"source_file": str(path), **dict(zip(["start", "end", "verb", "this", "that", "label", "remark"], row))})
    report["assembly101"] = {
        "csv_files": len(paths), "rows": len(rows),
        "labels": dict(collections.Counter(row["label"] for row in rows)),
        "column_widths": dict(widths),
        "nonpositive_intervals": sum(float(row["end"]) <= float(row["start"]) for row in rows),
    }
    Path("reports/assembly_first10.json").write_text(json.dumps(rows[:10], indent=2))
    data = read_json("annotations/egooops_upstream/meta/metadata.json")
    rows = [dict(video_id=video["video_id"], task_id=video["task_id"], **segment) for video in data["videos"] for segment in video["segments"]]
    report["egooops"] = {
        "videos": len(data["videos"]), "segments": len(rows),
        "error_segments": sum(bool(row["labels"]) for row in rows),
        "tasks": list(data["instructions"]),
    }
    Path("reports/egooops_first10.json").write_text(json.dumps(rows[:10], indent=2))
    root = next(Path("annotations/epic_tent_upstream").iterdir())
    tent = {}
    for kind in ["action", "error"]:
        with (root / f"Synchronised_{kind}_label.txt").open() as handle:
            rows = list(csv.DictReader(handle))
        tent[kind] = {
            "rows": len(rows),
            "subjects": len({row["subject_id"] for row in rows}),
            "missing_gopro_start_frame": sum(int(row["str_GoPro_frame"]) < 0 for row in rows),
        }
        Path(f"reports/epictent_{kind}_first10.json").write_text(json.dumps(rows[:10], indent=2))
    tent["frame_label_files"] = len(list((root / "frame_level_action_annotation").glob("*.txt")))
    report["epic_tent"] = tent
    Path("reports/upstream_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    for name in ["assembly", "egooops", "epictent_action", "epictent_error"]:
        print(name, json.dumps(read_json(f"reports/{name}_first10.json")))


if __name__ == "__main__":
    main()
