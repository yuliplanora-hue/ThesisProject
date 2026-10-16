# Local development environment

Open `finnish-energy-phase1` as the VS Code workspace folder. All commands below run from that folder in PowerShell. The current executable starter includes the Pandas profiler, PostgreSQL Compose service, tested Helen/FMI source-feasibility tools and operational database foundation. Analytical ingestion, dbt models and final research experiments are planned in [the development roadmap](07-development-plan.md).

## Existing setup and prerequisites

The earlier setup verified Python 3.13.7, Pandas, Git, VS Code and PostgreSQL through Docker. Docker Desktop is installed per user on this machine. These are recorded setup results, not a live uptime check. Use the commands below to verify the environment when resuming work.

The working dependency declaration is [requirements-dev.txt](../requirements-dev.txt), with application-only version constraints in [requirements-lock.txt](../requirements-lock.txt). It pins Pandas 2.3.3 and Psycopg/binary 3.3.6 plus their tested dependency versions for this Python 3.13 environment. The documentation-generation libraries installed during plan editing are not application dependencies and are excluded.

## Python and Pandas

Create the environment only when it does not already exist:

```powershell
if (-not (Test-Path .venv)) { python -m venv .venv }
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pip check
```

Use `python` on this machine; the `py` launcher did not locate an installation during initial setup. Calling the environment executable directly avoids changing PowerShell’s execution policy. In VS Code, use **Python: Select Interpreter** and choose `.venv\Scripts\python.exe`.

The local CSV is already present. In a fresh checkout, obtain an authorised copy using [the source inventory](02-source-inventory.md), save it under `data/raw/` and record its checksum before profiling:

```powershell
.venv\Scripts\python.exe tools/profile_csv.py data/raw/helen_open_dh_data_2015p01_2026p03b_v2.csv --output experiments/helen_profile.json
```

Inspect imported types, missing fields and duplicate rows. This utility does not validate units, expected-hour completeness or business keys. Its optional timestamp mode uses automatic parsing; use the explicit audit command below for lexical checks. Neither mode settles UTC or physical semantics by itself.

## Implemented source-feasibility commands

