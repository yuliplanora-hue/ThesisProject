"""Source-faithful Helen intake with exhaustive quarantine; no physical conversion."""

import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from ingestion.database import begin_run, finish_run
from ingestion.provenance import code_identity, inspect_manifest, project_path, read_json, register_acquisition


def intake_settings(root, foundation, contract_path=Path("config/helen-ingestion.json")):
    contract, payload = read_json(project_path(root, contract_path))
    if contract != {"version":"0.1", "scope":"Local unconverted Helen source values and quarantine only",
        "parser_version":"helen-source-0.1", "maximum_bytes":10000000, "maximum_records":250000,
        "timestamp_timezone":"UTC", "interval_convention":"interval_end", "interval_hours":1,
        "duplicate_policy":"quarantine_all_rows_with_the_same_valid_label",
        "negative_policy":"retain_with_warning_without_physical_inference", "analytical_publication":False}:
        raise ValueError("Unsupported Helen intake contract")
    semantic = foundation["contract"]["semantic_contract"]
    if (foundation["source"] != "HELEN" or semantic["timestamp_timezone"] != "UTC"
            or semantic["interval_convention"] != "interval_end" or semantic["interval_duration_hours"] != 1
            or semantic["accepted_utc_mapping"] is not True or semantic["accepted_interval_label_mapping"] is not True):
        raise ValueError("Helen UTC/interval label mapping is not accepted")
    digest = hashlib.sha256(payload).hexdigest()
    identity = {**foundation["configuration_identity"], "helen_intake_contract_sha256":digest}
    return {**foundation, "intake_contract":contract, "intake_contract_sha256":digest,
            "configuration_identity":identity,
            "configuration_sha256":hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()}


def parse_records(payload, maximum_records=250000):
    if not payload or len(payload)>10000000:
        raise ValueError("Helen input is empty or exceeds the byte bound")
    reader = csv.reader(io.StringIO(payload.decode("utf-8-sig"), newline=""), delimiter=";", strict=True)
    try:
        if next(reader, None) != ["datetime_utc", "dh_MWh"]:
            raise ValueError("Helen header differs from the explicit schema")
        records=[]
        for index, fields in enumerate(reader, start=1):
            if index>maximum_records:
                raise ValueError("Helen input exceeds the record bound")
            reasons=[]
            if len(fields)!=2: reasons.append("wrong_field_count")
            raw_time=fields[0] if fields else ""
            raw_value=fields[1] if len(fields)>1 else ""
            timestamp=value=None
            try:
                if len(raw_time)>32: raise ValueError("Timestamp too long")
                timestamp=datetime.strptime(raw_time,"%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
                if timestamp.strftime("%d.%m.%Y %H:%M")!=raw_time: raise ValueError("Noncanonical timestamp")
            except ValueError:
                timestamp=None
                reasons.append("invalid_timestamp")
            if timestamp and timestamp.minute: reasons.append("off_hour")
            if len(raw_value)<=128 and re.fullmatch(r"[+-]?\d+(?:,\d+)?",raw_value):
                value=Decimal(raw_value.replace(",","."))
            else: reasons.append("invalid_measurement")
            records.append({"index":index,"line_end":reader.line_num,"fields":fields,"label":timestamp,
                "start":timestamp-timedelta(hours=1) if timestamp else None,"end":timestamp,
                "measurement":value,"reasons":reasons,
                "warnings":["negative_source_value"] if value is not None and value<0 else []})
    except (csv.Error, UnicodeError, OverflowError) as exc:
        raise ValueError("Helen input is not a supported bounded CSV") from exc
    duplicates=Counter(r["label"] for r in records if r["label"] is not None)
    for record in records:
        if record["label"] is not None and duplicates[record["label"]]>1:
            record["reasons"].append("duplicate_label")
        record["status"]="quarantined" if record["reasons"] else "valid"
    return records


def row_tuple(record):
    return (record["index"],record["line_end"],record["fields"],record["label"],record["start"],record["end"],
            record["measurement"],record["status"],record["reasons"],record["warnings"])


def load_source(connection, root, settings, manifest):
    if not connection.autocommit:
        raise ValueError("Helen intake requires an autocommit connection")
    identity=code_identity(root)
    run=begin_run(connection,"ingest_helen_source",settings["configuration_sha256"],json.dumps(identity,sort_keys=True))
    try:
        with connection.transaction():
            connection.execute("SELECT pg_advisory_xact_lock(hashtext('helen_source_ingestion'))")
            record=inspect_manifest(root,manifest,settings)
            raw=project_path(root,record["raw_locator"])
            payload=raw.read_bytes()
            if hashlib.sha256(payload).hexdigest()!=record["content_sha256"] or len(payload)!=record["raw_bytes"]:
                raise ValueError("Helen input changed after manifest inspection")
            records=parse_records(payload,settings["intake_contract"]["maximum_records"])
            counts={"source_rows":len(records),"valid_rows":sum(r["status"]=="valid" for r in records),
                    "quarantined_rows":sum(r["status"]=="quarantined" for r in records),
                    "negative_rows":sum(bool(r["warnings"]) for r in records)}
            snapshot,_=register_acquisition(connection,run,record)
            previous=connection.execute("""SELECT parser_version,intake_contract_sha256,source_rows,valid_rows,
                quarantined_rows,negative_rows FROM ops.helen_snapshot_load WHERE snapshot_id=%s""",(snapshot,)).fetchone()
            expected=(settings["intake_contract"]["parser_version"],settings["intake_contract_sha256"],
                      counts["source_rows"],counts["valid_rows"],counts["quarantined_rows"],counts["negative_rows"])
            if previous is not None and previous!=expected:
                raise ValueError("Previously loaded Helen metadata differs from retained input/contract")
            if previous is None:
                connection.execute("""INSERT INTO ops.helen_snapshot_load VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                                   (snapshot,run,*expected))
                with connection.cursor() as cursor:
                    cursor.executemany("""INSERT INTO silver.helen_source_record VALUES
                        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        [(snapshot,r["index"],r["line_end"],Jsonb(r["fields"]),r["label"],r["start"],r["end"],
                          r["measurement"],r["status"],r["reasons"],r["warnings"]) for r in records])
            actual=connection.execute("""SELECT source_record_index,source_line_end,source_fields,source_label_utc,
                interval_start_utc,interval_end_utc,source_measurement,row_status,rejection_reasons,warnings
                FROM silver.helen_source_record WHERE snapshot_id=%s ORDER BY source_record_index""",(snapshot,)).fetchall()
            if actual!=[row_tuple(r) for r in records]:
                raise ValueError("Stored Helen records differ from the raw source")
            counts.update(inserted_rows=0 if previous is not None else len(records),
                          replayed_rows=len(records) if previous is not None else 0)
            finish_run(connection,run,counts)
    except (ValueError,TypeError,KeyError,OSError,psycopg.Error,KeyboardInterrupt):
        finish_run(connection,run,{"input_links_committed":0},"HELEN_SOURCE_INGESTION_FAILED")
        raise
    return {"run_id":str(run),"snapshot_id":str(snapshot),"status":"succeeded","counts":counts,
            "code_identity":identity,"configuration_sha256":settings["configuration_sha256"],
            "configuration_identity":settings["configuration_identity"],
            "scope":"Unconverted Helen source values/quarantine only; no accepted energy/paired/Gold publication"}
