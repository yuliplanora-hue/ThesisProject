"""Acquire/resume a bounded two-year weather availability audit from the versioned contract."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.fmi import acquire_sample, request_parameters
from ingestion.period_audit import chunk_points, plan_chunks, summarize_period, verify_cached_manifest


def write_report(path: Path, report: dict):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("config/fmi-source-contract.json"))
    parser.add_argument("--output", type=Path, default=Path("experiments/source-audit/fmi-full-period.json"))
    args = parser.parse_args()
    try:
        config_bytes = args.contract.read_bytes()
        config = json.loads(config_bytes)
        if config["request_timestep_minutes"] != 10 or config["expected_samples_per_hour"] != 6:
            raise ValueError("This audit implements the declared ten-minute/six-sample baseline only")
        chunks = plan_chunks(config["project_start_utc"], config["project_end_utc_exclusive"], config["chunk_days"])
        config_hash = hashlib.sha256(config_bytes).hexdigest()
        previous = json.loads(args.output.read_text()) if args.output.exists() else {}
        if previous and previous.get("configuration_sha256") != config_hash:
            raise ValueError("Existing output has a different contract; choose a new output path")
        cached = {c["index"]: c for c in previous.get("chunks", []) if c["status"] == "inspected"}
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Invalid period configuration: {exc}\n")
    raw_dir = Path("data/raw/fmi-feasibility")
    manifest_dir = Path("experiments/source-audit/fmi-period-manifests")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {"audit_version": "0.1", "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "configuration_sha256": config_hash, "station_id": config["station_id"],
              "start_utc": config["project_start_utc"], "end_utc_exclusive": config["project_end_utc_exclusive"],
              "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None,
              "git_worktree_dirty": bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()),
              "code_sha256": {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path("ingestion/fmi.py"), Path("ingestion/period_audit.py"), Path("tools/audit_fmi_period.py"))},
              "status": "running", "chunks": []}
    points = {}
    for index, (start, end) in enumerate(chunks):
        parameters = request_parameters(start, end, station=config["station_id"], timestep=10)
        try:
            if index in cached:
                path = Path(cached[index]["manifest"])
                manifest = json.loads(path.read_text())
                payload = verify_cached_manifest(manifest, raw_dir, parameters)
                mode = "cache_revalidated"
            else:
                manifest, path = acquire_sample(parameters, raw_dir, manifest_dir)
                payload = verify_cached_manifest(manifest, raw_dir, parameters)
                mode = "acquired"
            inspected = chunk_points(payload, start, end, config["station_id"])
            if points.keys() & inspected["points"].keys():
                raise ValueError("Chunk overlap duplicated a project key")
            points.update(inspected["points"])
            entry = {"index": index, "start": start, "end_exclusive": end, "status": "inspected",
                     "mode": mode, "manifest": path.as_posix(),
                     "coverage": inspected["inspection"]["coverage_by_station"][config["station_id"]]}
        except (ValueError, OSError) as exc:
            entry = {"index": index, "start": start, "end_exclusive": end, "status": "failed", "error": str(exc)}
        report["chunks"].append(entry)
        write_report(args.output, report)
        print(f"Chunk {index + 1}/{len(chunks)}: {entry['status']}", flush=True)
        if entry["status"] == "failed":
            report["status"] = "incomplete"
            write_report(args.output, report)
            print("Stopped after a failed chunk; rerun the same command to resume", file=sys.stderr)
            return 2
    report["coverage"] = summarize_period(points, config["project_start_utc"], config["project_end_utc_exclusive"], config["reporting_timezone"])
    report["status"] = "audit_completed"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_report(args.output, report)
    coverage = report["coverage"]
    print(f"Weather audit complete: {coverage['valid_samples']}/{coverage['expected_samples']} valid samples; "
          f"{coverage['complete_six_sample_hours']}/{coverage['expected_hours']} complete hours")
    print(f"Saved {args.output}; paired heating contract remains separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
