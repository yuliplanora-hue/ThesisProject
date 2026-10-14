"""Run the small versioned FMI sample matrix and retain failure/success evidence."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.fmi import acquire_sample, request_parameters


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/feasibility-samples.json"))
    args = parser.parse_args()
    try:
        config_bytes = args.config.read_bytes()
        config = json.loads(config_bytes)
        samples = config["samples"]
        if not 1 <= len(samples) <= 12 or len({s["id"] for s in samples}) != len(samples):
            raise ValueError("Use 1-12 uniquely named feasibility samples")
        queries = [(sample["id"], request_parameters(sample["start"], sample["end"],
                                                    station=config["station_id"], timestep=sample["timestep"]))
                   for sample in samples]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(2, f"Invalid sample configuration: {exc}\n")
    report = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
              "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
              "full_period_coverage_verified": False, "samples": []}
    report["code_sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [Path("ingestion/fmi.py"), Path(__file__)]}
    output_dir = Path("experiments/source-audit")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / ("fmi-matrix-" + uuid4().hex + ".json")
    for label, parameters in queries:
        try:
            manifest, path = acquire_sample(parameters, Path("data/raw/fmi-feasibility"), output_dir / "fmi")
            inspection = manifest["inspection"]
            coverage = inspection["coverage_by_station"][config["station_id"]]
            passed = (inspection["duplicate_key_rows"] == 0 and coverage["absent_samples"] == 0
                      and coverage["missing_value_samples"] == 0)
            entry = {"id": label, "status": "pass" if passed else "coverage_issue", "manifest": path.as_posix(),
                     "coverage": coverage, "keyed_observation_sha256": inspection["keyed_observation_sha256"]}
        except (ValueError, OSError) as exc:
            entry = {"id": label, "status": "failed", "error": str(exc)}
        report["samples"].append(entry)
        # Save after each request so a later interruption retains the earlier evidence.
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"{label}: {entry['status']}", flush=True)
    by_id = {s["id"]: s for s in report["samples"]}
    original, repeat = by_id.get("winter-2024"), by_id.get("winter-2024-repeat")
    report["repeat_observation_content_equal"] = (
        original["keyed_observation_sha256"] == repeat["keyed_observation_sha256"]
        if original and repeat and original["status"] == repeat["status"] == "pass" else None)
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {output}")
    return 0 if all(s["status"] == "pass" for s in report["samples"]) and report["repeat_observation_content_equal"] is not False else 2


if __name__ == "__main__":
    raise SystemExit(main())