The source helpers use the Python standard library; the offline suite also checks Psycopg database configuration. Install the declared development requirements above first. From the repository folder:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tools/audit_helen.py data/raw/helen_open_dh_data_2015p01_2026p03b_v2.csv --output experiments/source-audit/helen-explicit-audit.json
.venv\Scripts\python.exe tools/fmi_feasibility.py --station 100971 --start 2025-01-01T00:00:00Z --end 2025-01-02T00:00:00Z
.venv\Scripts\python.exe tools/run_feasibility_checks.py
.venv\Scripts\python.exe tools/audit_fmi_period.py
.venv\Scripts\python.exe tools/audit_paired_labels.py
```

The first two commands work offline; FMI commands need internet access. The final paired-label command runs offline after the contracted Helen CSV and completed full-weather report are present. It verifies the heat-file hash/schema and matching weather boundaries, then audits both possible interval-start/end label ranges without aggregating heating values. Contract v0.3 now selects interval-end labels from the author clarification; physical quantity/boundary/licence acceptance remains separate. The current result is 17,544/17,544 labels under either hypothesis, with no missing/duplicate labels; source-declared UTC evidence and author-confirmed interval-end mapping are recorded in contract v0.3. It stops if the UTC mapping is not accepted or the inputs differ from their contracts. See [the source evidence](11-source-audit.md).

The matrix performs nine bounded requests from `config/feasibility-samples.json`. Each query covers at most seven days, requests temperature only, uses a 20-second timeout and at most three attempts, and limits responses to 2 MB. Source responses are stored by content hash under ignored `data/raw/fmi-feasibility/`; acquisition manifests and audit reports are under ignored `experiments/source-audit/`.

`audit_fmi_period.py` uses [the weather baseline contract](../config/fmi-source-contract.json) to audit 2024–2025 Helsinki calendar years in 105 seven-day-or-shorter chunks with ten-minute temperature samples. The first run needs internet and saved approximately 34.8 MB of XML. Rerunning the same output revalidates all cached request/content hashes and recalculates coverage without source requests for completed chunks; a failed acquisition stops with preserved progress for a later resume. Use a different `--output` path for a separate fresh acquisition or changed contract; do not overwrite the declared source evidence silently. Partial local days cannot be counted as complete calendar days.

Project time windows are half-open: returned FMI endpoint samples outside `[start,end)` are excluded and counted. Source tests cover schema defects, missing/duplicate keys, explicit parsing, API errors, bounded retries, cached snapshot integrity and full/partial local-day accounting. The full weather-window inspection accounts for 16 NaNs affecting five hours; it does not establish sensor accuracy, Helen alignment or completed E1–E7. See [the recorded audit](11-source-audit.md) and [source contracts](16-source-contracts.md) for results and remaining conditions.

## PostgreSQL through Docker

Start Docker Desktop. If an existing VS Code terminal cannot find `docker`, restart VS Code or add the installed CLI directory for the current session; this also makes its credential helper available:

```powershell
$env:PATH = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;" + $env:PATH
docker version
docker compose version
```

For another machine, follow the [Docker Desktop Windows installation instructions](https://docs.docker.com/desktop/setup/install/windows-install/) and verify the chosen installation path. The project’s [compose.yaml](../compose.yaml) specifies PostgreSQL `17.11-bookworm` with a named data volume and a loopback-only port.

Create `.env` only if missing:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Replace a copied placeholder with a local password. If the existing `.env` contains the generated setup password, retain it. Validate and start the service without printing the resolved secret-bearing configuration:

```powershell
docker compose config --quiet
docker compose up -d --wait
docker compose ps
docker compose exec postgres psql -U energy -d finnish_energy -v ON_ERROR_STOP=1 -c "SELECT version(), current_database(), current_user;"
```

| Setting | Value |
| --- | --- |
| Host / port | `127.0.0.1:5432` |
| Database | `finnish_energy` |
| Current setup user | `energy` |
| Password | Local ignored `.env` |
| Data persistence | Named Docker volume from `compose.yaml` |

`energy` remains the setup superuser. WP3.1 now provisions non-login `energy_loader` and `energy_reporter` groups and accepted-weather reporting views. Real restricted logins are verified in disposable tests; dedicated persistent application/Power BI logins remain to configure. See [the permission runbook](24-database-permissions.md). `psql` is available inside the container, so a host PostgreSQL installation is unnecessary.

## Implemented operational database foundation

The database client reads the local ignored `.env` password or `POSTGRES_PASSWORD` from the environment. Optional `ENERGY_DB_HOST`, `ENERGY_DB_PORT`, `ENERGY_DB_NAME` and `ENERGY_DB_USER` override the local defaults. Optional `ENERGY_DB_ROLE` switches effective SQL role after connection; clear it for administrative migrate/roles/check commands. It does not print credentials or a resolved connection string. The simple project `.env` reader supports the `POSTGRES_PASSWORD=value` assignment and matching outer quotes; it does not implement general dotenv expansion.

After PostgreSQL is healthy:

```powershell
.venv\Scripts\python.exe -m ingestion database check
.venv\Scripts\python.exe -m ingestion database migrate
.venv\Scripts\python.exe -m ingestion database roles
```

`check` creates one uniquely named `energy_foundation_test_<uuid>` database, applies migrations and runs 44 checks of migrations, provenance, typed ingestion and revision/publication/checkpoint/recovery integrity, including a separate reader and interrupted test process. It creates real restricted test logins and verifies read/write/DDL boundaries, then removes only its exact UUID roles and database after closing their connections. It needs the setup account's database- and role-creation privileges; it is separate from ordinary offline tests. Evidence is saved to ignored `experiments/source-audit/database-foundation.json`.

`migrate` applies checked-in SQL to the configured development database. Migration files are tracked by checksum in `ops.schema_migration`; a second execution skips unchanged applied files, and changing an applied file fails visibly. Add a new migration for a schema change. `001_operational_ledger.sql` creates `ops.source_snapshot`, `ops.pipeline_run` and `ops.run_input`; additive `002_acquisition_provenance.sql` creates `ops.source_acquisition` and `ops.run_acquisition`. Migration `003_weather_observations.sql` adds `ops.weather_snapshot_load` and `silver.weather_observation`; migration `004_weather_publication.sql` adds the weather release/pointer/checkpoint and publication view; migration `005_reporting_boundary.sql` adds accepted-weather reporting views and PUBLIC access hardening; migration `006_helen_source_intake.sql` adds source-record/quarantine storage; migration `007_weather_model_build.sql` adds the private dbt candidate schema; all seven migrations are locally applied. The ledger now holds 107 snapshots, 108 acquisitions, 18 successful runs, two retained failed role-switch startup attempts and 425 run/acquisition links after Helen intake/replay and three successful model builds. The corrected loader replay preserves the accepted release and original checkpoint; [permission evidence](24-database-permissions.md) records the failures and fix. Weather publication adds 105 release/source links and one accepted 105,264-key dataset; [the publication runbook](22-weather-publication.md) records its frozen source set, checkpoint and publish/resume/status commands. Weather history contains 105,264 selected baseline rows plus six separate live-query revision rows. See [the typed weather runbook](21-weather-ingestion.md) for load/acquire commands and source-set boundaries. [The provenance runbook](20-operational-provenance.md) explains `python -m ingestion manifests inspect/record`, verification, configuration and exact evidence. The weather group-role/reporting boundary is implemented. The loader now has explicit source-only Helen grants; [Helen intake](25-helen-source-intake.md) stores/replays 91,767 unconverted records. Integrated Gold/reporting grants, persistent logins and final E1–E7 remain future work. [WP3.4](28-database-operations.md) now verifies separate-database restore for the current prototype.

Stop containers while retaining data:

```powershell
docker compose down
```

Avoid deleting the volume during normal development. Initialisation variables affect an empty database volume; editing `.env` does not change a password already stored in PostgreSQL. If port 5432 conflicts, change the host port in Compose and document the matching client setting. See the [official image documentation](https://hub.docker.com/_/postgres) for initialisation behaviour.

## Optional dbt weather models

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-models.txt
.venv\Scripts\python.exe -m ingestion database model-role
.venv\Scripts\python.exe -m ingestion models check
.venv\Scripts\python.exe -m ingestion models build --release-id f327b833-7b99-453f-b376-d1f82a0fe7d9
```

