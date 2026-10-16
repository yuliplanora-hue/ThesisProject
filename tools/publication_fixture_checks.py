"""Publication faults and recovery in the invocation's isolated test database."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode
from unittest.mock import patch

from ingestion.fmi import ENDPOINT, inspect_response, request_parameters
from ingestion.provenance import load_configuration
from ingestion.publication import publish_weather
from ingestion.database import connect, connection_settings
from ingestion.scheduling import run_schedule
from ingestion.weather import ingest_weather, weather_settings
from tools.weather_fixture_checks import fixture_xml
from tools.permission_fixture_checks import check_permissions


def check_publication(connection, reader, database: str) -> list[str]:
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory).resolve()
        (root/"config").mkdir()
        for name in ("foundation.json","fmi-source-contract.json","weather-ingestion.json"):
            shutil.copy2(Path("config")/name,root/"config"/name)
        raw=root/"data/raw/fmi-feasibility"
        manifests=root/"experiments/source-audit"
        raw.mkdir(parents=True)
        manifests.mkdir(parents=True)
        settings=weather_settings(root,load_configuration(root,"FMI",Path("config/foundation.json")))
        def save(points,name,start="2025-01-01T00:00:00Z",end="2025-01-01T01:00:00Z"):
            original=fixture_xml().decode()
            prefix=original.split("<w:MeasurementTVP>")[0]
            suffix="</w:MeasurementTimeseries>"+original.split("</w:MeasurementTimeseries>")[1]
            payload=(prefix+"".join(f"<w:MeasurementTVP><w:time>{t}</w:time><w:value>{v}</w:value></w:MeasurementTVP>" for t,v in points)+suffix).encode()
            digest=hashlib.sha256(payload).hexdigest()
            (raw/(digest+".xml")).write_bytes(payload)
            params=request_parameters(start,end,station="100971",timestep=10)
            manifest={"source":"FMI","status":"inspected","parameters":params,"response_sha256":digest,
                "response_bytes":len(payload),"snapshot_file":digest+".xml",
                "retrieval":{"request_url":ENDPOINT+"?"+urlencode(params),"http_status":200,"attempts":1,"retrieved_at_utc":"2026-10-14T12:00:00Z"},
                "inspection":inspect_response(payload,start,end,"100971",timestep=10)}
            path=manifests/name
            path.write_text(json.dumps(manifest),encoding="utf-8")
            ingest_weather(connection,root,settings,[path])
            return digest
        base=save([("2025-01-01T00:00:00Z","1"),("2025-01-01T00:20:00Z","NaN")],"base.json")
        fixed=save([("2025-01-01T00:00:00Z","2"),("2025-01-01T00:20:00Z","NaN")],"fix.json")
        fill=save([("2025-01-01T00:10:00Z","3")],"fill.json")
        extension=save([("2025-01-01T01:00:00Z","4")],"extension.json","2025-01-01T01:00:00Z","2025-01-01T02:00:00Z")
        initial={"version":"0.1","scope":"FMI source-resolution weather points only","stream_id":"synthetic-publication",
            "station_id":"100971","parameter_id":"t2m","unit":"degC","timestep_minutes":10,
            "policy":"explicit_layers_no_implicit_deletion","publication_reason":"Manufactured publication controls",
            "start_utc":"2025-01-01T00:00:00Z","end_utc_exclusive":"2025-01-01T01:00:00Z",
            "layers":[{"name":"base","mode":"base","reason":"Frozen synthetic baseline","snapshots":[base]}]}
        def digest(p):
            return hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()
        def publish(p,**kwargs):
            return publish_weather(connection,root,p,digest(p),**kwargs)
        def visible():
            return reader.execute("SELECT release_id,observed_at_utc,temperature_c,source_quality FROM publication.current_weather_point WHERE stream_id='synthetic-publication' ORDER BY observed_at_utc").fetchall()
        def checkpoint():
            return reader.execute("SELECT release_id,completed_end_utc,plan_sha256,updated_at_utc FROM ops.publication_checkpoint WHERE stream_id='synthetic-publication'").fetchone()
        first=publish(initial)
        if (first["counts"]["expected_keys"],first["counts"]["observed_keys"],first["counts"]["source_nan_keys"],first["counts"]["source_absent_keys"])!=(6,1,1,4):
            raise ValueError("Expected weather grid/quality accounting failed")
        results=["publication_independent_grid_and_source_states"]
        original_view,original_checkpoint=visible(),checkpoint()
        replay=publish(initial)
        if not replay["counts"]["replayed_release"] or replay["release_id"]!=first["release_id"] or checkpoint()!=original_checkpoint or visible()!=original_view:
            raise ValueError("Publication replay changed release/content/checkpoint")
        results.append("publication_replay_keeps_release_and_checkpoint")
        conflict=json.loads(json.dumps(initial))
        conflict["layers"][0]["snapshots"]=[base,fixed]
        try:
            publish(conflict)
        except ValueError:
            pass
        else:
            raise ValueError("Unordered conflict was published")
        if visible()!=original_view or checkpoint()!=original_checkpoint:
            raise ValueError("Conflict changed accepted reporting state")
        results.append("publication_unresolved_conflict_preserves_previous_release")
        correction=json.loads(json.dumps(initial))
        correction["layers"].append({"name":"fix","mode":"correction","reason":"Explicit known key correction","snapshots":[fixed]})
        changed=publish(correction)
        if changed["counts"]["changed_keys"]!=1 or visible()[0][2]!=2:
            raise ValueError("Declared correction changed the wrong keys")
        if connection.execute("SELECT count(*) FROM publication.weather_point WHERE release_id=%s",(first["release_id"],)).fetchone()[0]!=6:
            raise ValueError("New release destroyed pinned old rows")
        results.append("publication_explicit_correction_and_pinned_old_release")
        backfill=json.loads(json.dumps(correction))
        backfill["end_utc_exclusive"]="2025-01-01T02:00:00Z"
        backfill["layers"].append({"name":"backfill","mode":"backfill","reason":"Add a missing key and extend history","snapshots":[fill,extension]})
        before_view,before_checkpoint=visible(),checkpoint()
        for point in ("before_publication","after_pointer_before_commit"):
            def fail(stage):
                if visible()!=before_view or checkpoint()!=before_checkpoint:
                    raise AssertionError("Separate reader saw uncommitted publication")
                if stage==point:
                    raise ValueError("Controlled candidate interruption")
            try:
                publish(backfill,fault_hook=fail)
            except ValueError as exc:
                if str(exc) != "Controlled candidate interruption":
                    raise
            else:
                raise ValueError("Controlled publication fault was ignored")
            if visible()!=before_view or checkpoint()!=before_checkpoint:
                raise ValueError("Candidate fault advanced pointer/checkpoint")
        results.append("publication_both_fault_points_hide_candidate_from_reader")
        recovered=publish(backfill,resume=True)
        clean=json.loads(json.dumps(backfill))
        clean["stream_id"]="synthetic-clean-rebuild"
        rebuilt=publish(clean)
        if recovered["content_sha256"]!=rebuilt["content_sha256"] or (recovered["counts"]["changed_keys"],recovered["counts"]["new_keys"],recovered["counts"]["observed_keys"])!=(1,6,3):
            raise ValueError("Backfill/recovery differs from clean final-source rebuild")
        results.append("publication_backfill_resume_matches_clean_rebuild")
        final_view,final_checkpoint=visible(),checkpoint()
        try:
            publish(backfill,expected_release=first["release_id"])
        except ValueError:
            pass
        else:
            raise ValueError("Stale expected release accepted")
        if visible()!=final_view or checkpoint()!=final_checkpoint:
            raise ValueError("Stale candidate changed checkpoint")
        results.append("publication_stale_parent_guard")
        crashed=json.loads(json.dumps(backfill))
        crashed["publication_reason"]="Controlled child-process interruption"
        crash_path=root/"config/crash.json"
        crash_path.write_text(json.dumps(crashed),encoding="utf-8")
        child='''import os,sys,json
from pathlib import Path
from ingestion.database import connect
from ingestion.publication import publish_weather
root=Path(sys.argv[1]);plan=json.loads(Path(sys.argv[2]).read_text())
def stop(stage):
    if stage=='after_pointer_before_commit': os._exit(47)
with connect() as conn: publish_weather(conn,root,plan,sys.argv[3],fault_hook=stop)
'''
        environment={**os.environ,"ENERGY_DB_NAME":database}
        result=subprocess.run([sys.executable,"-c",child,str(root),str(crash_path),digest(crashed)],env=environment,capture_output=True,timeout=30)
        if result.returncode!=47 or visible()!=final_view or checkpoint()!=final_checkpoint:
            raise ValueError("Killed child process did not preserve the previous release")
        # Wait briefly for this exact disconnected backend to leave pg_stat_activity.
        old_context=connection.execute("SELECT stage_counts FROM ops.pipeline_run WHERE purpose='publish_fmi_weather' AND status='running' AND configuration_sha256=%s",(digest(crashed),)).fetchone()[0]
        for _ in range(100):
            if connection.execute("SELECT 1 FROM pg_stat_activity WHERE pid=%s AND backend_start=%s",(old_context["backend_pid"],old_context["backend_started_at_utc"])).fetchone() is None:
                break
            time.sleep(0.01)
        resumed=publish(crashed,resume=True)
        if resumed["content_sha256"]!=recovered["content_sha256"] or connection.execute("SELECT count(*) FROM ops.pipeline_run WHERE error_code='WEATHER_PUBLICATION_ABANDONED'").fetchone()[0]!=1:
            raise ValueError("Abandoned-process resume failed")
        results.append("publication_abandoned_process_checkpoint_recovery")
        original_zone=connection.execute("SHOW TimeZone").fetchone()[0]
        try:
            connection.execute("SELECT set_config('TimeZone','Europe/Helsinki',false)")
            local=json.loads(json.dumps(backfill))
            local["stream_id"]="synthetic-timezone-check"
            if publish(local)["content_sha256"]!=recovered["content_sha256"]:
                raise ValueError("Release hash depends on database session timezone")
        finally:
            connection.execute("SELECT set_config('TimeZone',%s,false)",(original_zone,))
        results.append("publication_utc_hash_independent_of_session_timezone")
        # Execute the real module CLI against only this invocation's synthetic database/root.
        for name in ("ingestion", "sql"):
            shutil.copytree(Path(name), root/name, ignore=shutil.ignore_patterns("__pycache__"))
        schedule_path = root/"config/schedule.json"
        schedule_path.write_text(json.dumps(crashed, sort_keys=True), encoding="utf-8")
        factory = lambda: connect(database)
        reader.execute("SELECT pg_advisory_lock(hashtext('weather_schedule'),hashtext(%s))", (crashed["stream_id"],))
        try:
            blocked = run_schedule(root, schedule_path, connection_factory=factory)
            if blocked.get("error_code") != "SCHEDULE_ALREADY_RUNNING" or blocked["ticks"]:
                raise ValueError("Overlapping schedule started a child")
        finally:
            reader.execute("SELECT pg_advisory_unlock(hashtext('weather_schedule'),hashtext(%s))", (crashed["stream_id"],))
        results.append("schedule_cross_connection_lease_excludes_overlap")
        prior_view, prior_checkpoint = visible(), checkpoint()
        with patch.dict(os.environ, {"ENERGY_DB_NAME": database, "POSTGRES_PASSWORD": connection_settings()["password"]}):
            scheduled = run_schedule(root, schedule_path, runs=2, interval_seconds=0, connection_factory=factory)
        if (scheduled["status"] != "succeeded" or len(scheduled["ticks"]) != 2
                or len({tick["run_id"] for tick in scheduled["ticks"]}) != 2
                or any(tick["release_id"] != resumed["release_id"] for tick in scheduled["ticks"])
                or visible() != prior_view or checkpoint() != prior_checkpoint):
            raise ValueError("Scheduled child replay changed accepted state or failed")
        results.append("schedule_real_cli_replay_preserves_release_and_checkpoint")
        def failed_child(*args):
            return {"status": "failed", "error_code": "CONTROLLED_CHILD_FAILURE"}
        failed_schedule = run_schedule(root, schedule_path, runs=3, interval_seconds=0,
                                       connection_factory=factory, execute=failed_child)
        if (failed_schedule.get("error_code") != "CONTROLLED_CHILD_FAILURE"
                or len(failed_schedule["ticks"]) != 1 or visible() != prior_view or checkpoint() != prior_checkpoint):
            raise ValueError("Failed schedule did not stop with the previous checkpoint intact")
        # A second successful lease acquisition also verifies release after failure.
        with factory() as lease:
            if not lease.execute("SELECT pg_try_advisory_lock(hashtext('weather_schedule'),hashtext(%s))", (crashed["stream_id"],)).fetchone()[0]:
                raise ValueError("Failed schedule leaked its session lock")
        results.append("schedule_failure_stops_ticks_preserves_checkpoint_and_releases_lease")
        results.extend(check_permissions(connection, database, root, settings, manifests/"base.json", crashed))
        return results
