"""Transactional source-resolution FMI loading with explicit revision lineage."""

import hashlib
import json
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from ingestion.database import begin_run, finish_run
from ingestion.fmi import NS, acquire_sample, inspect_response, request_parameters, utc_time
from ingestion.provenance import code_identity, inspect_manifest, project_path, read_json, register_acquisition
from ingestion.period_audit import plan_chunks

ERRORS = (ValueError, TypeError, KeyError, AttributeError, OSError, psycopg.Error)


def period_manifest_paths(root: Path, settings: dict, report_path: Path) -> list[Path]:
    path = project_path(root, report_path)
    if not path.is_relative_to(project_path(root, "experiments/source-audit")):
        raise ValueError("Weather period report must be under source-audit")
    report, _ = read_json(path)
    baseline = settings["contract"]
    if report["status"] != "audit_completed" or report["configuration_sha256"] != settings["configuration_identity"]["contract_sha256"]:
        raise ValueError("Period report does not match the current weather baseline")
    if (report["start_utc"], report["end_utc_exclusive"], report["station_id"]) != (baseline["project_start_utc"], baseline["project_end_utc_exclusive"], baseline["station_id"]):
        raise ValueError("Period boundaries/station differ from the declared baseline")
    expected = plan_chunks(report["start_utc"], report["end_utc_exclusive"], baseline["chunk_days"])
    if len(report["chunks"]) != len(expected):
        raise ValueError("Period chunk list is incomplete")
    paths = []
    for index, ((start, end), chunk) in enumerate(zip(expected, report["chunks"])):
        if (chunk["index"], chunk["status"], chunk["start"], chunk["end_exclusive"]) != (index, "inspected", start, end):
            raise ValueError("Period chunk grid differs from the baseline")
        manifest_path = project_path(root, chunk["manifest"])
        manifest, _ = read_json(manifest_path)
        parameters = manifest["parameters"]
        if parameters != request_parameters(start, end, station=baseline["station_id"], timestep=10):
            raise ValueError("Period manifest request differs from its declared chunk")
        paths.append(manifest_path)
    return paths


def weather_settings(root: Path, foundation: dict,
                     contract_path: Path = Path("config/weather-ingestion.json")) -> dict:
    contract, payload = read_json(project_path(root, contract_path))
    required = {"version": "0.1", "source_id": "FMI_WEATHER", "parameter": "t2m", "unit": "degC",
                "timestamp_basis": "UTC observation instant", "source_aggregation_period": "PT1M",
                "request_timestep_minutes": 10, "parser_version": "fmi-point-0.1",
                "accepted_scope": "FMI source-resolution temperature ingestion only",
                "nan_rule": "retain original text; NULL temperature with source_nan quality",
                "absent_rule": "record expected minus returned keys; do not fabricate source rows",
                "revision_rule": "retain each content snapshot; no active-revision selection",
                "paired_heating_acceptance": False}
    if foundation["source"] != "FMI" or any(contract.get(k) != v for k, v in required.items()):
        raise ValueError("Unsupported weather-ingestion contract")
    baseline = foundation["contract"]
    if any(baseline.get(k) != v for k, v in {"parameter": "t2m", "unit": "degC", "source_timestamp_timezone": "UTC", "source_aggregation_period": "PT1M"}.items()):
        raise ValueError("Weather baseline semantics differ from the typed-ingestion contract")
    stations = contract["allowed_station_ids"]
    if not isinstance(stations, list) or not stations or any(not isinstance(s, str) or not s.isdecimal() for s in stations):
        raise ValueError("Invalid declared station list")
    if contract["default_station_id"] not in stations or type(contract["maximum_batch_manifests"]) is not int or not 1 <= contract["maximum_batch_manifests"] <= 110:
        raise ValueError("Invalid weather batch settings")
    identity = {**foundation["configuration_identity"], "weather_contract_sha256": hashlib.sha256(payload).hexdigest()}
    return {**foundation, "weather_contract": contract, "configuration_identity": identity,
            "configuration_sha256": hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()}


def typed_points(payload: bytes, parameters: dict, allowed_stations: list[str]) -> dict:
    station = parameters["fmisid"]
    if station not in allowed_stations or parameters != request_parameters(parameters["starttime"], parameters["endtime"], station=station, timestep=10):
        raise ValueError("Request differs from the accepted station/ten-minute contract")
    inspection = inspect_response(payload, parameters["starttime"], parameters["endtime"], station, timestep=10)
    if inspection["duplicate_key_rows"]:
        raise ValueError("Duplicate weather source keys are not accepted")
    first, last = utc_time(parameters["starttime"]), utc_time(parameters["endtime"])
    rows = []
    for index, point in enumerate(ET.fromstring(payload).findall(".//wml:MeasurementTVP", NS), 1):
        timestamp = utc_time(point.findtext("wml:time", namespaces=NS))
        if not first <= timestamp < last:
            continue
        raw_value = point.findtext("wml:value", namespaces=NS)
        try:
            number = Decimal(raw_value)
        except InvalidOperation:
            raise ValueError("Invalid source measurement") from None
        if not number.is_finite():
            if raw_value.lower() != "nan":
                raise ValueError("Only declared source NaN is supported")
            number, quality = None, "source_nan"
        else:
            quality = "observed"
        rows.append((station, "t2m", timestamp, number, raw_value, index, quality))
    return {"rows": sorted(rows, key=lambda row: row[2]), "inspection": inspection,
            "station_id": station, "start_utc": first, "end_utc_exclusive": last}


