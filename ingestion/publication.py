"""Explicit weather revisions and transactionally accepted source-point releases."""

import hashlib
import json
import re
from datetime import timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from ingestion.database import begin_run, finish_run, register_input
from ingestion.fmi import request_parameters, utc_time
from ingestion.period_audit import plan_chunks
from ingestion.provenance import code_identity, project_path, read_json
from ingestion.weather import typed_points

ERRORS = (ValueError, TypeError, KeyError, AttributeError, OSError, psycopg.Error, KeyboardInterrupt)


def validate_plan(plan: dict) -> dict:
    required = {"version": "0.1", "scope": "FMI source-resolution weather points only",
                "parameter_id": "t2m", "unit": "degC", "timestep_minutes": 10,
                "policy": "explicit_layers_no_implicit_deletion"}
    if any(plan.get(key) != value for key, value in required.items()):
        raise ValueError("Unsupported publication plan")
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,62}", plan["stream_id"]) or plan["station_id"] not in ("100971", "100968"):
        raise ValueError("Invalid publication stream/station")
    plan_chunks(plan["start_utc"], plan["end_utc_exclusive"])
    if not isinstance(plan["publication_reason"], str) or not plan["publication_reason"].strip():
        raise ValueError("Declare why this source set should be published")
    layers = plan["layers"]
    if not isinstance(layers, list) or not 1 <= len(layers) <= 10:
        raise ValueError("Declare one base and bounded explicit overlay layers")
    count = 0
    for index, layer in enumerate(layers):
        if layer["mode"] not in (("base",) if index == 0 else ("correction", "backfill")):
            raise ValueError("Layer precedence must be explicitly declared")
        if not isinstance(layer["reason"], str) or not layer["reason"].strip() or not layer["name"]:
            raise ValueError("Each layer needs a name and precedence reason")
        snapshots = layer["snapshots"]
        if not isinstance(snapshots, list) or not snapshots or len(snapshots) != len(set(snapshots)):
            raise ValueError("Layer snapshots must be a nonempty unique list")
        if any(not isinstance(s, str) or not re.fullmatch(r"[0-9a-f]{64}", s) for s in snapshots):
            raise ValueError("Invalid selected snapshot hash")
        count += len(snapshots)
    if count > 220:
        raise ValueError("Publication source set exceeds its local bound")
    return plan


def read_plan(root: Path, path: Path) -> tuple[dict, str]:
    plan, payload = read_json(project_path(root, path))
    return validate_plan(plan), hashlib.sha256(payload).hexdigest()


def merge_layers(layers: list[list[tuple]], start: str, end: str) -> tuple[list[tuple], set]:
    first, last = utc_time(start), utc_time(end)
    selected, overlay_keys = {}, set()
    for index, rows in enumerate(layers):
        local = {}
        for timestamp, number, quality, snapshot, point_index in rows:
            if not first <= timestamp < last:
                continue
            if (timestamp - first).total_seconds() % 600:
                raise ValueError("Published source key is off grid")
            candidate = (number, quality, snapshot, point_index)
            if timestamp in local and local[timestamp][:2] != candidate[:2]:
                raise ValueError("Conflicting source values within one declared layer")
            # Caller orders hashes, giving identical overlaps deterministic source lineage.
            local.setdefault(timestamp, candidate)
        if index:
            overlay_keys.update(local)
        selected.update(local)
    points = []
    timestamp = first
    while timestamp < last:
        points.append((timestamp, *selected.get(timestamp, (None, "source_absent", None, None))))
        timestamp += timedelta(minutes=10)
    return points, overlay_keys


def content_hash(points: list[tuple]) -> str:
    digest = hashlib.sha256()
    for timestamp, number, quality, *_ in points:
        value = None
        if number is not None:
            value = format(number, "f")
            if "." in value:
                value = value.rstrip("0").rstrip(".")
            if number == 0:
                value = "0"
        digest.update((json.dumps([timestamp.astimezone(timezone.utc).isoformat(), value, quality], separators=(",", ":")) + "\n").encode())
    return digest.hexdigest()


