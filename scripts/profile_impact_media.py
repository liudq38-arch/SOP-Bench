import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/home/ldq/sop_work")
import mp4_probe


ROOT = Path("/data_1/ldq/dataset/impact/IMPACT-v1.1")
REPORT = Path("reports/design/impact_media_stats.json")


def quantiles(values):
    values = sorted(values)
    def q(p):
        return values[int((len(values) - 1) * p)]
    return {
        "min": min(values),
        "p25": q(0.25),
        "median": q(0.50),
        "p75": q(0.75),
        "p90": q(0.90),
        "max": max(values),
        "mean": statistics.mean(values),
    }


def segment_stats(files, coarse=False):
    rows = []
    for path in files:
        data = json.loads(path.read_text())
        fps = data["meta_data"]["fps"]
        key_start = "f_start" if coarse else "start_frame"
        key_end = "f_end" if coarse else "end_frame"
        for segment in data["segments"]:
            frames = segment[key_end] - segment[key_start] + 1
            rows.append({
                "phase": segment.get("phase"),
                "action_label": segment.get("action_label"),
                "frames": frames,
                "duration_sec": frames / fps,
            })
    result = {
        "records": len(files),
        "segments": len(rows),
        "fps": sorted({json.loads(p.read_text())["meta_data"]["fps"] for p in files}),
        "duration_sec": quantiles([r["duration_sec"] for r in rows]),
        "phase_counts": dict(Counter(r["phase"] for r in rows if r["phase"])),
    }
    if not coarse:
        non_null = [r for r in rows if r["action_label"] != 0]
        result["null_action_segments"] = len(rows) - len(non_null)
        result["non_null_action_segments"] = len(non_null)
        result["non_null_duration_sec"] = quantiles([r["duration_sec"] for r in non_null])
        result["non_null_phase_duration_sec"] = {}
        for phase in ["normal", "anomaly", "recovery"]:
            vals = [r["duration_sec"] for r in non_null if r["phase"] == phase]
            if vals:
                result["non_null_phase_duration_sec"][phase] = {
                    "count": len(vals),
                    "stats": quantiles(vals),
                }
    return result


def main():
    files = sorted((ROOT / "videos/ego").glob("*.mp4"))
    probes = [mp4_probe.probe(str(path)) for path in files]
    video = {
        "root": str(ROOT / "videos/ego"),
        "files": len(probes),
        "resolution": {
            "x".join(map(str, key)): value
            for key, value in Counter(tuple(row.get("resolution") or []) for row in probes).items()
        },
        "codec": dict(Counter((row.get("video") or {}).get("codec", [None])[0] for row in probes)),
        "fps": dict(Counter(row.get("fps") for row in probes)),
        "audio_tracks_with_nonzero_bitrate": sum((row.get("audio_bitrate_mbps") or 0) > 0 for row in probes),
        "duration_sec": quantiles([row["duration_sec"] for row in probes]),
        "frames": quantiles([(row.get("video") or {}).get("sample_count", 0) for row in probes]),
        "file_size_bytes": quantiles([row["size_bytes"] for row in probes]),
        "total_duration_sec": sum(row["duration_sec"] for row in probes),
        "total_frames": sum((row.get("video") or {}).get("sample_count", 0) for row in probes),
        "total_bytes": sum(row["size_bytes"] for row in probes),
        "frame_count_matches_duration": all(
            abs((row.get("video") or {}).get("sample_count", 0) / row["duration_sec"] - row["fps"]) < 0.01
            for row in probes
        ),
    }
    annotations = ROOT / "annotations"
    tas_b = segment_stats(sorted((annotations / "TAS-B/ego").glob("*.json")))
    tas_s = segment_stats(sorted((annotations / "TAS-S/ego").glob("*.json")), coarse=True)
    external_fps = {}
    for view in ["front", "left", "right", "top"]:
        paths = sorted((annotations / f"TAS-B/{view}").glob("*.json"))
        if paths:
            external_fps[view] = sorted({json.loads(p.read_text())["meta_data"]["fps"] for p in paths})
    report = {
        "date": "2026-09-18",
        "source": "local IMPACT v1.1 ego bundle and annotations",
        "video": video,
        "annotations": {
            "TAS_B_ego": tas_b,
            "TAS_S_ego": tas_s,
            "annotation_fps_external_views": external_fps,
        },
        "scope_note": "Only ego MP4 media is locally present and measured. External-view fps comes from annotation metadata; external MP4 container codec was not measured because those bundles are not present locally.",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
