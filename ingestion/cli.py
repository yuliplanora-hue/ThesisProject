"""Project CLI for the implemented database and provenance foundation."""

import argparse
import json
import sys
from pathlib import Path

import psycopg

from ingestion.database import apply_migrations, connect
from ingestion.provenance import inspect_manifest, load_configuration, project_path, record_manifests
from ingestion.fmi import request_parameters
from ingestion.weather import ingest_weather, period_manifest_paths, weather_settings
from ingestion.publication import publish_weather, read_plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    database = commands.add_parser("database", help="Migrate or check the operational database")
    database.add_argument("action", choices=("migrate", "check", "roles", "model-role"))
    database.add_argument("--model-role", default="energy_transformer")
    database.add_argument("--loader-role", default="energy_loader")
    database.add_argument("--reporter-role", default="energy_reporter")
    manifests = commands.add_parser("manifests", help="Inspect or record retained acquisition evidence")
    manifests.add_argument("action", choices=("inspect", "record"))
    manifests.add_argument("--source", choices=("FMI", "HELEN"), required=True)
    manifests.add_argument("--manifest", type=Path, action="append", required=True)
    manifests.add_argument("--configuration", type=Path, default=Path("config/foundation.json"))
    manifests.add_argument("--raw-directory", type=Path, help="Project-local raw directory override")
    weather = commands.add_parser("weather", help="Acquire/load typed FMI source-resolution revisions")
    weather.add_argument("action", choices=("load", "acquire"))
    inputs = weather.add_mutually_exclusive_group()
    inputs.add_argument("--manifest", type=Path, action="append")
    inputs.add_argument("--period-report", type=Path)
    weather.add_argument("--start")
    weather.add_argument("--end", help="Exclusive UTC end; acquire covers at most seven days")
    weather.add_argument("--station")
    weather.add_argument("--configuration", type=Path, default=Path("config/foundation.json"))
    weather.add_argument("--weather-contract", type=Path, default=Path("config/weather-ingestion.json"))
    weather.add_argument("--raw-directory", type=Path)
    helen = commands.add_parser("helen", help="Load unconverted Helen source values and quarantine")
    helen.add_argument("action", choices=("load",))
    helen.add_argument("--manifest", type=Path, required=True)
    helen.add_argument("--configuration", type=Path, default=Path("config/foundation.json"))
    helen.add_argument("--intake-contract", type=Path, default=Path("config/helen-ingestion.json"))
    helen.add_argument("--raw-directory", type=Path)
    release = commands.add_parser("release", help="Publish/resume an explicit weather source-point plan")
    release.add_argument("action", choices=("publish", "resume", "status"))
    release.add_argument("--plan", type=Path, default=Path("config/weather-release-plan.json"))
    release.add_argument("--expected-release", help="Require this accepted UUID before changing publication")
    release.add_argument("--json", action="store_true", help="Emit the successful release result as JSON")
    release.add_argument("--expected-plan-sha256", help="Require the exact reviewed plan bytes")
    schedule = commands.add_parser("schedule", help="Bounded replay of an already accepted weather stream")
    schedule.add_argument("--plan", type=Path, default=Path("config/weather-release-plan.json"))
    schedule.add_argument("--runs", type=int, default=1)
    schedule.add_argument("--interval-seconds", type=int, default=60)
    schedule.add_argument("--timeout-seconds", type=int, default=300)
    schedule.add_argument("--max-seconds", type=int, default=900)
    models = commands.add_parser("models", help="Build/check candidate dbt weather models")
    models.add_argument("action", choices=("build", "check"))
    models.add_argument("--release-id", help="Required accepted weather UUID for build")
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    try:
        if args.command == "models":
            if args.action == "check":
                if args.release_id:
                    raise ValueError("Isolated model checks do not take a working release")
                from tools.model_fixture_checks import check_models
                result = check_models()
                print(f"Model checks passed: {len(result['checks'])}; isolated database/role removed")
            else:
                if not args.release_id:
                    raise ValueError("Model build requires an explicit accepted release UUID")
                from ingestion.modeling import build_weather_models
                with connect() as connection:
                    result = build_weather_models(connection, root, args.release_id)
                print(f"Model build {result['run_id']}: {result['counts']['models']} models; {result['counts']['tests']} tests; candidate schema only")
            return 0
        if args.command == "helen":
            from ingestion.helen import intake_settings, load_source
            settings = intake_settings(root, load_configuration(root, "HELEN", args.configuration, args.raw_directory), args.intake_contract)
            with connect() as connection:
                result = load_source(connection, root, settings, args.manifest)
            output = project_path(root, "experiments/source-audit/helen-runs")
            output.mkdir(parents=True, exist_ok=True)
            (output / (result["run_id"] + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"Run {result['run_id']}: {result['counts']['inserted_rows']} source rows inserted; "
                  f"{result['counts']['replayed_rows']} replayed; {result['counts']['quarantined_rows']} quarantined; no analytical publication")
            return 0
        if args.command == "schedule":
            from ingestion.scheduling import run_schedule
            result = run_schedule(root, args.plan, runs=args.runs, interval_seconds=args.interval_seconds,
                                  timeout_seconds=args.timeout_seconds, max_seconds=args.max_seconds)
            print(f"Schedule {result['schedule_id']}: {result['status']}; {len(result['ticks'])} tick(s); "
                  f"{result.get('error_code', 'OK')}")
            return 0 if result["status"] == "succeeded" else 2
        if args.command == "database":
            if args.action == "check":
                from tools.database_foundation import check_foundation
                result = check_foundation()
                output = root / "experiments/source-audit/database-foundation.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print(f"Foundation checks passed: {len(result['checks'])}; isolated database removed")
            elif args.action == "model-role":
                from ingestion.permissions import provision_model_role
                with connect() as connection:
                    result = provision_model_role(connection,args.model_role)
                print(f"Provisioned {result['model_role']}; DDL limited to dbt_weather; no login credentials created")
            elif args.action == "roles":
                from ingestion.permissions import provision_roles
                with connect() as connection:
                    result = provision_roles(connection, args.loader_role, args.reporter_role)
                output = root / "experiments/source-audit/database-permissions.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print(f"Provisioned {result['loader_role']} and {result['reporter_role']}; no login credentials created")
            else:
                with connect() as connection:
                    applied = apply_migrations(connection)
                print("Applied: " + (", ".join(applied) if applied else "no new migrations"))
            return 0
        if args.command == "weather":
            settings = weather_settings(root, load_configuration(root, "FMI", args.configuration, args.raw_directory), args.weather_contract)
            if args.action == "load":
                if args.start or args.end or args.station or not (args.manifest or args.period_report):
                    raise ValueError("Load requires retained manifests or a period report, without acquisition arguments")
                paths = period_manifest_paths(root, settings, args.period_report) if args.period_report else args.manifest
                parameters = None
            else:
                if args.manifest or args.period_report or not args.start or not args.end:
                    raise ValueError("Acquire requires UTC start/end, without retained inputs")
                paths = None
                parameters = request_parameters(args.start, args.end,
                    station=args.station or settings["weather_contract"]["default_station_id"], timestep=10)
            with connect() as connection:
                result = ingest_weather(connection, root, settings, paths, parameters)
            output = project_path(root, "experiments/source-audit/weather-runs")
            output.mkdir(parents=True, exist_ok=True)
            (output / (result["run_id"] + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"Run {result['run_id']}: {result['counts']['inserted_rows']} weather rows inserted; "
                  f"{result['counts']['replayed_rows']} rows verified on replay; {result['counts']['source_nan_rows']} source NaNs")
            return 0
        if args.command == "release":
            plan, digest = read_plan(root, args.plan)
            if args.expected_plan_sha256 is not None and digest != args.expected_plan_sha256:
                raise ValueError("Release plan changed since review")
            with connect() as connection:
                if args.action == "status":
                    row = connection.execute("""SELECT r.release_id,r.content_sha256,r.counts,c.completed_end_utc
                        FROM ops.accepted_release h JOIN ops.release r USING(release_id)
                        JOIN ops.publication_checkpoint c ON c.stream_id=h.stream_id AND c.release_id=r.release_id
                        WHERE h.stream_id=%s""", (plan["stream_id"],)).fetchone()
                    print(json.dumps({"stream_id": plan["stream_id"], "accepted_release": str(row[0]) if row else None,
                        "content_sha256": row[1] if row else None, "counts": row[2] if row else {},
                        "checkpoint_end_utc": str(row[3]) if row else None}, indent=2))
                    return 0
                result = publish_weather(connection, root, plan, digest, args.expected_release, args.action == "resume")
            output = project_path(root, "experiments/source-audit/publication-runs")
            output.mkdir(parents=True, exist_ok=True)
            (output / (result["run_id"] + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            if args.json:
                print(json.dumps(result))
            else:
                print(f"Accepted weather release {result['release_id']}; {result['counts']['expected_keys']} keys; "
                      f"replayed={result['counts']['replayed_release']}; run={result['run_id']}")
            return 0
        settings = load_configuration(root, args.source, args.configuration, args.raw_directory)
        if args.action == "inspect":
            for path in args.manifest:
                inspect_manifest(root, path, settings)
            print(f"Verified {len(args.manifest)} acquisition manifest(s); no database writes")
        else:
            with connect() as connection:
                result = record_manifests(connection, root, args.manifest, settings)
            output = project_path(root, "experiments/source-audit/ledger-runs")
            output.mkdir(parents=True, exist_ok=True)
            (output / (result["run_id"] + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"Run {result['run_id']}: {result['counts']['unique_acquisitions']} acquisition(s) registered; zero analytical rows loaded")
    except (ValueError, TypeError, KeyError, AttributeError, OSError, psycopg.Error) as exc:
        # Raw exception text can contain paths, SQL parameters or connection secrets.
        print(f"Foundation command failed ({type(exc).__name__}); check input integrity, configuration and database setup.", file=sys.stderr)
        return 2
    return 0
