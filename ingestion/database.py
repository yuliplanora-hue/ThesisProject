"""Local operational ledger. Credentials never appear in command arguments or logs."""

import hashlib
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb


def connection_settings(env_file: Path = Path(".env"), environment=None) -> dict:
    environment = os.environ if environment is None else environment
    password = environment.get("POSTGRES_PASSWORD")
    if not password and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            if line.strip().startswith("POSTGRES_PASSWORD="):
                password = line.strip().split("=", 1)[1]
                if len(password) >= 2 and password[0] == password[-1] and password[0] in "\"'":
                    password = password[1:-1]
    if not password or password == "replace_with_a_local_password":
        raise ValueError("Set a local POSTGRES_PASSWORD in the ignored .env file or environment")
    try:
        port = int(environment.get("ENERGY_DB_PORT", "5432"))
    except ValueError:
        raise ValueError("ENERGY_DB_PORT must be a valid port number") from None
    if not 1 <= port <= 65535:
        raise ValueError("ENERGY_DB_PORT must be a valid port number")
    return {"host": environment.get("ENERGY_DB_HOST", "127.0.0.1"), "port": port,
            "dbname": environment.get("ENERGY_DB_NAME", "finnish_energy"),
            "user": environment.get("ENERGY_DB_USER", "energy"), "password": password,
            "connect_timeout": 5, "application_name": "finnish_energy_foundation"}


def connect(database: str | None = None):
    settings = connection_settings()
    if database is not None:
        settings["dbname"] = database
    return psycopg.connect(**settings, autocommit=True)


def apply_migrations(connection, directory: Path = Path("sql/migrations")) -> list[str]:
    files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    if not files:
        raise ValueError("No migration files found; run from the repository folder")
    applied = []
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(hashtext('finnish_energy_migrations'))")
        connection.execute("CREATE SCHEMA IF NOT EXISTS ops")
        connection.execute("""CREATE TABLE IF NOT EXISTS ops.schema_migration (
            name text PRIMARY KEY, content_sha256 text NOT NULL,
            applied_at_utc timestamptz NOT NULL DEFAULT now())""")
        for path in files:
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            previous = connection.execute("SELECT content_sha256 FROM ops.schema_migration WHERE name = %s", (path.name,)).fetchone()
            if previous:
                if previous[0] != digest:
                    raise ValueError("Applied migration checksum changed; add a new migration instead")
                continue
            connection.execute(payload.decode("utf-8"))
            connection.execute("INSERT INTO ops.schema_migration (name, content_sha256) VALUES (%s, %s)", (path.name, digest))
            applied.append(path.name)
    return applied


def begin_run(connection, purpose: str, configuration_sha256: str, code_version: str):
    run_id = uuid4()
    connection.execute("""INSERT INTO ops.pipeline_run
        (run_id, purpose, configuration_sha256, code_version) VALUES (%s, %s, %s, %s)""",
                       (run_id, purpose, configuration_sha256, code_version))
    return run_id


def register_input(connection, run_id, source_id: str, content_sha256: str, locator: str):
    with connection.transaction():
        connection.execute("""INSERT INTO ops.source_snapshot
            (snapshot_id, source_id, content_sha256, source_locator) VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_id, content_sha256) DO NOTHING""",
                           (uuid4(), source_id, content_sha256, locator))
        snapshot_id = connection.execute("""SELECT snapshot_id FROM ops.source_snapshot
            WHERE source_id = %s AND content_sha256 = %s""", (source_id, content_sha256)).fetchone()[0]
        connection.execute("""INSERT INTO ops.run_input (run_id, snapshot_id) VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", (run_id, snapshot_id))
    return snapshot_id


def finish_run(connection, run_id, counts: dict, error_code: str | None = None):
    row = connection.execute("""UPDATE ops.pipeline_run SET status = %s, completed_at_utc = now(),
        stage_counts = %s, error_code = %s WHERE run_id = %s AND status = 'running' RETURNING run_id""",
                             ("failed" if error_code else "succeeded", Jsonb(counts), error_code, run_id)).fetchone()
    if row is None:
        raise ValueError("Run is absent or already completed")
