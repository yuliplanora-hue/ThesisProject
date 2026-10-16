"""Bounded local replay of an explicit weather release; no live acquisition."""

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import psycopg

from ingestion.database import connect
from ingestion.provenance import code_identity, project_path
from ingestion.publication import read_plan


def validate_limits(runs, interval_seconds, timeout_seconds, max_seconds):
    for value, lower, upper in ((runs, 1, 24), (interval_seconds, 0, 3600),
                                (timeout_seconds, 1, 900), (max_seconds, 1, 3600)):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError("Schedule limits are outside their supported bounds")
    if (runs - 1) * interval_seconds >= max_seconds:
        raise ValueError("Requested intervals leave no time for the final execution")


def execute_release(root, plan_path, plan_sha256, expected_release, timeout_seconds):
    """A single owned child, no shell; subprocess.run kills and waits on timeout."""
    command = [sys.executable, "-m", "ingestion", "release", "publish",
               "--plan", str(plan_path), "--expected-plan-sha256", plan_sha256, "--json"]
    if expected_release:
        command.extend(["--expected-release", expected_release])
    environment = os.environ.copy()
    # Bound server work as well as the child process, including lock waits.
    environment["PGOPTIONS"] = f"-c statement_timeout={max(1, int(timeout_seconds * 1000))} -c lock_timeout=5000"
    try:
        result = subprocess.run(command, cwd=root, env=environment, capture_output=True,
                                text=True, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error_code": "CHILD_TIMEOUT"}
    if result.returncode:
        # Child stderr and raw exception text are deliberately not logged.
        return {"status": "failed", "error_code": "CHILD_FAILED", "exit_code": result.returncode}
    try:
        payload = json.loads(result.stdout)
        run_id, release_id = str(UUID(payload["run_id"])), str(UUID(payload["release_id"]))
        if (payload["status"] != "succeeded" or payload["counts"]["replayed_release"] is not True
                or release_id != expected_release or payload["plan_sha256"] != plan_sha256):
            raise ValueError("Invalid child result")
    except (ValueError, KeyError, TypeError, AttributeError):
        return {"status": "failed", "error_code": "CHILD_RESULT_INVALID"}
    return {"status": "succeeded", "run_id": run_id, "release_id": release_id,
            "replayed_release": payload["counts"]["replayed_release"]}


def run_schedule(root: Path, plan_path: Path, *, runs=1, interval_seconds=60,
                 timeout_seconds=300, max_seconds=900, connection_factory=connect,
                 execute=execute_release, monotonic=time.monotonic, sleep=time.sleep):
    """Stop on the first failure. Intervals are delays after completion, not catch-up ticks."""
    validate_limits(runs, interval_seconds, timeout_seconds, max_seconds)
    root = root.resolve()
    path = project_path(root, plan_path)
    plan, digest = read_plan(root, path)
    directory = project_path(root, "experiments/source-audit/schedule-runs")
    directory.mkdir(parents=True, exist_ok=True)
    schedule_id = str(uuid4())
    output = directory / (schedule_id + ".json")
    report = {"schedule_id": schedule_id, "status": "running", "started_at_utc": _now(),
              "plan_sha256": digest, "stream_id": plan["stream_id"], "ticks": [],
              "limits": {"runs": runs, "interval_seconds": interval_seconds,
                         "timeout_seconds": timeout_seconds, "max_seconds": max_seconds},
              "code_identity": code_identity(root)}

    def save():
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, output)

    save()
    deadline = monotonic() + max_seconds
    try:
        with connection_factory() as connection:
            connection.execute("SET statement_timeout = '5s'")
            locked = connection.execute("SELECT pg_try_advisory_lock(hashtext('weather_schedule'),hashtext(%s))",
                                        (plan["stream_id"],)).fetchone()[0]
            if not locked:
                report.update(status="failed", error_code="SCHEDULE_ALREADY_RUNNING")
            else:
                try:
                    # Require an established accepted checkpoint; initial publication is deliberate.
                    head = connection.execute("""SELECT h.release_id,r.plan_sha256 FROM ops.accepted_release h
                        JOIN ops.release r USING(release_id) WHERE h.stream_id=%s""",
                                              (plan["stream_id"],)).fetchone()
                    if not head or head[1] != digest:
                        raise ValueError("Publish and review this exact plan before scheduling")
                    expected = str(head[0])
                    report["initial_release_id"] = expected
                    for index in range(runs):
                        if index:
                            remaining = deadline - monotonic()
                            if remaining <= interval_seconds:
                                report.update(status="failed", error_code="SCHEDULE_DEADLINE")
                                break
                            sleep(interval_seconds)
                        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                            report.update(status="failed", error_code="PLAN_CHANGED")
                            break
                        remaining = deadline - monotonic()
                        if remaining <= 0:
                            report.update(status="failed", error_code="SCHEDULE_DEADLINE")
                            break
                        connection.execute("SELECT 1")
                        tick = {"number": index + 1, "started_at_utc": _now()}
                        report["ticks"].append(tick)
                        save()
                        tick.update(execute(root, path, digest, expected, min(timeout_seconds, remaining)))
                        tick["completed_at_utc"] = _now()
                        save()
                        if tick["status"] != "succeeded":
                            report.update(status="failed", error_code=tick["error_code"])
                            break
                        expected = tick["release_id"]
                    else:
                        report["status"] = "succeeded"
                finally:
                    connection.execute("SELECT pg_advisory_unlock(hashtext('weather_schedule'),hashtext(%s))",
                                       (plan["stream_id"],))
    except KeyboardInterrupt:
        report.update(status="failed", error_code="SCHEDULE_INTERRUPTED")
    except (ValueError, KeyError, TypeError, OSError, psycopg.Error) as exc:
        report.update(status="failed", error_code="SCHEDULE_FAILED", error_type=type(exc).__name__)
    report["completed_at_utc"] = _now()
    save()
    return report


def _now():
    return datetime.now(timezone.utc).isoformat()
