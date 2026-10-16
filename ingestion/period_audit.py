"""Weather availability accounting for WP1.3; does not publish analytical facts."""

import hashlib
import math
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ingestion.fmi import NS, inspect_response, utc_time


def plan_chunks(start: str, end: str, days: int = 7) -> list[tuple[str, str]]:
    first, last = utc_time(start), utc_time(end)
    if not 1 <= days <= 7 or not timedelta(0) < last - first <= timedelta(days=732):
        raise ValueError("Use a positive period of at most 732 days and 1-7 day chunks")
    if any(t.minute or t.second or t.microsecond for t in (first, last)):
        raise ValueError("Period boundaries must be whole UTC hours")
    result = []
    while first < last:
        boundary = min(first + timedelta(days=days), last)
        result.append((first.isoformat(), boundary.isoformat()))
        first = boundary
    return result


def chunk_points(payload: bytes, start: str, end: str, station: str) -> dict:
    inspection = inspect_response(payload, start, end, station, timestep=10)
    if inspection["duplicate_key_rows"]:
        raise ValueError("Duplicate source keys prevent period coverage acceptance")
    first, last = utc_time(start), utc_time(end)
    points = {}
    for point in ET.fromstring(payload).findall(".//wml:MeasurementTVP", NS):
        timestamp = utc_time(point.findtext("wml:time", namespaces=NS))
        if first <= timestamp < last:
            value = float(point.findtext("wml:value", namespaces=NS))
            points[timestamp] = value if math.isfinite(value) else None
    return {"points": points, "inspection": inspection}


def verify_cached_manifest(manifest: dict, raw_dir: Path, parameters: dict) -> bytes:
    if manifest.get("status") != "inspected" or manifest.get("parameters") != parameters:
        raise ValueError("Cached manifest does not match the declared request")
    digest = manifest["response_sha256"]
    # Derive the filename from the expected hash rather than trusting a path from JSON.
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid cached content hash")
    payload = (raw_dir / (digest + ".xml")).read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("Cached response checksum mismatch")
    return payload


def summarize_period(points: dict, start: str, end: str, reporting_timezone: str = "Europe/Helsinki") -> dict:
    first, last = utc_time(start), utc_time(end)
    plan_chunks(start, end)
    zone = ZoneInfo(reporting_timezone)
    expected = set()
    cursor = first
    while cursor < last:
        expected.add(cursor)
        cursor += timedelta(minutes=10)
    if any(t not in expected for t in points):
        raise ValueError("Points outside the declared sample grid")
    returned = set(points)
    valid = {t for t, value in points.items() if value is not None and math.isfinite(value)}
    missing = expected - returned
    invalid = returned - valid
    valid_per_hour = Counter(t.replace(minute=0) for t in valid)
    expected_per_day = Counter()
    complete_per_day = Counter()
    incomplete_hours = []
    cursor = first
    while cursor < last:
        day = cursor.astimezone(zone).date().isoformat()
        expected_per_day[day] += 1
        if valid_per_hour[cursor] == 6:
            complete_per_day[day] += 1
        else:
            incomplete_hours.append(cursor.isoformat())
        cursor += timedelta(hours=1)
    daily = {day: {"expected_hours": hours, "complete_hours": complete_per_day[day]}
             for day, hours in sorted(expected_per_day.items())}
    for day, counts in daily.items():
        midnight = datetime.combine(date.fromisoformat(day), time(), tzinfo=zone)
        full_day_hours = int(((midnight + timedelta(days=1)).astimezone(timezone.utc)
                              - midnight.astimezone(timezone.utc)).total_seconds() // 3600)
        counts["full_calendar_day_hours"] = full_day_hours
        counts["full_day_in_scope"] = counts["expected_hours"] == full_day_hours
    return {
        "expected_samples": len(expected), "returned_distinct_samples": len(returned),
        "valid_samples": len(valid), "absent_samples": len(missing), "nonfinite_samples": len(invalid),
        "expected_hours": sum(expected_per_day.values()),
        "complete_six_sample_hours": sum(complete_per_day.values()),
        "incomplete_hours": len(incomplete_hours), "incomplete_hour_examples": incomplete_hours[:20],
        "expected_local_days": len(daily),
        "complete_local_days": sum(v["full_day_in_scope"] and v["expected_hours"] == v["complete_hours"] for v in daily.values()),
        "partial_local_days": sum(not v["full_day_in_scope"] for v in daily.values()),
        "minimum_finite_temperature_c": min((points[t] for t in valid), default=None),
        "maximum_finite_temperature_c": max((points[t] for t in valid), default=None),
        "days_by_expected_hours": dict(sorted(Counter(str(v["expected_hours"]) for v in daily.values()).items())),
        "daily_coverage": daily,
        "accounting_reconciles": len(expected) == len(valid) + len(missing) + len(invalid),
        "weather_coverage_only": True,
    }