def source_layers(connection, root: Path, plan: dict, run_id) -> tuple[list, list]:
    layers, references = [], []
    cache = {}
    for index, layer in enumerate(plan["layers"]):
        points = []
        for digest in sorted(layer["snapshots"]):
            if digest not in cache:
                header = connection.execute("""SELECT s.snapshot_id,s.source_locator,l.start_utc,l.end_utc_exclusive,
                    l.station_id,l.parser_version,l.unit FROM ops.source_snapshot s
                    JOIN ops.weather_snapshot_load l USING(snapshot_id)
                    WHERE s.source_id='FMI_WEATHER' AND s.content_sha256=%s""", (digest,)).fetchone()
                if header is None or header[4:] != (plan["station_id"], "fmi-point-0.1", "degC"):
                    raise ValueError("Selected weather revision is absent or incompatible")
                snapshot, locator, start, end, station, *_ = header
                raw = project_path(root, locator)
                if not raw.is_relative_to(project_path(root, "data/raw")) or raw.stat().st_size > 2_000_000:
                    raise ValueError("Invalid selected raw locator/size")
                payload = raw.read_bytes()
                if hashlib.sha256(payload).hexdigest() != digest:
                    raise ValueError("Selected source content checksum mismatch")
                parameters = request_parameters(start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat(), station=station, timestep=10)
                expected = typed_points(payload, parameters, [station])["rows"]
                actual = connection.execute("""SELECT station_id,parameter_id,observed_at_utc,temperature_c,
                    source_value,source_point_index,source_quality FROM silver.weather_observation
                    WHERE snapshot_id=%s ORDER BY observed_at_utc""", (snapshot,)).fetchall()
                if actual != expected:
                    raise ValueError("Selected Silver revision differs from its raw source")
                register_input(connection, run_id, "FMI_WEATHER", digest, locator)
                cache[digest] = (snapshot, [(r[2], r[3], r[6], snapshot, r[5]) for r in actual])
            snapshot, selected = cache[digest]
            references.append((snapshot, index))
            points.extend(selected)
        layers.append(points)
    return layers, references


