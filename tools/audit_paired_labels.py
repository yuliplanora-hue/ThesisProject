"""Audit paired-window labels using an explicitly evidenced interval convention."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def inspect_window(contract_path: Path, weather_path: Path) -> dict:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if not contract["semantic_contract"]["accepted_utc_mapping"]:
        raise ValueError("Publisher-declared UTC mapping must be evidenced first")
    semantic = contract["semantic_contract"]
    selected = None
    if semantic.get("accepted_interval_label_mapping"):
        convention = semantic.get("interval_convention")
        if convention not in ("interval_start", "interval_end"):
            raise ValueError("Unsupported accepted interval convention")
        selected = "timestamp_as_" + convention
    payload = Path(contract["local_snapshot"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != contract["snapshot_sha256"]:
        raise ValueError("Helen snapshot differs from its audited contract")
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), delimiter=";")
    if reader.fieldnames != contract["lexical_contract"]["columns"]:
        raise ValueError("Helen schema differs from the contract")
    labels = Counter(datetime.strptime(row["datetime_utc"], "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
                     for row in reader)
    start = datetime.fromisoformat(contract["paired_period"]["candidate_start_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(contract["paired_period"]["candidate_end_utc_exclusive"].replace("Z", "+00:00"))
    hours = (end - start).total_seconds() / 3600
    if not hours.is_integer() or not 0 < hours <= 732 * 24:
        raise ValueError("Invalid proposed hourly window")
    weather_bytes = weather_path.read_bytes()
    weather = json.loads(weather_bytes)
    if weather["status"] != "audit_completed" or weather["coverage"]["expected_hours"] != int(hours):
        raise ValueError("Weather audit is incomplete or has a different expected grid")
    if datetime.fromisoformat(weather["start_utc"].replace("Z", "+00:00")) != start or datetime.fromisoformat(weather["end_utc_exclusive"].replace("Z", "+00:00")) != end:
        raise ValueError("Weather audit boundaries differ from the proposed window")
    scenarios = {}
    for name, shift in (("timestamp_as_interval_start", 0), ("timestamp_as_interval_end", 1)):
        expected = {start + timedelta(hours=i + shift) for i in range(int(hours))}
        returned = expected.intersection(labels)
        scenarios[name] = {
            "status": ("selected by evidenced interval-label convention" if name == selected
                       else "alternative label-coverage check; not selected"),
            "first_expected_label_utc": min(expected).isoformat(),
            "last_expected_label_utc": max(expected).isoformat(),
            "expected_labels": len(expected), "returned_distinct_labels": len(returned),
            "absent_labels": len(expected - returned),
            "duplicate_rows_in_scope": sum(labels[key] - 1 for key in returned),
        }
    return {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_version": contract["contract_version"],
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "helen_snapshot_sha256": contract["snapshot_sha256"],
        "weather_audit_sha256": hashlib.sha256(weather_bytes).hexdigest(),
        "window_start_utc": start.isoformat(), "window_end_utc_exclusive": end.isoformat(),
        "hypotheses": scenarios,
        "selected_label_mapping": selected,
        "interval_mapping_evidence": semantic.get("interval_mapping_evidence"),
        "weather_complete_hours": weather["coverage"]["complete_six_sample_hours"],
        "weather_complete_days": weather["coverage"]["complete_local_days"],
        "interpretation": "Selection follows explicit contract evidence, not coverage. Available labels do not establish physical quantity, system boundary or licence acceptance.",
        "paired_physical_contract_accepted": False,
        "scope": "source-key feasibility only; no heating values aggregated, model fitted or E1-E7 passed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("config/helen-source-contract.json"))
    parser.add_argument("--weather-report", type=Path, default=Path("experiments/source-audit/fmi-full-period.json"))
    parser.add_argument("--output", type=Path, default=Path("experiments/source-audit/paired-label-window.json"))
    args = parser.parse_args()
    try:
        result = inspect_window(args.contract, args.weather_report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Paired-label audit failed ({type(exc).__name__}); verify contracts and source reports.\n")
    for name, counts in result["hypotheses"].items():
        print(f"{name}: {counts['returned_distinct_labels']}/{counts['expected_labels']} labels; absent {counts['absent_labels']}; duplicates {counts['duplicate_rows_in_scope']}")
    print(f"Selected label mapping: {result['selected_label_mapping'] or 'none'}; physical paired contract remains unaccepted.")


if __name__ == "__main__":
    main()
