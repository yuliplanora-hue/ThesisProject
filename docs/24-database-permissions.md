# WP3.1 schema and database permissions

**Verified:** 16 October 2026. **Status:** accepted weather source-point schema/permission slice delivered. Helen, hourly/dimensional/combined Gold schemas and their grants extend this boundary after their prerequisites; the full integrated WP3.1 scope remains open. This work supports FR-06/11/12, NFR-02/06/09/12, SK-10/13 and E4 preparation. It retains the 18-hour task estimate; actual author hours and competency demonstration remain unrecorded. These development checks do not pass final E4 or configure Power BI authentication.

## Apply the schema and group roles

Use the existing setup account from the repository folder, with `ENERGY_DB_ROLE` unset:

```powershell
.venv\Scripts\python.exe -m ingestion database migrate
.venv\Scripts\python.exe -m ingestion database roles
.venv\Scripts\python.exe -m ingestion database check
```

[Migration 005](../sql/migrations/005_reporting_boundary.sql) adds the `reporting` schema and two views. It revokes PUBLIC database access, temporary-table permission and application-schema/table privileges, and PUBLIC creation in `public`. The database owner retains administrative access. Migrations 001–004 remain unchanged and checksum-verified; all five are applied locally.

Role creation is a separate explicit administrator action because PostgreSQL roles exist across the cluster, while the migration ledger belongs to one database. [Provisioning](../ingestion/permissions.py) creates `energy_loader` and `energy_reporter` as non-login groups, with no superuser, database/role creation, replication or RLS-bypass capability. Neither group owns schema/data objects or inherits another role. A database/purpose marker identifies managed groups; unexpected existing roles, changed flags, inherited memberships or object ownership cause rejection. Provisioning replay creates no new roles and resets application table and column grants to the allow-list.

No persistent login or password is created. The current `energy` login remains the local setup administrator. Dedicated application/BI logins need separate credentials and membership in only the relevant group when connections are configured. The isolated checks use real temporary non-superuser logins to prove enforcement; their passwords exist only in process memory and their exact UUID roles are removed afterwards.

## Permission boundary

| Capability | Setup administrator | `energy_loader` | `energy_reporter` |
| --- | --- | --- | --- |
| Migrations, role management and grants | Yes | Denied | Denied |
| Read source/operational weather tables | Yes | Explicit allow-list | Denied |
| Insert typed history, lineage and candidate weather rows | Yes | Explicit allow-list | Denied |
| Update run status/acquisition conflict marker/current pointer/checkpoint | Yes | Listed columns only | Denied |
| Change/delete historical weather values or accepted release records | Administrative capability | Denied | Denied |
| Read reporting views | Yes | Use publication/source reads | Yes |
| Create application/public tables, schemas or temporary tables | Administrative capability | Denied | Denied |
| Automatically access new future tables | Owner | No | No |

