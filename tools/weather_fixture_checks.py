"""Manufactured weather loader checks; invoked only in the isolated test database."""

import hashlib
import json
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import UUID

import psycopg

from ingestion.fmi import ENDPOINT, inspect_response, request_parameters
from ingestion.provenance import load_configuration
from ingestion.weather import ingest_weather, weather_settings


def fixture_xml(value="-1.1234567890123456789"):
    return f'''<f:FeatureCollection xmlns:f="http://www.opengis.net/wfs/2.0"
      xmlns:t="http://xml.fmi.fi/namespace/om/atmosphericfeatures/1.1"
      xmlns:g="http://www.opengis.net/gml/3.2" xmlns:o="http://www.opengis.net/om/2.0"
      xmlns:w="http://www.opengis.net/waterml/2.0" xmlns:x="http://www.w3.org/1999/xlink">
      <f:member><o:Observation><o:observedProperty x:href="https://opendata.fmi.fi/meta?param=t2m"/>
      <t:Location><g:identifier codeSpace="http://xml.fmi.fi/namespace/stationcode/fmisid">100971</g:identifier>
      <g:name codeSpace="http://xml.fmi.fi/namespace/locationcode/name">Manufactured station</g:name></t:Location>
      <g:Point><g:pos>60.0 25.0</g:pos></g:Point><w:MeasurementTimeseries>
      <w:MeasurementTVP><w:time>2025-01-01T00:00:00Z</w:time><w:value>{value}</w:value></w:MeasurementTVP>
      <w:MeasurementTVP><w:time>2025-01-01T00:20:00Z</w:time><w:value>NaN</w:value></w:MeasurementTVP>
      <w:MeasurementTVP><w:time>2025-01-01T01:00:00Z</w:time><w:value>2</w:value></w:MeasurementTVP>
      </w:MeasurementTimeseries></o:Observation></f:member></f:FeatureCollection>'''.encode()