Run administrative/ledger commands with `ENERGY_DB_ROLE` unset. The optional stack pins dbt Core 1.12.6/adapter 1.11.0 and leaves the base application pins unchanged. Child dbt connections use non-login `energy_transformer`, with DDL only in `dbt_weather` and accepted-weather source reads. Nine models/36 dbt tests and 15 separate synthetic graph controls pass on Windows/Linux. The actual candidate graph retains 17,544 hours (five incomplete) and 731 Helsinki dates (728 complete weather days); reporter access and accepted publication remain unchanged. [Time/reporting rules and evidence](27-weather-time-model.md) cover DST, ISO/leap boundaries, partial days and session timezone independence. See [the model runbook](26-weather-dbt-models.md) for role/authentication limits, artifact locations and CI scope.


Hosted CI now passes on [commit c25c87f](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38896004389): Windows/Linux offline tests, PostgreSQL foundation and the weather dbt/Helsinki calendar job. Offline checks include model/operations CLI help; only the model job installs optional dbt dependencies. It uses synthetic inputs and does not read the local raw data or database archives. [CI publication and Windows regression evidence](23-scheduling-and-ci.md) records the initial failure and fix.

## Database backup/restore and query measurement

```powershell
.venv\Scripts\python.exe tools/database_operations.py --release-id f327b833-7b99-453f-b376-d1f82a0fe7d9
```

