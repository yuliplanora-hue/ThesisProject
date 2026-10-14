"""Explicit Helen parsing without asserting physical units or timestamp timezone."""

import csv
import hashlib
import re
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

HELEN_COLUMNS = ["datetime_utc", "dh_MWh"]
HELEN_TIME_FORMAT = "%d.%m.%Y %H:%M"
AUDIT_VERSION = "0.1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_helen(path: Path) -> dict:
    """Account for every row, retaining only bounded examples in the report.

    Written-clock coverage is deliberately naive: it does not certify UTC/DST
    semantics. Original strings remain in the unchanged input snapshot.
    """
    timestamps = Counter()
    values_by_time = {}
    monthly = Counter()
    reasons = Counter()
    examples = []
    conflicts = set()
    minimum_value = maximum_value = None
    row_count = accepted = negative = off_hour = 0
    previous = None
    descending_steps = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        if reader.fieldnames != HELEN_COLUMNS:
            raise ValueError(f"Helen schema mismatch: expected {HELEN_COLUMNS}, got {reader.fieldnames}")
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            errors = []
            timestamp = value = None
            if None in row or any(row.get(column) is None for column in HELEN_COLUMNS):
                errors.append("wrong_field_count")
            try:
                raw_time = row.get("datetime_utc") or ""
                timestamp = datetime.strptime(raw_time, HELEN_TIME_FORMAT)
                if timestamp.strftime(HELEN_TIME_FORMAT) != raw_time:
                    raise ValueError("timestamp not in canonical source format")
            except ValueError:
                errors.append("invalid_timestamp")
            try:
                raw_value = row.get("dh_MWh") or ""
                if not re.fullmatch(r"[+-]?\d+(?:,\d+)?", raw_value):
                    raise InvalidOperation
                value = Decimal(raw_value.replace(",", "."))
                if not value.is_finite() or raw_value.strip() != raw_value:
                    raise InvalidOperation
            except InvalidOperation:
                errors.append("invalid_measurement")
            if timestamp is not None:
                timestamps[timestamp] += 1
                monthly[timestamp.strftime("%Y-%m")] += 1
                off_hour += int(timestamp.minute != 0 or timestamp.second != 0)
                descending_steps += int(previous is not None and timestamp < previous)
                previous = timestamp
            if errors:
                reasons.update(errors)
                if len(examples) < 10:
                    examples.append({"csv_row": row_number, "reasons": errors})
                continue
            accepted += 1
            if timestamp in values_by_time and values_by_time[timestamp] != value:
                conflicts.add(timestamp)
            values_by_time.setdefault(timestamp, value)
            minimum_value = value if minimum_value is None else min(minimum_value, value)
            maximum_value = value if maximum_value is None else max(maximum_value, value)
            negative += int(value < 0)
    ordered = sorted(timestamps)
    coverage = None
    # A finite range prevents a malformed historical date from creating an
    # unbounded hourly expansion. Off-hour timestamps are reported separately.
    if ordered and off_hour == 0:
        first, last = ordered[0], ordered[-1]
        expected_count = int((last - first).total_seconds() // 3600) + 1
        if expected_count > 1_000_000:
            raise ValueError("Written-clock range exceeds the bounded audit limit")
        missing = []
        missing_count = 0
        cursor = first
        while cursor <= last:
            if cursor not in timestamps:
                missing_count += 1
                if len(missing) < 10:
                    missing.append(cursor.isoformat())
            cursor += timedelta(hours=1)
        coverage = {"expected_keys": expected_count, "observed_distinct_keys": len(ordered),
                    "missing_keys": missing_count, "missing_examples": missing,
                    "basis": "naive written-clock hourly sequence; timezone unverified"}
    return {
        "audit_version": AUDIT_VERSION,
        "source_file": path.name, "source_sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "parser": {"encoding": "utf-8-sig", "delimiter": ";",
                   "timestamp_format": HELEN_TIME_FORMAT, "decimal_separator": ","},
        "rows": row_count, "parsable_rows": accepted, "rejected_rows": row_count - accepted,
        "rejection_counts": dict(reasons), "rejection_examples": examples,
        "minimum_timestamp_as_written": ordered[0].isoformat() if ordered else None,
        "maximum_timestamp_as_written": ordered[-1].isoformat() if ordered else None,
        "duplicate_timestamp_rows": sum(count - 1 for count in timestamps.values()),
        "conflicting_timestamp_keys": len(conflicts), "off_hour_rows": off_hour,
        "descending_timestamp_steps": descending_steps, "negative_measurements": negative,
        "minimum_measurement_as_written": str(minimum_value) if minimum_value is not None else None,
        "maximum_measurement_as_written": str(maximum_value) if maximum_value is not None else None,
        "rows_by_written_month": dict(sorted(monthly.items())), "written_clock_coverage": coverage,
        "analytical_use_approved": False,
        "unresolved": ["timestamp timezone", "interval start/end convention",
                       "physical quantity and interval representation", "source revision precedence"],
    }