def publish_weather(connection, root: Path, plan: dict, plan_sha256: str,
                    expected_release: str | None = None, resume: bool = False, fault_hook=None) -> dict:
    validate_plan(plan)
    if not connection.autocommit:
        raise ValueError("Use an autocommit connection for durable publication failure records")
    expected_uuid = UUID(expected_release) if expected_release is not None else None
    prior = connection.execute("SELECT release_id FROM ops.accepted_release WHERE stream_id=%s", (plan["stream_id"],)).fetchone()
    initial_parent = prior[0] if prior else None
    identity = code_identity(root)
    backend = connection.execute("SELECT pid,backend_start FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
    run_id = begin_run(connection, "publish_fmi_weather", plan_sha256, json.dumps(identity, sort_keys=True))
    candidate, parent = uuid4(), None
    context = {"candidate_release_id": str(candidate), "parent_release_id": str(initial_parent) if initial_parent else None,
               "backend_pid": backend[0], "backend_started_at_utc": backend[1].isoformat() if backend[1] else None}
    connection.execute("UPDATE ops.pipeline_run SET stage_counts=%s WHERE run_id=%s", (Jsonb(context), run_id))
    stage, counts = "select_sources", {}
    try:
        with connection.transaction():
            # Same lock as typed ingestion prevents a cooperative loader changing inputs mid-build.
            connection.execute("SELECT pg_advisory_xact_lock(hashtext('fmi_weather_ingestion'))")
            # Different weather streams also serialize their accepted-pointer updates.
            connection.execute("SELECT pg_advisory_xact_lock(hashtext('weather_publication'))")
            current = connection.execute("""SELECT r.release_id,r.plan_sha256,r.content_sha256,r.station_id,
                r.start_utc,r.end_utc_exclusive FROM ops.accepted_release h
                JOIN ops.release r USING(release_id) WHERE h.stream_id=%s""", (plan["stream_id"],)).fetchone()
            parent = current[0] if current else None
            if parent != initial_parent:
                raise ValueError("Accepted release changed after this attempt started")
            if expected_release is not None and expected_uuid != parent:
                raise ValueError("Accepted release changed; review the candidate against the current checkpoint")
            if resume:
                abandoned = connection.execute("""SELECT run_id,stage_counts FROM ops.pipeline_run
                    WHERE purpose='publish_fmi_weather' AND configuration_sha256=%s AND status='running'
                    AND run_id<>%s ORDER BY started_at_utc""", (plan_sha256, run_id)).fetchall()
                for old_run, old_context in abandoned:
                    old_parent = UUID(old_context["parent_release_id"]) if old_context["parent_release_id"] else None
                    alive = connection.execute("""SELECT 1 FROM pg_stat_activity WHERE pid=%s
                        AND (%s::timestamptz IS NULL OR backend_start=%s OR backend_start IS NULL)""",
                        (old_context["backend_pid"], old_context["backend_started_at_utc"], old_context["backend_started_at_utc"])).fetchone()
                    if alive or old_parent != parent:
                        raise ValueError("A matching attempt is still live or has a stale checkpoint")
                    record_failed_release(connection, UUID(old_context["candidate_release_id"]), old_run,
                        old_parent, plan, plan_sha256, {"failed_stage": "abandoned_process", "error_type": "BackendDisconnected"})
                    finish_run(connection, old_run, {**old_context, "failed_stage": "abandoned_process"}, "WEATHER_PUBLICATION_ABANDONED")
                previous = connection.execute("""SELECT parent_release_id FROM ops.release
                    WHERE stream_id=%s AND plan_sha256=%s AND status='failed'
                    ORDER BY completed_at_utc DESC,release_id DESC LIMIT 1""", (plan["stream_id"], plan_sha256)).fetchone()
                if previous is None or previous[0] != parent:
                    raise ValueError("No resumable failed plan against the current accepted release")
            layers, references = source_layers(connection, root, plan, run_id)
            points, overlay = merge_layers(layers, plan["start_utc"], plan["end_utc_exclusive"])
            digest = content_hash(points)
            counts = {"expected_keys": len(points), "observed_keys": sum(p[2] == "observed" for p in points),
                      "source_nan_keys": sum(p[2] == "source_nan" for p in points),
                      "source_absent_keys": sum(p[2] == "source_absent" for p in points),
                      "changed_keys": 0, "new_keys": len(points), "selected_snapshots": len({s for s, _ in references})}
            if current:
                if current[3] != plan["station_id"] or utc_time(plan["start_utc"]) > current[4] or utc_time(plan["end_utc_exclusive"]) < current[5]:
                    raise ValueError("A weather stream cannot change station or silently shrink its accepted window")
                before = connection.execute("""SELECT observed_at_utc,temperature_c,source_quality
                    FROM publication.weather_point WHERE release_id=%s ORDER BY observed_at_utc""", (parent,)).fetchall()
                old = {p[0]: p[1:] for p in before}
                counts["new_keys"] = sum(p[0] not in old for p in points)
                for timestamp, number, quality, *_ in points:
                    if timestamp not in old or old[timestamp] == (number, quality):
                        continue
                    if quality == "source_absent" and old[timestamp][1] != "source_absent":
                        raise ValueError("Omitted source rows cannot silently delete accepted observations")
                    if timestamp not in overlay:
                        raise ValueError("Changed accepted keys require an explicit correction/backfill layer")
                    counts["changed_keys"] += 1
            stage = "validate_candidate"
            if current and current[1:3] == (plan_sha256, digest):
                # Verify pinned values as well as source inputs before accepting replay.
                actual = connection.execute("""SELECT observed_at_utc,temperature_c,source_quality,snapshot_id,source_point_index
                    FROM publication.weather_point WHERE release_id=%s ORDER BY observed_at_utc""", (parent,)).fetchall()
                if actual != points:
                    raise ValueError("Accepted release content/lineage differs from the verified replay")
                release_id, replayed = parent, True
            else:
                release_id, replayed = candidate, False
                connection.execute("""INSERT INTO ops.release
                    (release_id,stream_id,build_run_id,parent_release_id,plan_sha256,plan,station_id,parameter_id,
                     start_utc,end_utc_exclusive,status,content_sha256,counts)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'t2m',%s,%s,'accepted',%s,%s)""",
                    (candidate, plan["stream_id"], run_id, parent, plan_sha256, Jsonb(plan), plan["station_id"],
                     utc_time(plan["start_utc"]), utc_time(plan["end_utc_exclusive"]), digest, Jsonb(counts)))
                with connection.cursor() as cursor:
                    cursor.executemany("INSERT INTO ops.release_source VALUES (%s,%s,%s)", [(candidate, snapshot, index) for snapshot, index in references])
                    cursor.executemany("""INSERT INTO publication.weather_point
                        (release_id,station_id,parameter_id,observed_at_utc,temperature_c,source_quality,snapshot_id,source_point_index)
                        VALUES (%s,%s,'t2m',%s,%s,%s,%s,%s)""", [(candidate, plan["station_id"], *point) for point in points])
                actual = connection.execute("""SELECT observed_at_utc,temperature_c,source_quality,snapshot_id,source_point_index
                    FROM publication.weather_point WHERE release_id=%s ORDER BY observed_at_utc""", (candidate,)).fetchall()
                if actual != points or content_hash(actual) != digest:
                    raise ValueError("Candidate keys/values/lineage differ from expected publication")
                stage = "before_publication"
                if fault_hook:
                    fault_hook(stage)
                connection.execute("""INSERT INTO ops.accepted_release VALUES (%s,%s)
                    ON CONFLICT(stream_id) DO UPDATE SET release_id=EXCLUDED.release_id""", (plan["stream_id"], candidate))
                connection.execute("""INSERT INTO ops.publication_checkpoint
                    (stream_id,release_id,completed_end_utc,plan_sha256) VALUES (%s,%s,%s,%s)
                    ON CONFLICT(stream_id) DO UPDATE SET release_id=EXCLUDED.release_id,
                    completed_end_utc=EXCLUDED.completed_end_utc,plan_sha256=EXCLUDED.plan_sha256,updated_at_utc=now()""",
                    (plan["stream_id"], candidate, utc_time(plan["end_utc_exclusive"]), plan_sha256))
                stage = "after_pointer_before_commit"
                if fault_hook:
                    fault_hook(stage)
            counts.update(replayed_release=replayed, release_id=str(release_id))
            finish_run(connection, run_id, counts)
    except ERRORS as exc:
        failed_counts = {"failed_stage": stage, "error_type": type(exc).__name__, "candidate_release_id": str(candidate)}
        with connection.transaction():
            record_failed_release(connection, candidate, run_id, parent, plan, plan_sha256, failed_counts)
            finish_run(connection, run_id, failed_counts, "WEATHER_PUBLICATION_FAILED")
        raise
    return {"run_id": str(run_id), "release_id": str(release_id), "status": "succeeded", "counts": counts,
            "content_sha256": digest, "plan_sha256": plan_sha256, "code_identity": identity,
            "scope": "Accepted weather source-point release only; hourly/heat/BI Gold and final E1-E7 remain separate"}


def record_failed_release(connection, candidate, run_id, parent, plan, digest, counts):
    connection.execute("""INSERT INTO ops.release
        (release_id,stream_id,build_run_id,parent_release_id,plan_sha256,plan,station_id,parameter_id,
         start_utc,end_utc_exclusive,status,content_sha256,counts)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'t2m',%s,%s,'failed',NULL,%s)""",
        (candidate, plan["stream_id"], run_id, parent, digest, Jsonb(plan), plan["station_id"],
         utc_time(plan["start_utc"]), utc_time(plan["end_utc_exclusive"]), Jsonb(counts)))