Run with the setup connection and `ENERGY_DB_ROLE` unset, after building the candidate graph for that accepted release. The helper uses PostgreSQL clients inside Compose, exports a consistent snapshot, retains a new ignored binary archive and restores into its own new UUID database. All 27 project tables/views, audit records, schema definitions and pointer/checkpoint data match; destination-only groups and transformer ownership are verified. Five warm-cache repetitions compare a lookup before/after a trial index in the copy, with identical rows and raw plans retained. Windows/fresh Linux pass; temporary resources are removed and the working database is unchanged. See [the operations runbook](28-database-operations.md) for archive paths, hashes, measurements, native-client mode and final-E4 limits.

## Source-evidence backup

The author-selected project `backup/` folder is ignored by Git. Create a new checksum-verified evidence snapshot with:

```powershell
.venv\Scripts\python.exe tools/backup_evidence.py --destination backup
```

This copies raw inputs, source-audit evidence, nonsecret contracts and `tests/fixtures/wp1/` into a fresh snapshot, preserving previous backups. The manifest lists per-file SHA-256 checksums and three representative CSV/XML/JSON restore checks. It rejects a destination inside the source directories and does not copy `.env` or a database volume. The latest 16 October snapshot verified 3,146 files and three sample restores, including new weather evidence/configuration and archived prior code/contracts; earlier 282/294/304/330/361/379/415/438/1,316-file snapshots remain intact. Because this local folder is on the same C: drive as the inputs, the author explicitly chose local-only backup on 16 October and accepted the shared-drive failure risk. External storage is not a pending user decision; this file-copy helper claims no independence or database restore. See [the DMP](15-data-management-plan.md) for scope and evidence. The separate [database rehearsal](28-database-operations.md) now passes on the current prototype; final E4 remains future work.

## Synthetic metric reference controls

```powershell
.venv\Scripts\python.exe tools/check_wp1_fixtures.py
```

This offline command verifies 55 hand-entered M1–M5 answers from 240 manufactured heat rows and 240 weather-hour rows. Cases cover the required six filters plus DST, missingness, zero and unequal-exposure controls. The 95-test suite includes fixture verification and corruption/wrong-answer rejection. These are reference controls for later SQL/DAX, not production models or passed E5. See [fixture definitions and the author-walkthrough template](19-reference-fixtures.md). Byte hashes remain stable across checkout through the scoped `.gitattributes` rule.

## Continuous integration and later deployment

The [GitHub Actions workflow](../.github/workflows/ci.yml) runs on pushes, pull requests and manual dispatch. It uses Python 3.13.7, matching the local baseline, with `requirements-dev.txt` and `requirements-lock.txt`. Offline synthetic tests run separately on Ubuntu 24.04 and Windows Server 2025; a separate Ubuntu job starts PostgreSQL `17.11-bookworm` and runs the 44 isolated-database foundation/weather/publication/scheduler/permission/Helen checks through the module CLI. These normal jobs check dependency compatibility and have 15-minute timeouts; the optional failure-probe job has a five-minute timeout. A newer run cancels an older run for the same Git ref. Actions are pinned to verified release commit hashes; review these pins and the Python/dependency baseline deliberately when upgrading.

The workflow uses a disposable test database and a public fixture password, never the local `.env` or application credentials. Test execution requires no Helen download, live FMI access or cloud account; runner provisioning and dependency installation still require network access. The repository token has read-only contents permission and checkout does not retain Git credentials. There is no live-source schedule or deployment step. An opt-in `failure_probe` dispatch input deliberately fails a separate job using a corrupted temporary fixture; it defaults to false. Hosted green, deliberate red and green recovery are now verified for commit `9fb12dd`; [run links and scope](25-helen-source-intake.md) distinguish the hosted 76/39 baseline from local Helen 83/44 verification.

