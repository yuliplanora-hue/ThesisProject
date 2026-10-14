"""Apply metadata migrations or verify the foundation in a temporary isolated database."""

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from ingestion.database import apply_migrations, begin_run, connect, finish_run, register_input


def check_foundation() -> dict:
    # Never run destructive test cleanup against an existing/working database.
    database = "energy_foundation_test_" + uuid4().hex
    created = False
    results = []
    with connect() as admin:
        try:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
            created = True
            with connect(database) as connection:
                first = apply_migrations(connection)
                if first != ["001_operational_ledger.sql"] or apply_migrations(connection) != []:
                    raise ValueError("Fresh build or migration replay did not match expectations")
                results.append("fresh_migration_and_replay")
                with tempfile.TemporaryDirectory() as directory:
                    altered = Path(directory) / "001_operational_ledger.sql"
                    altered.write_bytes(Path("sql/migrations/001_operational_ledger.sql").read_bytes() + b"\n-- changed fixture\n")
                    try:
                        apply_migrations(connection, Path(directory))
                    except ValueError:
                        pass
                    else:
                        raise ValueError("Changed applied migration was accepted")
                results.append("changed_migration_checksum_rejected")
                digest = hashlib.sha256(b"synthetic foundation fixture").hexdigest()
                first_run = begin_run(connection, "synthetic_check", digest, "foundation-0.1")
                snapshot = register_input(connection, first_run, "SYNTHETIC", digest, "synthetic://fixture")
                if register_input(connection, first_run, "SYNTHETIC", digest, "synthetic://fixture") != snapshot:
                    raise ValueError("Repeated input changed snapshot identity")
                finish_run(connection, first_run, {"input_rows": 2})
                second_run = begin_run(connection, "synthetic_check", digest, "foundation-0.1")
                if register_input(connection, second_run, "SYNTHETIC", digest, "synthetic://fixture") != snapshot:
                    raise ValueError("Replay changed content snapshot identity")
                finish_run(connection, second_run, {"input_rows": 2})
                counts = connection.execute("""SELECT
                    (SELECT count(*) FROM ops.source_snapshot),
                    (SELECT count(*) FROM ops.pipeline_run),
                    (SELECT count(*) FROM ops.run_input)""").fetchone()
                if counts != (1, 2, 2):
                    raise ValueError("Snapshot/run/input grain check failed")
                results.append("snapshot_reuse_distinct_runs_unique_links")
                try:
                    finish_run(connection, second_run, {})
                except ValueError:
                    pass
                else:
                    raise ValueError("Completed run accepted another completion")
                results.append("completed_run_guard")
                failed = begin_run(connection, "synthetic_failure", digest, "foundation-0.1")
                finish_run(connection, failed, {"rejected_rows": 1}, "SYNTHETIC_SCHEMA_FAILURE")
                status = connection.execute("SELECT status, error_code FROM ops.pipeline_run WHERE run_id = %s", (failed,)).fetchone()
                if status != ("failed", "SYNTHETIC_SCHEMA_FAILURE"):
                    raise ValueError("Failed-run state did not persist")
                results.append("failure_status_persisted")
                try:
                    with connection.transaction():
                        register_input(connection, uuid4(), "ROLLBACK", digest, "synthetic://rollback")
                except psycopg.errors.ForeignKeyViolation:
                    pass
                else:
                    raise ValueError("Invalid run reference was accepted")
                if connection.execute("SELECT count(*) FROM ops.source_snapshot WHERE source_id = 'ROLLBACK'").fetchone()[0] != 0:
                    raise ValueError("Failed input transaction left a partial snapshot")
                results.append("foreign_key_failure_rolls_back_snapshot")
                migration_sha = hashlib.sha256(Path("sql/migrations/001_operational_ledger.sql").read_bytes()).hexdigest()
                return {"executed_at_utc": datetime.now(timezone.utc).isoformat(), "status": "pass",
                        "test_database": database, "checks": results, "psycopg_version": psycopg.__version__,
                        "postgres_version": connection.execute("SHOW server_version").fetchone()[0],
                        "migration_sha256": migration_sha, "scope": "operational foundation, not E1-E7"}
        finally:
            if created:
                # This exact UUID name was successfully created by this invocation.
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "check"))
    args = parser.parse_args()
    try:
        if args.command == "migrate":
            with connect() as connection:
                applied = apply_migrations(connection)
            print("Applied: " + (", ".join(applied) if applied else "no new migrations"))
        else:
            result = check_foundation()
            output = Path("experiments/source-audit/database-foundation.json")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"Foundation checks passed: {len(result['checks'])}; isolated test database removed")
            print(f"Saved {output}")
    except (ValueError, OSError, psycopg.Error) as exc:
        # Never print a raw connection exception/DSN or SQL parameter payload.
        print(f"Database operation failed ({type(exc).__name__}); verify local setup and migration state.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
