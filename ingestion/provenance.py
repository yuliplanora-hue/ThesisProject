"""Validate retained acquisitions and link them to operational runs, not facts."""

import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from ingestion.database import begin_run, finish_run, register_input
from ingestion.fmi import inspect_response, request_parameters, utc_time


def project_path(root: Path, value: str | Path) -> Path:
    """Only project-local files; do not register secrets or arbitrary external paths."""
    root = root.resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Evidence path is outside the project")
    return path


def read_json(path: Path) -> tuple[dict, bytes]:
    if path.stat().st_size > 2_000_000:
        raise ValueError("Metadata exceeds the size limit")
    payload = path.read_bytes()
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("Metadata must be a JSON object")
    return value, payload


def load_configuration(root: Path, source: str, configuration: Path,
                       raw_directory: Path | None = None) -> dict:
    path = project_path(root, configuration)
    config, config_bytes = read_json(path)
    if config["version"] != "0.1" or source not in ("FMI", "HELEN"):
        raise ValueError("Unsupported foundation configuration")
    settings = config["sources"][source]
    if settings["source_id"] != {"FMI": "FMI_WEATHER", "HELEN": "HELEN_DISTRICT_HEATING"}[source]:
        raise ValueError("Unexpected source identity")
    raw = project_path(root, raw_directory if raw_directory is not None else settings["raw_directory"])
    if not raw.is_relative_to(project_path(root, "data/raw")):
        raise ValueError("Raw evidence must be under data/raw")
    contract_path = project_path(root, settings["contract"])
    contract, contract_bytes = read_json(contract_path)
    identity = {"foundation_sha256": hashlib.sha256(config_bytes).hexdigest(),
                "source": source, "raw_directory": raw.relative_to(root).as_posix(),
                "contract_sha256": hashlib.sha256(contract_bytes).hexdigest()}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"source": source, "source_id": settings["source_id"], "raw_directory": raw,
            "contract": contract, "configuration_identity": identity,
            "configuration_sha256": digest}


def inspect_manifest(root: Path, manifest_path: Path, settings: dict) -> dict:
    root = root.resolve()
    path = project_path(root, manifest_path)
    if not path.is_relative_to(project_path(root, "experiments/source-audit")):
        raise ValueError("Acquisition manifests must be under experiments/source-audit")
    manifest, manifest_bytes = read_json(path)
    source = settings["source"]
    if source == "FMI":
        if manifest["source"] != "FMI" or manifest["status"] != "inspected":
            raise ValueError("Only inspected FMI acquisitions are supported")
        parameters = manifest["parameters"]
        expected = request_parameters(parameters["starttime"], parameters["endtime"],
                                      station=parameters["fmisid"], timestep=int(parameters["timestep"]))
        if parameters != expected:
            raise ValueError("FMI request parameters differ from the supported query")
        digest, size = manifest["response_sha256"], manifest["response_bytes"]
        filename = manifest["snapshot_file"]
        if filename != digest + ".xml":
            raise ValueError("FMI snapshot filename must match its content hash")
        raw = project_path(root, settings["raw_directory"] / filename)
        retrieval = manifest["retrieval"]
        if retrieval["http_status"] != 200 or not 1 <= retrieval["attempts"] <= 3:
            raise ValueError("Invalid FMI acquisition status")
        url = retrieval["request_url"]
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "opendata.fmi.fi" or parsed.path != "/wfs" or parsed.fragment:
            raise ValueError("Unsupported FMI request URL")
        if parse_qs(parsed.query, strict_parsing=True) != {k: [v] for k, v in expected.items()}:
            raise ValueError("FMI URL differs from the retained request parameters")
        retrieved = utc_time(retrieval["retrieved_at_utc"])
        status, max_size = "inspected", 2_000_000
    else:
        digest, size = manifest["sha256"], manifest["bytes"]
        raw = project_path(root, manifest["raw_file"])
        url = manifest["url"]
        contract = settings["contract"]
        if digest != contract["snapshot_sha256"] or url != contract["licence_and_acquisition"]["verified_current_download_url"]:
            raise ValueError("Helen acquisition differs from the verified current snapshot")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "www.helen.fi" or parsed.query or parsed.fragment:
            raise ValueError("Unsupported Helen acquisition URL")
        retrieved = utc_time(manifest["retrieved_at_utc"])
        parameters, status, max_size = {}, "acquired", 10_000_000
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid source content hash")
    if type(size) is not int or not 0 < size <= max_size:
        raise ValueError("Invalid source byte count")
    if not raw.is_relative_to(settings["raw_directory"]) or raw.stat().st_size != size:
        raise ValueError("Raw path or byte count does not match the acquisition")
    payload = raw.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("Raw content checksum mismatch")
    if source == "FMI":
        inspection = inspect_response(payload, parameters["starttime"], parameters["endtime"],
                                      parameters["fmisid"], int(parameters["timestep"]))
        if inspection != manifest["inspection"] or inspection["duplicate_key_rows"]:
            raise ValueError("FMI inspection differs or duplicate keys were returned")
    return {"source_id": settings["source_id"], "content_sha256": digest,
            "raw_locator": raw.relative_to(root).as_posix(), "raw_bytes": size,
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "manifest_locator": path.relative_to(root).as_posix(),
            "retrieved_at_utc": retrieved, "request_url": url,
            "request_parameters": parameters, "source_status": status}