def load_snapshot(connection, run_id, snapshot, prepared: dict, settings: dict) -> int:
    inspection = prepared["inspection"]
    coverage = inspection["coverage_by_station"][prepared["station_id"]]
    expected_header = (settings["weather_contract"]["parser_version"], prepared["station_id"],
                       prepared["start_utc"], prepared["end_utc_exclusive"],
                       coverage["expected_samples"], coverage["returned_distinct_samples"],
                       coverage["missing_value_samples"], coverage["absent_samples"],
                       inspection["out_of_scope_points"], inspection["station_metadata"][prepared["station_id"]])
    previous = connection.execute("""SELECT parser_version, station_id, start_utc, end_utc_exclusive,
        expected_samples, returned_samples, source_nan_samples, absent_samples,
        excluded_endpoint_samples, station_metadata FROM ops.weather_snapshot_load WHERE snapshot_id = %s""", (snapshot,)).fetchone()
    if previous is not None and previous != expected_header:
        raise ValueError("Existing weather snapshot metadata differs from source/configuration")
    inserted = 0
    if previous is None:
        connection.execute("""INSERT INTO ops.weather_snapshot_load
            (snapshot_id, first_loaded_run_id, contract_sha256, parser_version, station_id,
             parameter_id, unit, start_utc, end_utc_exclusive, timestep_minutes, expected_samples,
             returned_samples, source_nan_samples, absent_samples, excluded_endpoint_samples, station_metadata)
            VALUES (%s,%s,%s,%s,%s,'t2m','degC',%s,%s,10,%s,%s,%s,%s,%s,%s)""",
            (snapshot, run_id, settings["configuration_identity"]["weather_contract_sha256"],
             *expected_header[:-1], Jsonb(expected_header[-1])))
        with connection.cursor() as cursor:
            cursor.executemany("""INSERT INTO silver.weather_observation
                (snapshot_id, station_id, parameter_id, observed_at_utc, temperature_c,
                 source_value, source_point_index, source_quality, first_loaded_run_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                [(snapshot, *row, run_id) for row in prepared["rows"]])
            inserted = cursor.rowcount
    actual = connection.execute("""SELECT station_id, parameter_id, observed_at_utc, temperature_c,
        source_value, source_point_index, source_quality FROM silver.weather_observation
        WHERE snapshot_id = %s ORDER BY observed_at_utc""", (snapshot,)).fetchall()
    if actual != prepared["rows"]:
        raise ValueError("Stored weather rows differ from their immutable source revision")
    return inserted


def ingest_weather(connection, root: Path, settings: dict, paths: list[Path] | None = None,
                   acquisition_parameters: dict | None = None) -> dict:
    if not connection.autocommit or bool(paths) == (acquisition_parameters is not None):
        raise ValueError("Use an autocommit connection and exactly one input mode")
    if paths and len(paths) > settings["weather_contract"]["maximum_batch_manifests"]:
        raise ValueError("Weather batch exceeds the declared manifest bound")
    identity = code_identity(root)
    run_id = begin_run(connection, "ingest_fmi_weather", settings["configuration_sha256"], json.dumps(identity, sort_keys=True))
    counts = {"requested_manifests": len(paths) if paths else 1, "inserted_rows": 0}
    try:
        if acquisition_parameters is not None:
            if acquisition_parameters["fmisid"] not in settings["weather_contract"]["allowed_station_ids"]:
                raise ValueError("Station is outside the accepted ingestion scope")
            if acquisition_parameters != request_parameters(acquisition_parameters["starttime"], acquisition_parameters["endtime"], station=acquisition_parameters["fmisid"], timestep=10):
                raise ValueError("Unsupported acquisition request")
            _, path = acquire_sample(acquisition_parameters, settings["raw_directory"],
                                     project_path(root, "experiments/source-audit/fmi-ingestion-manifests"))
            paths = [path]
        with connection.transaction():
            # Serialize this small local loader; do not hold its lock during HTTP acquisition.
            connection.execute("SELECT pg_advisory_xact_lock(hashtext('fmi_weather_ingestion'))")
            seen, acquisitions = set(), set()
            counts.update(source_rows=0, finite_rows=0, source_nan_rows=0, absent_samples=0, excluded_endpoint_samples=0)
            for path in paths:
                record = inspect_manifest(root, path, settings)
                payload = project_path(root, record["raw_locator"]).read_bytes()
                if hashlib.sha256(payload).hexdigest() != record["content_sha256"]:
                    raise ValueError("Source changed after manifest verification")
                prepared = typed_points(payload, record["request_parameters"], settings["weather_contract"]["allowed_station_ids"])
                snapshot, acquisition = register_acquisition(connection, run_id, record)
                acquisitions.add(acquisition)
                if snapshot in seen:
                    continue
                seen.add(snapshot)
                counts["inserted_rows"] += load_snapshot(connection, run_id, snapshot, prepared, settings)
                coverage = prepared["inspection"]["coverage_by_station"][prepared["station_id"]]
                counts["source_rows"] += len(prepared["rows"])
                counts["finite_rows"] += coverage["valid_samples"]
                counts["source_nan_rows"] += coverage["missing_value_samples"]
                counts["absent_samples"] += coverage["absent_samples"]
                counts["excluded_endpoint_samples"] += prepared["inspection"]["out_of_scope_points"]
            counts.update(distinct_snapshots=len(seen), unique_acquisitions=len(acquisitions),
                          replayed_rows=counts["source_rows"] - counts["inserted_rows"])
            finish_run(connection, run_id, counts)
    except ERRORS:
        finish_run(connection, run_id, {"requested_manifests": counts["requested_manifests"], "inserted_rows": 0}, "FMI_INGESTION_FAILED")
        raise
    return {"run_id": str(run_id), "status": "succeeded", "counts": counts,
            "configuration_sha256": settings["configuration_sha256"], "configuration_identity": settings["configuration_identity"],
            "code_identity": identity, "scope": "FMI source-resolution Silver revisions; no hourly/Gold publication or E1-E7 result"}
