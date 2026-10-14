"""Acquire one bounded FMI sample and retain its immutable response and inspection manifest."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.fmi import acquire_sample, request_parameters


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="Exclusive project boundary; FMI may also return this endpoint")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--station")
    selector.add_argument("--place", help="Station discovery only; inspect identity before choosing")
    parser.add_argument("--timestep", type=int, choices=(10, 60), default=60)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/fmi-feasibility"))
    parser.add_argument("--manifest-dir", type=Path, default=Path("experiments/source-audit/fmi"))
    args = parser.parse_args()
    try:
        parameters = request_parameters(args.start, args.end, args.station, args.place, args.timestep)
        manifest, path = acquire_sample(parameters, args.raw_dir, args.manifest_dir)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Feasibility check failed: {exc}\n")
    inspection = manifest["inspection"]
    print(f"Saved manifest {path}; stations: {', '.join(inspection['station_metadata'])}")
    print(f"In-scope points: {inspection['point_rows_in_scope']}; duplicates: {inspection['duplicate_key_rows']}")
    return 2 if inspection["duplicate_key_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
