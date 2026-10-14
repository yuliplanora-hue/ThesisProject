"""Run the explicit source-feasibility audit; no energy/power conversion is performed."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.audit import audit_helen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_helen(args.csv_file)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(2, f"Audit failed: {exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {args.output}: {report['rows']} rows, {report['rejected_rows']} rejected")
    return 2 if not report["rows"] or report["rejected_rows"] or report["duplicate_timestamp_rows"] or report["off_hour_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
