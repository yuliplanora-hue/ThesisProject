"""Explicit administrator provisioning of application group roles in one database."""

import re

from psycopg import sql


INSERT_TABLES = (
    "ops.source_snapshot", "ops.pipeline_run", "ops.run_input", "ops.source_acquisition",
    "ops.run_acquisition", "ops.weather_snapshot_load", "silver.weather_observation",
    "ops.release", "ops.release_source", "publication.weather_point",
    "ops.accepted_release", "ops.publication_checkpoint",
)
UPDATES = {
    "ops.pipeline_run": ("status", "completed_at_utc", "stage_counts", "error_code"),
    "ops.source_acquisition": ("manifest_sha256",),
    "ops.accepted_release": ("release_id",),
    "ops.publication_checkpoint": ("release_id", "completed_end_utc", "plan_sha256", "updated_at_utc"),
}
REPORT_VIEWS = ("reporting.weather_release", "reporting.weather_point")


def role_name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value) or value.startswith("pg_") or value == "public":
        raise ValueError("Role name must be an ordinary lowercase identifier, maximum 63 characters")
    return value


def table_name(value):
    return sql.Identifier(*value.split("."))


def provision_roles(connection, loader="energy_loader", reporter="energy_reporter"):
    """Never repurpose existing users/roles or create login credentials implicitly."""
    loader, reporter = role_name(loader), role_name(reporter)
    if loader == reporter:
        raise ValueError("Loader and reporter must be separate roles")
    database = connection.info.dbname
    created = []
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(hashtext('energy_role_provisioning'))")
        if connection.execute("SELECT to_regclass('reporting.weather_point')").fetchone()[0] is None:
            raise ValueError("Apply reporting migration before provisioning roles")
        for name, purpose in ((loader, "loader"), (reporter, "reporter")):
            marker = f"finnish-energy:{database}:{purpose}:v1"
            existing = connection.execute("""SELECT r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolinherit,
                r.rolcanlogin,r.rolreplication,r.rolbypassrls,shobj_description(r.oid,'pg_authid'),
                EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid),
                EXISTS(SELECT 1 FROM pg_shdepend d WHERE d.refclassid='pg_authid'::regclass
                    AND d.refobjid=r.oid AND d.deptype='o')
                FROM pg_roles r WHERE r.rolname=%s""", (name,)).fetchone()
            if existing is not None:
                if existing != (False, False, False, False, False, False, False, marker, False, False):
                    raise ValueError("Existing role is not an unchanged group managed for this database")
            else:
                connection.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(sql.Identifier(name)))
                connection.execute(sql.SQL("COMMENT ON ROLE {} IS {}").format(sql.Identifier(name), sql.Literal(marker)))
                created.append(name)
        for name in (loader, reporter):
            # Reset this project's database/schema/table ACLs before explicit allow-list grants.
            connection.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM {}").format(sql.Identifier(database), sql.Identifier(name)))
            connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(name)))
            connection.execute(sql.SQL("REVOKE ALL ON SCHEMA public,ops,silver,publication,reporting FROM {}").format(sql.Identifier(name)))
            connection.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA ops,silver,publication,reporting FROM {}").format(sql.Identifier(name)))
            # Table-level revocation does not remove existing column-level grants.
            relations = connection.execute("""SELECT n.nspname,c.relname,array_agg(a.attname ORDER BY a.attnum)
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
                WHERE n.nspname IN ('ops','silver','publication','reporting') AND c.relkind IN ('r','v','m','p')
                GROUP BY n.nspname,c.relname""").fetchall()
            for schema, table, columns in relations:
                fields = sql.SQL(",").join(map(sql.Identifier, columns))
                connection.execute(sql.SQL("REVOKE SELECT ({}),INSERT ({}),UPDATE ({}),REFERENCES ({}) ON {} FROM {}").format(
                    fields, fields, fields, fields, sql.Identifier(schema, table), sql.Identifier(name)))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA ops,silver,publication TO {}").format(sql.Identifier(loader)))
        for table in INSERT_TABLES:
            connection.execute(sql.SQL("GRANT SELECT,INSERT ON {} TO {}").format(table_name(table), sql.Identifier(loader)))
        for table, columns in UPDATES.items():
            connection.execute(sql.SQL("GRANT UPDATE ({}) ON {} TO {}").format(
                sql.SQL(",").join(map(sql.Identifier, columns)), table_name(table), sql.Identifier(loader)))
        connection.execute(sql.SQL("GRANT SELECT ON publication.current_weather_point TO {}").format(sql.Identifier(loader)))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA reporting TO {}").format(sql.Identifier(reporter)))
        for view in REPORT_VIEWS:
            connection.execute(sql.SQL("GRANT SELECT ON {} TO {}").format(table_name(view), sql.Identifier(reporter)))
    return {"database": database, "loader_role": loader, "reporter_role": reporter,
            "created_roles": created, "login_credentials_created": False,
            "scope": "Weather source-point loading and accepted reporting views only"}
