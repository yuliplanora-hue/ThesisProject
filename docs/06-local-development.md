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
```

The first two commands work offline; FMI commands need internet access. The matrix performs nine bounded requests from `config/feasibility-samples.json`. Each query covers at most seven days, requests temperature only, uses a 20-second timeout and at most three attempts, and limits responses to 2 MB. Source responses are stored by content hash under ignored `data/raw/fmi-feasibility/`; acquisition manifests and audit reports are under ignored `experiments/source-audit/`.

Project time windows are half-open: returned FMI endpoint samples outside `[start,end)` are excluded and counted. Source tests cover schema defects, missing/duplicate keys, explicit parsing, API errors, bounded retries and preservation of failed response evidence. These checks do not certify the full analytical period or mark E1–E7 passed. See [the recorded audit](11-source-audit.md) for results and remaining conditions.

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

`energy` currently has superuser privileges. WP2/WP3 will add a loader account and a read-only reporting account; use the latter for the future Power BI connection. `psql` is available inside the container, so a host PostgreSQL installation is unnecessary.

## Implemented operational database foundation

The database client reads the local ignored `.env` password or `POSTGRES_PASSWORD` from the environment. Optional `ENERGY_DB_HOST`, `ENERGY_DB_PORT`, `ENERGY_DB_NAME` and `ENERGY_DB_USER` override the local defaults. It does not print credentials or a resolved connection string. The simple project `.env` reader supports the `POSTGRES_PASSWORD=value` assignment and matching outer quotes; it does not implement general dotenv expansion.

After PostgreSQL is healthy:

```powershell
.venv\Scripts\python.exe tools/database_foundation.py check
.venv\Scripts\python.exe tools/database_foundation.py migrate
```

`check` creates one uniquely named `energy_foundation_test_<uuid>` database, applies migrations and verifies snapshot/run/input grain, replay, failed status and rollback. It removes only that database after closing its connections. It needs the current setup account's database-creation privilege; it is separate from ordinary offline tests. Evidence is saved to ignored `experiments/source-audit/database-foundation.json`.

`migrate` applies checked-in SQL to the configured development database. Migration files are tracked by checksum in `ops.schema_migration`; a second execution skips unchanged applied files, and changing an applied file fails visibly. Add a new migration for a schema change. `001_operational_ledger.sql` was verified and applied on 14 October 2026 and creates only `ops.source_snapshot`, `ops.pipeline_run` and `ops.run_input`. These operational tables currently contain no production audit records; database integration of source manifests is the next WP2.1 task. Gold publication, application role separation, backups/restores and final E1–E7 remain future work.

Stop containers while retaining data:

```powershell
docker compose down
```

Avoid deleting the volume during normal development. Initialisation variables affect an empty database volume; editing `.env` does not change a password already stored in PostgreSQL. If port 5432 conflicts, change the host port in Compose and document the matching client setting. See the [official image documentation](https://hub.docker.com/_/postgres) for initialisation behaviour.

## Tooling to introduce during development

| Work | Planned additions | Required check before adopting |
| --- | --- | --- |
| WP2.1 | Database client/metadata migration and bounded HTTP helpers implemented; finish package/entry point and later pytest adoption | Pinned dependency checks and isolated ledger checks pass; preserve application-only pins and safe fixtures |
| WP2.5 | CI workflow and bounded local scheduler | Tests use fixtures and a temporary database; scheduled source checks are distinguished from CI |
| WP3.1–WP3.2 | Migrations, dbt Core/PostgreSQL adapter and model documentation | Compatible versions, clean database build, key/relationship checks |
| WP4 | Statistical libraries, Power BI project, DAX definitions and Excel audit | Parameterised connections and reproducible data/model versions |
| WP5 | Fabric workspace, pipeline/notebook exports and capacity evidence | Confirm actual access; keep the work within 50 hours |

No `pytest`, `dbt build` or pipeline entry-point command is a current project quick start. Add exact tested commands here as those tasks deliver working code. Preserve a small synthetic path that never requires a cloud account or live public API for routine CI.

## Git and evidence handling

This local folder is already a Git repository. For a separately downloaded starter without Git metadata, initialise it once with `git init -b main`. Review changes with:

```powershell
git status --short
```

Before a commit or GitHub publication, inspect `.gitignore` and the staged files. It currently excludes `.venv`, `.env`, raw data, top-level experiment JSON/CSV files and `experiments/source-audit/`; other nested evidence files need deliberate review. Keep secret-bearing configuration, reviewer identities and unapproved source data private. Retain publishable code, contracts, synthetic fixtures and selected result summaries.

The detailed [architecture](08-architecture.md) specifies future release, backup and recovery behaviour. A successful setup query confirms database access, not completion of E1–E7.