def check_weather(connection) -> list[str]:
    # This generated directory is the explicit test target, never a working data directory.
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        (root/"config").mkdir()
        for name in ("foundation.json","fmi-source-contract.json","weather-ingestion.json"):
            shutil.copy2(Path("config")/name,root/"config"/name)
        raw = root/"data/raw/fmi-feasibility"
        manifests = root/"experiments/source-audit"
        raw.mkdir(parents=True)
        manifests.mkdir(parents=True)
        settings = weather_settings(root,load_configuration(root,"FMI",Path("config/foundation.json")))
        parameters = request_parameters("2025-01-01T00:00:00Z","2025-01-01T01:00:00Z",station="100971",timestep=10)
        def save(payload, name):
            digest = hashlib.sha256(payload).hexdigest()
            (raw/(digest+".xml")).write_bytes(payload)
            manifest = {"source":"FMI","status":"inspected","parameters":parameters,
                "response_sha256":digest,"response_bytes":len(payload),"snapshot_file":digest+".xml",
                "retrieval":{"request_url":ENDPOINT+"?"+urlencode(parameters),"http_status":200,"attempts":1,"retrieved_at_utc":"2026-10-14T12:00:00Z"},
                "inspection":inspect_response(payload,parameters["starttime"],parameters["endtime"],"100971",timestep=10)}
            path = manifests/name
            path.write_text(json.dumps(manifest),encoding="utf-8")
            return path,manifest
        first, manifest = save(fixture_xml(),"first.json")
        initial = ingest_weather(connection,root,settings,[first])
        counts = initial["counts"]
        if (counts["inserted_rows"],counts["finite_rows"],counts["source_nan_rows"],counts["absent_samples"],counts["excluded_endpoint_samples"]) != (2,1,1,4,1):
            raise ValueError("Known weather accounting failed")
        rows = connection.execute("SELECT temperature_c,source_value,source_point_index,source_quality,first_loaded_run_id FROM silver.weather_observation ORDER BY observed_at_utc").fetchall()
        if rows != [(Decimal("-1.1234567890123456789"),"-1.1234567890123456789",1,"observed",UUID(initial["run_id"])),(None,"NaN",2,"source_nan",UUID(initial["run_id"]))]:
            raise ValueError("Decimal/source-value/NaN/lineage fidelity failed")
        results = ["weather_typed_values_missingness_and_lineage"]
        replay = ingest_weather(connection,root,settings,[first,first])
        if replay["counts"]["inserted_rows"] != 0 or replay["counts"]["replayed_rows"] != 2:
            raise ValueError("Weather replay inserted rows")
        if rows != connection.execute("SELECT temperature_c,source_value,source_point_index,source_quality,first_loaded_run_id FROM silver.weather_observation ORDER BY observed_at_utc").fetchall():
            raise ValueError("Replay changed values or first-loaded lineage")
        results.append("weather_replay_preserves_content_and_first_lineage")
        second,_ = save(fixture_xml("-9"),"second.json")
        ingest_weather(connection,root,settings,[second])
        if connection.execute("SELECT count(*) FROM silver.weather_observation").fetchone()[0] != 4:
            raise ValueError("Corrected source revision overwrote prior history")
        results.append("weather_corrected_revision_retains_prior_history")
        third, _ = save(fixture_xml("-8"),"third.json")
        manifest["response_bytes"] += 1
        invalid = manifests/"invalid.json"
        invalid.write_text(json.dumps(manifest),encoding="utf-8")
        try:
            ingest_weather(connection,root,settings,[third,invalid])
        except ValueError:
            pass
        else:
            raise ValueError("Invalid weather batch accepted")
        if connection.execute("SELECT count(*) FROM silver.weather_observation").fetchone()[0] != 4:
            raise ValueError("Invalid weather batch left partial observations")
        failed = connection.execute("""SELECT r.error_code,(SELECT count(*) FROM ops.run_input i WHERE i.run_id=r.run_id)
            FROM ops.pipeline_run r WHERE purpose='ingest_fmi_weather' AND status='failed'""").fetchall()
        if failed != [("FMI_INGESTION_FAILED",0)]:
            raise ValueError("Failed weather batch state/links incorrect")
        results.append("weather_invalid_batch_atomicity_and_durable_failure")
        with patch("ingestion.weather.acquire_sample",side_effect=ValueError("controlled timeout")):
            try:
                ingest_weather(connection,root,settings,acquisition_parameters=parameters)
            except ValueError:
                pass
            else:
                raise ValueError("Acquisition failure accepted")
        if connection.execute("SELECT count(*) FROM ops.pipeline_run WHERE purpose='ingest_fmi_weather' AND status='failed'").fetchone()[0] != 2:
            raise ValueError("Acquisition failure did not retain failed status")
        results.append("weather_acquisition_failure_persists_run")
        snapshot = connection.execute("SELECT snapshot_id FROM ops.source_snapshot WHERE content_sha256=%s",(hashlib.sha256(fixture_xml()).hexdigest(),)).fetchone()[0]
        connection.execute("UPDATE silver.weather_observation SET temperature_c=7 WHERE snapshot_id=%s AND source_quality='observed'",(snapshot,))
        try:
            ingest_weather(connection,root,settings,[first])
        except ValueError:
            pass
        else:
            raise ValueError("Stored weather corruption accepted on replay")
        connection.execute("UPDATE silver.weather_observation SET temperature_c=%s WHERE snapshot_id=%s AND source_quality='observed'",(Decimal("-1.1234567890123456789"),snapshot))
        results.append("weather_replay_detects_stored_content_corruption")
        try:
            with connection.transaction():
                connection.execute("UPDATE silver.weather_observation SET temperature_c='Infinity'::numeric WHERE snapshot_id=%s AND source_quality='observed'",(snapshot,))
        except psycopg.errors.CheckViolation:
            pass
        else:
            raise ValueError("Database accepted infinite weather value")
        results.append("weather_database_finite_value_constraint")
        return results
