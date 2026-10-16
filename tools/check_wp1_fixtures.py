"""Verify hand-entered analytical answers; this is not the SQL/DAX implementation or E5."""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Europe/Helsinki")
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / "tests/fixtures/wp1"


def utc(value):
    if not value.endswith("Z"):
        raise ValueError("Fixture timestamps must explicitly identify UTC")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.minute or timestamp.second or timestamp.microsecond:
        raise ValueError("Fixture timestamps must be whole hours")
    return timestamp


def calendar(scope):
    if scope.get("empty"):
        return []
    start, end = utc(scope["start_utc"]), utc(scope["end_utc_exclusive"])
    count = int((end - start).total_seconds() // 3600)
    if not 0 < count <= 31 * 25:
        raise ValueError("Reference scope must be a positive bounded period")
    if any(t.astimezone(ZONE).hour for t in (start, end)):
        raise ValueError("Reference scopes must contain whole Helsinki days")
    return [start + timedelta(hours=i) for i in range(count)]


def read_inputs(directory):
    inputs = {}
    for name in ("heat", "weather_hourly"):
        values = {}
        with (directory / (name + ".csv")).open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                timestamp = utc(row["timestamp_utc"])
                if timestamp in values:
                    raise ValueError("Duplicate reference observation key")
                if name == "heat":
                    if row["system_id"] != "SYNTHETIC_HEATING" or Decimal(row["interval_hours"]) != 1:
                        raise ValueError("Only the declared synthetic interval-energy contract is supported")
                    value = Decimal(row["energy_mwh"])
                else:
                    if row["station_id"] != "SYNTHETIC_WEATHER" or int(row["finite_sample_count"]) != 6:
                        raise ValueError("Only complete synthetic weather hours are supported")
                    value = Decimal(row["temperature_c"])
                if not value.is_finite():
                    raise ValueError("Canonical reference inputs must be finite")
                values[timestamp] = value
        inputs[name] = values
    return inputs


def reference_answers(case, inputs):
    expected = calendar(case["scope"])
    keys = set(expected)
    omitted = {utc(value) for value in case.get("omit_heat_utc", [])}
    heat = {key: value for key, value in inputs["heat"].items() if key in keys
            and key not in omitted and not case.get("omit_all_heat")}
    weather = {key: value for key, value in inputs["weather_hourly"].items() if key in keys
               and key.astimezone(ZONE).date().isoformat() not in case.get("omit_weather_days", [])
               and not case.get("omit_all_weather")}
    empty_reason = "no_expected_keys" if not keys else "no_accepted_heat" if not heat else None
    total = sum(heat.values(), Decimal(0))
    complete = len(heat) == len(keys)
    energy = {"energy_mwh": str(total) if heat else None,
              "state": "blank" if empty_reason else "complete" if complete else "observed_subtotal",
              "blank_reason": empty_reason}
    maximum = max(heat.values()) if heat else None  # Each fixture interval is exactly one elapsed hour.
    peaks = sorted(key for key, value in heat.items() if value == maximum)
    peak = {"peak_mw": str(maximum) if maximum is not None else None, "tie_count": len(peaks),
            "earliest_utc": peaks[0].strftime("%Y-%m-%dT%H:%M:%SZ") if peaks else None,
            "earliest_local": peaks[0].astimezone(ZONE).isoformat() if peaks else None,
            "state": "blank" if empty_reason else "complete" if complete else "observed_peak",
            "blank_reason": empty_reason}
    baseline_keys = set(calendar(case["comparison_scope"])) if case["comparison_scope"] else set()
    baseline = {key: value for key, value in inputs["heat"].items() if key in baseline_keys}
    baseline_total = sum(baseline.values(), Decimal(0))
    if not keys:
        reason = "no_expected_keys"
    elif not baseline_keys:
        reason = "no_comparison_mapping"
    elif not complete or len(baseline) != len(baseline_keys):
        reason = "incomplete_period"
    elif len(keys) != len(baseline_keys):
        reason = "unequal_exposure"
    elif baseline_total == 0:
        reason = "zero_baseline"
    else:
        reason = None
    change = {"change_pct": None if reason else str(100 * (total - baseline_total) / baseline_total), "blank_reason": reason}
    coverage = {"expected_hours": len(keys), "accepted_heat_hours": len(heat), "accepted_weather_hours": len(weather),
                "heat_pct": str(Decimal(100) * len(heat) / len(keys)) if keys else None,
                "weather_pct": str(Decimal(100) * len(weather) / len(keys)) if keys else None}
    days = defaultdict(list)
    for key in expected:
        days[key.astimezone(ZONE).date().isoformat()].append(key)
    bands = defaultdict(list)
    unavailable = incomplete = 0
    flags = {}
    for day, day_keys in sorted(days.items()):
        good_weather = all(key in weather for key in day_keys)
        good_heat = all(key in heat for key in day_keys)
        reasons = ([] if good_weather else ["temperature_unavailable"]) + ([] if good_heat else ["heat_incomplete"])
        if reasons:
            flags[day] = reasons
        if not good_weather:
            unavailable += 1
        elif not good_heat:
            incomplete += 1
        else:
            average = sum((weather[key] for key in day_keys), Decimal(0)) / len(day_keys)
            lower = int((average / 5).to_integral_value(rounding=ROUND_FLOOR)) * 5
            bands[lower].append(sum((heat[key] for key in day_keys), Decimal(0)))
    grouped = {"selected_calendar_days": len(days), "eligible_days": sum(map(len, bands.values())),
               "temperature_unavailable_days": unavailable, "heat_incomplete_days": incomplete,
               "bands": [{"lower_c": lower, "upper_c": lower + 5, "mean_energy_mwh": str(sum(values) / len(values)),
                          "eligible_days": len(values)} for lower, values in sorted(bands.items())], "day_reason_flags": flags}
    return dict(zip(("M1", "M2", "M3", "M4", "M5"), (energy, peak, change, coverage, grouped)))


def compare(actual, expected, tolerance, location):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise ValueError(f"Reference shape mismatch at {location}")
        for key in expected:
            compare(actual[key], expected[key], tolerance, location + "." + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"Reference list mismatch at {location}")
        for i, (left, right) in enumerate(zip(actual, expected)):
            compare(left, right, tolerance, location + f"[{i}]")
    elif isinstance(expected, str):
        try:
            numeric = Decimal(expected)
        except InvalidOperation:
            if actual != expected:
                raise ValueError(f"Reference value mismatch at {location}")
        else:
            if actual is None or abs(Decimal(actual) - numeric) > tolerance:
                raise ValueError(f"Reference numeric mismatch at {location}")
    elif actual != expected:
        raise ValueError(f"Reference value mismatch at {location}")


def verify_suite(directory=DEFAULT_DIRECTORY):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if set(manifest["files"]) != {"heat.csv", "weather_hourly.csv", "cases.json"}:
        raise ValueError("Unexpected fixture file set")
    for name, expected_digest in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected_digest:
            raise ValueError("Reference fixture checksum mismatch")
    fixture = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
    inputs = read_inputs(directory)
    cases = fixture["cases"]
    if len({case["id"] for case in cases}) != len(cases) or len(cases) != manifest["case_count"]:
        raise ValueError("Reference case count/identity mismatch")
    if len(inputs["heat"]) != manifest["heat_rows"] or len(inputs["weather_hourly"]) != manifest["weather_rows"]:
        raise ValueError("Reference input count mismatch")
    for case in cases:
        compare(reference_answers(case, inputs), case["expected"], Decimal(fixture["numeric_tolerance"]), case["id"])
    if len(cases) * 5 != manifest["metric_comparisons"]:
        raise ValueError("Reference comparison count mismatch")
    return {"cases": len(cases), "comparisons": len(cases) * 5, "scope": "reference arithmetic; SQL/DAX/E5 not executed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args()
    try:
        result = verify_suite(args.directory)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Reference verification failed: {exc}\n")
    print(f"Verified {result['comparisons']} manual answers across {result['cases']} synthetic cases")
    print(result["scope"])


if __name__ == "__main__":
    main()
