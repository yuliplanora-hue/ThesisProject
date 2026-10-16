# Finnish District Heating Data Platform

Build and evaluate a reliable data engineering and analytics platform using Helen district-heating data and FMI weather observations. This repository supports Li Yu’s TAMK master’s thesis and a balanced data analyst and data engineer portfolio.

**Working title:** Design and Evaluation of a Reliable Data Engineering and Analytics Platform for Finnish District Heating

**Planning baseline:** [revised research plan](docs/Li_Yu_Thesis_Research_Plan.docx), 14 October 2026; [PDF copy](docs/Li_Yu_Thesis_Research_Plan.pdf). The author confirmed supervisor approval of the revised topic/RQs; academic workload, assessment details and exact programme review/submission dates still need confirmation. The author now confirms an end-of-2026 deadline; the proposal's May 2027 finish is superseded by the development plan.

**Current delivery envelope:** end of December 2026, **50–55 hours/week** (author-confirmed), with an **11-week plan at approximately 51 hours/week**. Preserve the full analyst/engineer/Fabric scope and the **560-hour estimate including 60 contingency hours**; exact programme dates/workload and actual author hours remain to record. The author already reports strong SQL, Python and Power BI skills.

## Start here

1. Follow the [development plan](docs/07-development-plan.md) for weekly work, task estimates, dependencies and milestone gates.
2. Review the [requirements](docs/01-requirements.md) and resolve the [source audit questions](docs/02-source-inventory.md) before implementing conversions or bulk ingestion.
3. Use the [local setup guide](docs/06-local-development.md) to reproduce the current Python/PostgreSQL environment.
4. Implement and evaluate against the [architecture](docs/08-architecture.md), [data dictionary](docs/05-data-dictionary.md), [metric catalogue](docs/09-metric-catalog.md) and [evaluation protocol](docs/03-evaluation-protocol.md).

## Current implementation status

Evidence available as of 16 October 2026:

| Component | Status |
| --- | --- |
| Python, Pandas and VS Code configuration | Local virtual environment prepared; dependencies checked |
| PostgreSQL through Docker Compose | Started and verified during setup; use the setup guide to check current runtime state |
| Git | Local repository initialised; GitHub destination: [ThesisProject](https://github.com/yuliplanora-hue/ThesisProject) |
| Helen CSV | Full explicit lexical audit: 91,767 rows, no rejected rows, duplicate timestamps or gaps in the written-clock sequence |
| Source semantics | Publisher-linked current CSV hash and declared UTC labels verified; author-provided MWh/DH recorded; author-confirmed interval-end labels recorded; physical quantity/boundary, current-edition licence and paired acceptance remain open |
| FMI feasibility | Full 2024–2025 weather window audited: 105,264 returned timestamps, 16 NaNs, 17,539/17,544 complete hours; source responses/manifests retained |
| Offline tests | 76 pass on Windows/Linux; includes role-name/connection controls, scheduling, publication/recovery and 55 metric controls |
| Database foundation | Five migrations and explicit group-role CLI; 39 isolated database checks pass on Windows/Linux, including real restricted-logins and publication/recovery |
| WP1 research preparation | Initial local package delivered: 15 selected references from 20 candidates, nine critical notes, contracts, 55 controls, statistical split and author-selected walkthrough fallback; closure conditions remain pending |
| Station sensitivity | Airport 100968 preselected; four seasonal samples return 576/576 finite readings; full-period analytical comparison remains planned |
| Source evidence backup | Latest local `backup/`: 415 file copies and three sample restores verified; earlier snapshot preserved; independent storage remains pending |
| CI | Windows/Linux and PostgreSQL workflow linted; opt-in visible failure probe added and verified locally; hosted execution pending publication |
| Fabric access | Available per author confirmation; workspace/capacity/permissions and deployment still to verify |
| FMI typed ingestion | 105,264 selected baseline rows loaded with 16 explicit NaNs; full replay inserts zero. Separate live query adds six retained revision rows |
| Weather publication | Explicit 105-snapshot source-point release accepted; replay reuses its ID/checkpoint; correction/backfill/failure recovery verified in isolated fixtures |
| Database permissions | Non-login loader/reporter groups provisioned; reporting views expose accepted weather revisions; writes/raw access denied. Dedicated application/BI logins remain to configure |
| Local scheduling | Two bounded CLI ticks reuse the accepted weather release/checkpoint; overlap and failure-stop controls verified; no persistent OS task registered |
| Helen ingestion, SQL/dbt/hourly/combined Gold models, Power BI, Fabric and CD | Planned; integrated publication, permissions, deployment and final experiments remain to implement |

The available [CSV profiler](tools/profile_csv.py) is a generic inspection utility. Its report does not certify units, time semantics, expected-hour completeness or business-key uniqueness.

## Scope and technology choices

The required artefact integrates **two publishers and one heating system**, targets 24 consecutive overlapping months where feasible, and produces **five governed measures, three Power BI pages and seven evaluation experiments**. A justified 12-month fallback must still cover seasons and both DST transitions.

| Area | Development choice |
| --- | --- |
| Acquisition and validation | Python, Pandas, explicit CSV/WFS contracts |
| Local storage and modelling | PostgreSQL, SQL and dbt Core |
| Reproducibility and tests | Docker Compose, current stdlib unittest suite and GitHub Actions; pytest adoption later |
| Analysis and communication | Python statistics, Power BI/DAX/Power Query, a small Excel audit and a decision memo |
| Conditional cloud demonstration | Microsoft Fabric, one Data Factory pipeline and Lakehouse, focused Delta/PySpark work; maximum 50 hours |

Core research remains executable locally. Forecasting, another source such as Fingrid, or an additional orchestration example is stretch work: choose at most one after the core BI milestone and only within remaining capacity. Streaming, multi-cloud, hydraulic simulation and production utility control are outside scope.

## Documentation map

| Document | Use |
| --- | --- |
| [01 Requirements](docs/01-requirements.md) | Research questions, priorities and acceptance traceability |
| [02 Source inventory](docs/02-source-inventory.md) | Observed file evidence, unresolved semantics and source feasibility gates |
| [03 Evaluation protocol](docs/03-evaluation-protocol.md) | E1–E7 procedures, thresholds and result records |
| [04 Decisions and questions](docs/04-decisions-and-questions.md) | Design choices, pending decisions and supervisor questions |
| [05 Data dictionary](docs/05-data-dictionary.md) | Proposed grains, fields, keys, timestamps and provenance |
| [06 Local development](docs/06-local-development.md) | Commands that work with the current starter and planned tooling additions |
| [07 Development plan](docs/07-development-plan.md) | Work packages, revised 11-week year-end schedule, detailed backlog and release criteria |
| [08 Architecture](docs/08-architecture.md) | Component boundaries, revision processing, publication and operations |
| [09 Metric catalogue](docs/09-metric-catalog.md) | M1–M5 definitions, filters, edge cases and independent validation |
| [10 Competency evidence](docs/10-competency-evidence.md) | Sixteen skills linked to tasks, artefacts and review evidence |
| [11 Source audit](docs/11-source-audit.md) | Executed Helen/FMI checks, preliminary contracts and unresolved semantics |
| [12 Execution tracker](docs/12-execution-tracker.md) | Current task status, evidence, remaining prerequisites and next actions |
| [13 Scope and method](docs/13-scope-and-method.md) | Personas, analytical tasks/rubrics, DSR stages and academic completion record |
| [14 Literature review](docs/14-literature-review.md) | Executed search log, 20-candidate matrix, 45-hit screening and design rationale |
| [15 Data-management plan](docs/15-data-management-plan.md) | Storage, attribution, publication, backup, reviewer handling and retention decisions |
| [16 Source contracts](docs/16-source-contracts.md) | Weather baseline/full-window evidence and Helen clarification/acceptance conditions |
| [17 Critical literature notes](docs/17-critical-literature-notes.md) | Nine targeted readings, method/limit comparisons and bounded contribution statement |
| [18 WP1 readiness](docs/18-wp1-readiness.md) | Verified preparation, outstanding academic/source/storage decisions and completion sequence |
| [19 Reference fixtures](docs/19-reference-fixtures.md) | 55 manual metric answers, verification commands, predeclared split and author-walkthrough template |
| [20 Operational provenance](docs/20-operational-provenance.md) | WP2.1 module CLI, acquisition/run identities, atomic metadata registration and verified replay |
| [21 Weather ingestion](docs/21-weather-ingestion.md) | WP2.3 accepted point contract, typed Silver history, working commands, replay/failure checks and real evidence |
| [22 Weather publication](docs/22-weather-publication.md) | WP2.4 frozen source layers, accepted release/checkpoint, reader pinning and interruption recovery |
| [23 Scheduling and CI](docs/23-scheduling-and-ci.md) | WP2.5 bounded replay, failure diagnosis, real execution IDs and hosted CI completion procedure |
| [24 Database permissions](docs/24-database-permissions.md) | WP3.1 reporting views, group roles, real restricted-login checks and retained failure evidence |

## First practical run

From this repository folder in PowerShell:

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tools/check_wp1_fixtures.py
.venv\Scripts\python.exe tools/profile_csv.py data/raw/helen_open_dh_data_2015p01_2026p03b_v2.csv --output experiments/helen_profile.json
```

For a fresh checkout, create the environment and obtain an authorised source copy using the [setup guide](docs/06-local-development.md). Raw data, secrets and generated profiling reports are excluded from Git. Source download instructions and synthetic test fixtures will support reproduction without redistributing unapproved data.

Development has started with WP1 research/source preparation and WP2.1 operational foundation. The setup guide includes working audit, bounded FMI and database commands; the execution tracker records progress. The full weather audit establishes available timestamps and explicit missing-value accounting, while Helen interpretation and paired source acceptance remain pending.

## Documentation maintenance

The Word research plan governs academic scope. These Markdown documents implement that proposal; dates, detailed task allocations and schema choices are development decisions until confirmed at their gates. Record changes in the [decision register](docs/04-decisions-and-questions.md), then update affected requirements, contracts, metrics, tests and estimates together. Use actual experiment evidence before marking a task or competency complete.