def code_identity(root: Path) -> dict:
    paths = sorted((root / "ingestion").glob("*.py")) + sorted((root / "sql/migrations").glob("*.sql"))
    identity = {"python_version": platform.python_version(), "psycopg_version": psycopg.__version__,
                "files_sha256": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=5)
        identity.update(git_commit=commit.stdout.strip() if commit.returncode == 0 else None,
                        git_worktree_dirty=bool(dirty.stdout.strip()) if dirty.returncode == 0 else None)
    except (OSError, subprocess.TimeoutExpired):
        identity.update(git_commit=None, git_worktree_dirty=None)
    return identity


def register_acquisition(connection, run_id, record: dict):
    """Attach verified evidence within the caller's transaction, reusing identities."""
    snapshot = register_input(connection, run_id, record["source_id"], record["content_sha256"], record["raw_locator"])
    acquisition = connection.execute("""INSERT INTO ops.source_acquisition
        (acquisition_id, snapshot_id, manifest_sha256, manifest_locator, raw_bytes,
         retrieved_at_utc, request_url, request_parameters, source_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (snapshot_id, manifest_sha256) DO UPDATE
        SET manifest_sha256 = EXCLUDED.manifest_sha256 RETURNING acquisition_id""",
        (uuid4(), snapshot, record["manifest_sha256"], record["manifest_locator"], record["raw_bytes"],
         record["retrieved_at_utc"], record["request_url"], Jsonb(record["request_parameters"]), record["source_status"])).fetchone()[0]
    connection.execute("""INSERT INTO ops.run_acquisition (run_id, acquisition_id, snapshot_id)
        VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""", (run_id, acquisition, snapshot))
    return snapshot, acquisition


def record_manifests(connection, root: Path, paths: list[Path], settings: dict) -> dict:
    if not paths or not connection.autocommit:
        raise ValueError("Require acquisition manifests and an autocommit connection for durable failed-run records")
    identity = code_identity(root)
    run_id = begin_run(connection, "register_acquisition_evidence", settings["configuration_sha256"],
                       json.dumps(identity, sort_keys=True))
    counts = {"requested_manifests": len(paths)}
    try:
        # A bad later input rolls back all input/acquisition links, retaining the failed run.
        with connection.transaction():
            records = [inspect_manifest(root, path, settings) for path in paths]
            unique = {(r["content_sha256"], r["manifest_sha256"]): r for r in records}
            for record in unique.values():
                register_acquisition(connection, run_id, record)
            counts.update(unique_acquisitions=len(unique),
                          distinct_snapshots=len({r["content_sha256"] for r in unique.values()}),
                          analytical_rows_loaded=0)
            finish_run(connection, run_id, counts)
    except (ValueError, TypeError, KeyError, AttributeError, OSError, psycopg.Error):
        finish_run(connection, run_id, {"requested_manifests": len(paths), "registered_acquisitions": 0}, "ACQUISITION_REGISTRATION_FAILED")
        raise
    return {"run_id": str(run_id), "status": "succeeded", "counts": counts,
            "configuration_sha256": settings["configuration_sha256"],
            "configuration_identity": settings["configuration_identity"], "code_identity": identity,
            "scope": "Operational acquisition registration only; not analytical loading or E1-E7"}