To reproduce the relevant checks locally:

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
# Start the local PostgreSQL service first; this check creates/removes only its UUID test database.
.venv\Scripts\python.exe tools/database_foundation.py check
```

The committed workflow is now published on GitHub. Review results under the repository's **Actions** tab and the pull request's **Checks** tab. The initial hosted success/failure/recovery URLs and commit are recorded in [the Helen/CI evidence](25-helen-source-intake.md); expanded Helen/dbt/calendar code now passes hosted CI on [c25c87f](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38896004389). A separate weather job installs `requirements-models.txt` and runs 15 model/calendar scenarios, including nine models/36 SQL tests. Merge enforcement additionally requires a branch rule making the checks required; this workflow alone does not configure that rule.

Continuous deployment is deferred until there is an executable application and an agreed deployment target. Before introducing CD, define environment-specific configuration, migration/release ordering, health checks and rollback; for the conditional Fabric slice, confirm workspace/capacity and an approved authentication route. Successful CI must precede deployment. Extend the current dbt/calendar checks with integrated release checks when those artefacts exist, while keeping live-source acquisition separate from routine fixture checks.

## Tooling to introduce during development

| Work | Planned additions | Required check before adopting |
| --- | --- | --- |
| WP2.1 | Complete: module CLI, versioned configuration, client, two migrations and acquisition-to-run ledger | 44 offline tests and nine isolated checks pass; 106 retained acquisitions and full FMI replay verified; author competency remains unassessed |
| WP2.5 | Executable-slice scheduling/recovery and hosted green/red/green criterion complete for 9fb12dd | [Hosted evidence](25-helen-source-intake.md); local suite now 83/44. Future models add checks; no persistent OS task or CD deployment registered |
| WP3.1 | Accepted-weather migration/role/view boundary delivered; full integrated schema and dedicated logins remain | [39 database controls and actual restricted replay](24-database-permissions.md); five migrations rebuild cleanly |
| WP3.2 | Weather-first dbt graph delivered; full integrated model scope remains | Five models/22 dbt tests, nine synthetic model controls and 17,544 real hourly comparisons; [commands/evidence](26-weather-dbt-models.md). The [WP3.3 weather time/reporting extension](27-weather-time-model.md) now passes nine models/36 tests and 15 controls; [WP3.4 backup/restore and measured optimisation](28-database-operations.md) are also delivered for the current database; next is WP4.1 synthetic metric reference SQL |
| WP4 | Statistical libraries, Power BI project, DAX definitions and Excel audit | Parameterised connections and reproducible data/model versions |
| WP5 | Fabric workspace, pipeline/notebook exports and capacity evidence | Access is author-confirmed; verify workspace/capacity/permissions and expiry, and keep the work within 50 hours |

The module CLI now supports bounded scheduling; use [the exact scheduling commands](23-scheduling-and-ci.md). `pytest` remains future tooling. Optional pinned dbt modelling now runs through `python -m ingestion models build/check`; see [the dbt runbook](26-weather-dbt-models.md). Add exact tested commands here as those tasks deliver working code. Preserve a small synthetic path that never requires a cloud account or live public API for routine CI.

## Git and evidence handling

This local folder is already a Git repository. For a separately downloaded starter without Git metadata, initialise it once with `git init -b main`. Review changes with:

```powershell
git status --short
```

Before a commit or GitHub publication, inspect `.gitignore` and the staged files. It currently excludes `.venv`, `.env`, raw data, `backup/`, top-level experiment JSON/CSV files and `experiments/source-audit/`; other nested evidence files need deliberate review. Keep secret-bearing configuration, reviewer identities and unapproved source data private. Retain publishable code, contracts, synthetic fixtures and selected result summaries.

The detailed [architecture](08-architecture.md) specifies future release, backup and recovery behaviour. A successful setup query confirms database access, not completion of E1–E7.
