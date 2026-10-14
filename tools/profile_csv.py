"""Lightweight Phase 1 dataset profiler. No network requests, no assumed schema.

Usage:
    python tools/profile_csv.py data/raw/helen.csv --output experiments/helen_profile.json
    python tools/profile_csv.py data/raw/helen.csv --timestamp "Date" --output experiments/helen_profile.json

This does NOT infer physical units or certify publisher provenance/time zone.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_settings(path: Path) -> dict:
    sample = path.read_bytes()[:65536].decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except csv.Error:
        delim = ","
    return {"separator": delim, "encoding": "utf-8-sig"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv_file", type=Path)
    p.add_argument("--timestamp", help="Optional existing column name used for date/time profiling")
    p.add_argument("--output", type=Path, help="Path of JSON audit output")
    args = p.parse_args()
    path = args.csv_file
    if not path.is_file():
        p.error(f"File not found: {path}")

    settings = csv_settings(path)
    try:
        data = pd.read_csv(path, sep=settings["separator"], encoding=settings["encoding"], low_memory=False)
    except UnicodeDecodeError:
        settings["encoding"] = "latin-1"
        data = pd.read_csv(path, sep=settings["separator"], encoding=settings["encoding"], low_memory=False)

    report = {
        "path": str(path),
        "sha256": hash_file(path),
        "size_bytes": path.stat().st_size,
        "delimiter": settings["separator"],
        "encoding": settings["encoding"],
        "rows": int(len(data)),
        "columns": [str(x) for x in data.columns],
        "data_types_as_imported": {str(k): str(v) for k, v in data.dtypes.items()},
        "missing_values_per_column": {str(k): int(v) for k, v in data.isna().sum().items()},
        "fully_duplicated_rows": int(data.duplicated().sum()),
        "first_five_rows": json.loads(data.head(5).to_json(orient="records", date_format="iso")),
        "timestamp_column": args.timestamp,
        "timestamp_results": None,
        "warnings": [
            "Parsers, source units, time zone, intervals, and column meanings require manual publisher verification.",
            "Identical complete rows are not the same as duplicate timestamp/business keys.",
        ],
    }
    if args.timestamp:
        if args.timestamp not in data.columns:
            p.error(f"Timestamp column {args.timestamp!r} not found. Available: {data.columns.tolist()}")
        ts = pd.to_datetime(data[args.timestamp], errors="coerce", utc=False)
        good = ts.dropna()
        report["timestamp_results"] = {
            "parsed_count": int(ts.notna().sum()),
            "unparsed_count": int(ts.isna().sum()),
            "minimum_as_parsed": str(good.min()) if not good.empty else None,
            "maximum_as_parsed": str(good.max()) if not good.empty else None,
            "duplicated_timestamp_count": int(good.duplicated().sum()),
        }
        report["warnings"].append("Do not assume naive timestamps are UTC; confirm semantics before converting.")

    result = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
        print(f"Saved audit: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