Loader SELECT/INSERT grants cover the current twelve ingestion/publication tables. UPDATE is limited to run completion/context columns, the acquisition manifest conflict marker, the current accepted release ID and checkpoint fields. No DELETE, TRUNCATE, DDL, grant option or migration-ledger access is granted. New models require an explicit grant review; there is no blanket future-table grant. Existing column grants are revoked separately because table-level revocation alone does not remove them, following [PostgreSQL GRANT semantics](https://www.postgresql.org/docs/17/sql-grant.html).

| Reporting object | Grain and use |
| --- | --- |
| `reporting.weather_release` | One accepted weather release, including station/window, plan/content hashes, counts and `is_current`; failed candidates are excluded |
| `reporting.weather_point` | Accepted release × expected ten-minute UTC key; value/quality and chosen snapshot/point lineage |

Views resolve underlying access through the migration owner and use `security_barrier`; the reporter receives SELECT only and no base-table schema access. The joins also make the views structurally read-only. Tests inspect missing table/column write privileges separately from structural DML rejection, using [PostgreSQL view behaviour](https://www.postgresql.org/docs/17/sql-createview.html). Pin one release ID across an entire analysis/refresh; historical accepted releases remain readable. Selecting every release would mix revisions.

```sql
SELECT release_id, stream_id, start_utc, end_utc_exclusive, is_current
FROM reporting.weather_release
WHERE stream_id = 'fmi-kaisaniemi-reference';

-- Use the reviewed release ID consistently across all refresh queries.
SELECT count(*) AS expected_keys, count(temperature_c) AS finite_values
FROM reporting.weather_point
WHERE release_id = 'f327b833-7b99-453f-b376-d1f82a0fe7d9';
```

## Local role switching and recovery

The Python client supports optional `ENERGY_DB_ROLE`. It performs quoted `SET ROLE` after connection and closes the connection if switching fails. This is useful for local verification with the setup account:

```powershell
$previousRole = $env:ENERGY_DB_ROLE
try {
    $env:ENERGY_DB_ROLE = 'energy_loader'
    .venv\Scripts\python.exe -m ingestion release publish --plan config/weather-release-plan.json
}
finally {
    $env:ENERGY_DB_ROLE = $previousRole
}
```

`SET ROLE` changes effective SQL permissions; it does not remove the underlying setup login's ability to reset its role. Use a dedicated restricted login for application/BI connections. PostgreSQL documents this distinction in [SET ROLE](https://www.postgresql.org/docs/17/sql-set-role.html). The reporter group is never made a member of the loader or owner role.

Restricted roles can have hidden `pg_stat_activity.backend_start` values, even for the current session after a role switch. Publication records a nullable start time and checks PID ownership conservatively: a hidden old/current start time is not evidence that the owner disconnected. Resume refuses takeover while that PID exists. This avoids granting cluster-wide monitoring privileges. Where a PID was reused and a start time is hidden, recovery can conservatively require waiting or administrator review. Existing [publication](22-weather-publication.md) and [scheduling recovery](23-scheduling-and-ci.md) conditions still apply.

## Evidence and retained failures

- **76 offline tests** pass on Windows and Linux Python 3.13.7; dependencies are compatible.
- **39 isolated PostgreSQL checks** pass on both platforms: the previous 28 controls plus 11 permission/session-visibility controls. Each run rebuilds all five migrations, verifies replay/checksums, creates restricted logins, exercises real ingestion/publication/replay, checks reporting reads and denied operations, tests privilege drift/conflicting roles/future-table exclusion, and removes only its UUID database/roles.
- Local `energy_loader` replay run **`e25ec951-d17c-4f6b-bb6e-4e0bbba043a8`** reused release **`f327b833-7b99-453f-b376-d1f82a0fe7d9`**. Its **105,264 keys**, 105,248 finite values, 16 source NaNs, zero absent keys, content hash and original checkpoint timestamp are unchanged.
- Two earlier local startup attempts exposed the hidden-session-time issue before candidate construction. Runs `dd3d2649-5e29-4e6d-b7ae-e5ba37242408` and `be819fe0-57cf-42fe-8cf9-596baf2407bf` are retained as `BACKEND_CONTEXT_INITIALIZATION_FAILED`; their exact code bytes are archived privately. They created no release/input rows. Current ledger: **13 successful runs, two failed startup runs, no running attempts and no failed working-database release candidates**. These development failures are separate from final E1–E7 results.

Private evidence: `experiments/source-audit/permissions-verification.json`, `database-permissions.json`, `database-foundation.json`, `role-switch-failures.json` and the loader replay report. The prior successful WP2.5 code and initial failing WP3.1 code are retained under private code snapshots. Temporary test roles remaining: zero. Hosted CI evidence, persistent application/BI login provisioning, independent backup and PostgreSQL restore remain separate completion conditions.

Next implementation: WP3.2's weather-first SQL/dbt slice, then UTC/hour/reporting models under WP3.3. Extend migrations, reporting/grants and source acceptance together when adding Helen and the complete Gold model. See [the development plan](07-development-plan.md) and [execution tracker](12-execution-tracker.md).

## Subsequent Helen and hosted CI delivery

[Helen source intake](25-helen-source-intake.md), delivered 16 October 2026, adds migration 006 and explicit loader-only SELECT/INSERT on two intake tables. The current suite is 83 offline tests/44 DB checks on Windows/Linux. Actual intake/replay retains 91,767 source records without changing weather publication. Hosted CI green/red/green is verified for 9fb12dd (76/39 baseline); local Helen changes await their own publication. The author confirms selected-literature review and consumption interpretation, and chooses local-only backup with shared-drive risk acceptance. Earlier counts above describe their dated delivery.
