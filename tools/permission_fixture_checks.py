"""Real restricted-login checks, using only UUID roles created for one isolated database."""

import hashlib
import json
import secrets
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from ingestion.database import begin_run, connection_settings, finish_run
from ingestion.permissions import provision_roles
from ingestion.publication import publish_weather
from ingestion.weather import ingest_weather


def check_permissions(admin, database, root, settings, manifest, plan):
    prefix = "energy_test_" + uuid4().hex
    loader, reporter = prefix+"_loader", prefix+"_reporter"
    created = []
    connections = []
    results = []

    def login(group, suffix):
        name, password = prefix+suffix, secrets.token_hex(24)
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}").format(sql.Identifier(name), sql.Literal(password)))
        created.append(name)
        admin.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(name)))
        admin.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(group), sql.Identifier(name)))
        options = {**connection_settings(), "dbname": database, "user": name, "password": password}
        connection = psycopg.connect(**options, autocommit=True)
        connections.append(connection)
        return name, connection

    def denied(connection, statement, readonly_view=False):
        try:
            connection.execute(statement)
        except psycopg.errors.InsufficientPrivilege:
            return
        except psycopg.errors.ObjectNotInPrerequisiteState:
            if readonly_view:
                return
            raise
        raise AssertionError("Restricted statement was not denied")

    def digest(p):
        return hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()

    try:
        provisioned = provision_roles(admin, loader, reporter)
        created.extend(provisioned["created_roles"])
        if set(created) != {loader, reporter} or provision_roles(admin, loader, reporter)["created_roles"]:
            raise AssertionError("Role provisioning/replay identity failed")
        results.append("roles_explicit_group_provisioning_and_idempotent_replay")
        reporter_login, report = login(reporter, "_report_login")
        loader_login, load = login(loader, "_loader_login")
        observed = report.execute("SELECT release_id,observed_at_utc,temperature_c,source_quality FROM reporting.weather_point ORDER BY release_id,observed_at_utc").fetchall()
        expected = admin.execute("""SELECT p.release_id,p.observed_at_utc,p.temperature_c,p.source_quality
            FROM publication.weather_point p JOIN ops.release r USING(release_id)
            WHERE r.status='accepted' ORDER BY release_id,observed_at_utc""").fetchall()
        if not observed or observed != expected:
            raise AssertionError("Reporting boundary differs from accepted weather values")
        old = report.execute("SELECT release_id FROM reporting.weather_release WHERE NOT is_current ORDER BY completed_at_utc LIMIT 1").fetchone()
        if not old or not report.execute("SELECT count(*) FROM reporting.weather_point WHERE release_id=%s", old).fetchone()[0]:
            raise AssertionError("Historical accepted release cannot be pinned")
        if report.execute("SELECT count(*) FROM reporting.weather_release").fetchone()[0] != admin.execute("SELECT count(*) FROM ops.release WHERE status='accepted'").fetchone()[0]:
            raise AssertionError("Failed candidates leaked into reporting")
        results.append("reporter_real_login_reads_only_accepted_current_and_pinned_history")
        # Joined views reject DML structurally before PostgreSQL checks their ACL.
        # Assert missing table/column privileges independently of that rejection.
        for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            if report.execute("SELECT has_table_privilege(current_user,'reporting.weather_point',%s)", (privilege,)).fetchone()[0]:
                raise AssertionError("Reporter has unexpected reporting write privilege")
        for privilege in ("INSERT", "UPDATE"):
            if report.execute("SELECT has_any_column_privilege(current_user,'reporting.weather_point',%s)", (privilege,)).fetchone()[0]:
                raise AssertionError("Reporter has unexpected reporting column write privilege")
        for statement in (
            "INSERT INTO reporting.weather_point DEFAULT VALUES",
            "UPDATE reporting.weather_point SET temperature_c=0 WHERE false",
            "DELETE FROM reporting.weather_point WHERE false",
        ):
            denied(report, statement, readonly_view=True)
        for statement in (
            "TRUNCATE publication.weather_point",
            "SELECT * FROM silver.weather_observation LIMIT 0",
            "SELECT * FROM ops.pipeline_run LIMIT 0",
            "SELECT * FROM publication.weather_point LIMIT 0",
            "CREATE TABLE public.permission_probe (id integer)",
            "CREATE TEMP TABLE permission_probe (id integer)",
            "CREATE SCHEMA permission_probe",
            "ALTER VIEW reporting.weather_point RENAME TO changed_probe",
            sql.SQL("SET ROLE {}").format(sql.Identifier(loader)),
            sql.SQL("SET ROLE {}").format(sql.Identifier(admin.info.user)),
        ):
            denied(report, statement)
        results.append("reporter_dml_ddl_raw_access_temporary_tables_and_escalation_denied")
        # Repair both table and column drift: REVOKE at table level alone is insufficient.
        admin.execute(sql.SQL("GRANT UPDATE (temperature_c) ON reporting.weather_point TO {}").format(sql.Identifier(reporter)))
        admin.execute(sql.SQL("GRANT SELECT ON ops.pipeline_run TO {}").format(sql.Identifier(reporter)))
        provision_roles(admin, loader, reporter)
        if report.execute("SELECT has_any_column_privilege(current_user,'reporting.weather_point','UPDATE')").fetchone()[0]:
            raise AssertionError("Column update privilege survived reprovisioning")
        if admin.execute("SELECT has_table_privilege(%s,'ops.pipeline_run','SELECT')", (reporter_login,)).fetchone()[0]:
            raise AssertionError("Table read privilege survived reprovisioning")
        denied(report, "UPDATE reporting.weather_point SET temperature_c=0 WHERE false", readonly_view=True)
        denied(report, "SELECT * FROM ops.pipeline_run LIMIT 0")
        results.append("role_reprovision_removes_table_and_column_privilege_drift")
        replay = ingest_weather(load, root, settings, [manifest])
        published = publish_weather(load, root, plan, digest(plan))
        if replay["counts"]["inserted_rows"] or not published["counts"]["replayed_release"]:
            raise AssertionError("Restricted loader cannot replay retained data/release")
        changed = json.loads(json.dumps(plan))
        changed["stream_id"] = "synthetic-permission-loader"
        publish_weather(load, root, changed, digest(changed))
        changed["publication_reason"] = "Restricted loader pointer/checkpoint update control"
        publish_weather(load, root, changed, digest(changed))
        results.append("loader_real_login_ingests_publishes_replays_and_updates_checkpoint")
        with psycopg.connect(**{**connection_settings(), "dbname": database}, autocommit=True) as switched:
            switched.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(loader)))
            restricted_replay = publish_weather(switched, root, plan, digest(plan))
            if not restricted_replay["counts"]["replayed_release"]:
                raise AssertionError("SET ROLE loader cannot safely publish with hidden session metadata")
        results.append("loader_set_role_handles_hidden_own_backend_timestamp")
        for statement in (
            "UPDATE silver.weather_observation SET temperature_c=0 WHERE false",
            "UPDATE publication.weather_point SET temperature_c=0 WHERE false",
            "DELETE FROM ops.release WHERE false",
            "TRUNCATE silver.weather_observation",
            "SELECT * FROM ops.schema_migration LIMIT 0",
            "CREATE TABLE ops.permission_probe (id integer)",
            "CREATE TEMP TABLE permission_probe (id integer)",
        ):
            denied(load, statement)
        results.append("loader_historical_mutation_migration_and_schema_ddl_denied")
        # A restricted user cannot see another user's backend_start. NULL means
        # unknown ownership, not proof that the old publisher has disconnected.
        owner = admin.execute("SELECT pg_backend_pid(),backend_start FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        parent = admin.execute("SELECT release_id FROM ops.accepted_release WHERE stream_id=%s", (plan["stream_id"],)).fetchone()[0]
        running = begin_run(admin, "publish_fmi_weather", digest(plan), "synthetic live-owner visibility check")
        context = {"candidate_release_id": str(uuid4()), "parent_release_id": str(parent),
                   "backend_pid": owner[0], "backend_started_at_utc": owner[1].isoformat()}
        admin.execute("UPDATE ops.pipeline_run SET stage_counts=%s WHERE run_id=%s", (Jsonb(context), running))
        try:
            try:
                publish_weather(load, root, plan, digest(plan), resume=True)
            except ValueError:
                pass
            else:
                raise AssertionError("Restricted recovery took over a live publisher")
            if admin.execute("SELECT status FROM ops.pipeline_run WHERE run_id=%s", (running,)).fetchone()[0] != "running":
                raise AssertionError("Live owner's run status was changed")
        finally:
            finish_run(admin, running, {"synthetic_control": True}, "SYNTHETIC_LIVE_OWNER_CHECK")
        results.append("restricted_recovery_does_not_treat_hidden_backend_time_as_dead")
        # Never adopt a pre-existing login, even if earlier role creation would succeed.
        other_loader = prefix+"_unused"
        try:
            provision_roles(admin, other_loader, reporter_login)
        except ValueError:
            pass
        else:
            raise AssertionError("Existing login was repurposed")
        if admin.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (other_loader,)).fetchone():
            raise AssertionError("Failed role preflight left a partial role")
        results.append("role_conflict_rejected_without_partial_cluster_changes")
        admin.execute("CREATE TABLE ops.future_permission_probe (id integer)")
        for connection in (report, load):
            denied(connection, "SELECT * FROM ops.future_permission_probe")
        results.append("future_tables_are_not_automatically_granted")
        admin.execute(sql.SQL("REVOKE {} FROM {}").format(sql.Identifier(reporter), sql.Identifier(reporter_login)))
        denied(report, "SELECT * FROM reporting.weather_point LIMIT 0")
        results.append("public_role_has_no_reporting_access_after_membership_revocation")
        return results
    finally:
        for connection in connections:
            connection.close()
        # These exact UUID roles were created successfully by this invocation.
        # DROP OWNED is limited to its disposable test database, without CASCADE.
        for name in reversed(created):
            admin.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(name)))
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(name)))
