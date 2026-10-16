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
from ingestion.provenance import record_manifests
from tools.weather_fixture_checks import check_weather
from tools.publication_fixture_checks import check_publication


def check_acquisitions(connection) -> list[str]:
    """Manufactured CSV/acquisition records in the invocation's isolated database."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        raw = root / "data/raw/source-documents"
        raw.mkdir(parents=True)
        manifests = root / "experiments/source-audit"
        manifests.mkdir(parents=True)
        payload = b"datetime_utc;dh_MWh\n01.01.2025 00:00;10,0\n"
        digest = hashlib.sha256(payload).hexdigest()
        (raw / "synthetic.csv").write_bytes(payload)
        url = "https://www.helen.fi/contentassets/synthetic.csv"
        settings = {"source": "HELEN", "source_id": "HELEN_DISTRICT_HEATING", "raw_directory": raw,
                    "contract": {"snapshot_sha256": digest, "licence_and_acquisition": {"verified_current_download_url": url}},
                    "configuration_sha256": hashlib.sha256(b"synthetic acquisition configuration").hexdigest(),
                    "configuration_identity": {"fixture": "manufactured; not publisher evidence"}}
        manifest = {"sha256": digest, "bytes": len(payload), "raw_file": "data/raw/source-documents/synthetic.csv",
                    "url": url, "retrieved_at_utc": "2026-10-14T12:00:00Z"}
        first = manifests / "first.json"
        first.write_text(json.dumps(manifest), encoding="utf-8")
        initial = record_manifests(connection, root, [first, first], settings)
        replay = record_manifests(connection, root, [first], settings)
        if initial["counts"]["unique_acquisitions"] != 1 or initial["run_id"] == replay["run_id"]:
            raise ValueError("Acquisition replay did not retain the declared run/input grain")
        manifest["retrieved_at_utc"] = "2026-10-14T13:00:00Z"
        second = manifests / "second.json"
        second.write_text(json.dumps(manifest), encoding="utf-8")
        record_manifests(connection, root, [second], settings)
        counts = connection.execute("""SELECT
            (SELECT count(*) FROM ops.source_snapshot WHERE source_id = 'HELEN_DISTRICT_HEATING'),
            (SELECT count(*) FROM ops.source_acquisition),
            (SELECT count(*) FROM ops.run_acquisition)""").fetchone()
        if counts != (1, 2, 3):
            raise ValueError("Snapshot/acquisition/run identity accounting failed")
        results = ["acquisition_replay_and_distinct_retrieval_identity"]
        manifest["bytes"] += 1
        invalid = manifests / "invalid.json"
        invalid.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            record_manifests(connection, root, [first, invalid], settings)
        except ValueError:
            pass
        else:
            raise ValueError("Invalid acquisition batch was accepted")
        failed = connection.execute("""SELECT r.status, r.error_code,
            (SELECT count(*) FROM ops.run_input i WHERE i.run_id = r.run_id),
            (SELECT count(*) FROM ops.run_acquisition a WHERE a.run_id = r.run_id)
            FROM ops.pipeline_run r WHERE r.purpose = 'register_acquisition_evidence' AND r.status = 'failed'""").fetchall()
        if failed != [("failed", "ACQUISITION_REGISTRATION_FAILED", 0, 0)]:
            raise ValueError("Invalid acquisition left partial links or no failed-run record")
        results.append("acquisition_batch_failure_atomicity_and_durable_status")
        # Use the second retrieval, absent from the first run, to exercise the foreign
        # key rather than accidentally hitting that run's existing primary key.
        acquisition = connection.execute("SELECT acquisition_id FROM ops.source_acquisition WHERE manifest_sha256 = %s",
                                         (hashlib.sha256(second.read_bytes()).hexdigest(),)).fetchone()[0]
        try:
            with connection.transaction():
                connection.execute("INSERT INTO ops.run_acquisition VALUES (%s, %s, %s)",
                                   (initial["run_id"], acquisition, uuid4()))
        except psycopg.errors.ForeignKeyViolation:
            pass
        else:
            raise ValueError("Acquisition link accepted a mismatched snapshot")
        results.append("acquisition_snapshot_run_link_integrity")
        return results


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
                if first != ["001_operational_ledger.sql", "002_acquisition_provenance.sql", "003_weather_observations.sql", "004_weather_publication.sql", "005_reporting_boundary.sql"] or apply_migrations(connection) != []:
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
                results.extend(check_acquisitions(connection))
                results.extend(check_weather(connection))
                with connect(database) as reader:
                    results.extend(check_publication(connection, reader, database))
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
