# Finnish District Heating Data Platform

Build and evaluate a reliable data engineering and analytics platform using Helen district-heating data and FMI weather observations. This repository supports Li Yu’s TAMK master’s thesis and a balanced data analyst and data engineer portfolio.

**Working title:** Design and Evaluation of a Reliable Data Engineering and Analytics Platform for Finnish District Heating

**Planning baseline:** [revised research plan](docs/Li_Yu_Thesis_Research_Plan.docx), 14 October 2026; [PDF copy](docs/Li_Yu_Thesis_Research_Plan.pdf). The author confirmed supervisor approval of the revised topic/RQs; academic workload, assessment details and official dates still need confirmation.

**Delivery envelope:** November 2026–May 2027, 20 hours per week, 28 active weeks, **560 hours including 60 hours of contingency**. The author already reports strong SQL, Python and Power BI skills.

## Start here

1. Follow the [development plan](docs/07-development-plan.md) for weekly work, task estimates, dependencies and milestone gates.
2. Review the [requirements](docs/01-requirements.md) and resolve the [source audit questions](docs/02-source-inventory.md) before implementing conversions or bulk ingestion.
3. Use the [local setup guide](docs/06-local-development.md) to reproduce the current Python/PostgreSQL environment.
4. Implement and evaluate against the [architecture](docs/08-architecture.md), [data dictionary](docs/05-data-dictionary.md), [metric catalogue](docs/09-metric-catalog.md) and [evaluation protocol](docs/03-evaluation-protocol.md).

## Current implementation status

Evidence available as of 14 October 2026:

| Component | Status |
| --- | --- |
| Python, Pandas and VS Code configuration | Local virtual environment prepared; dependencies checked |
| PostgreSQL through Docker Compose | Started and verified during setup; use the setup guide to check current runtime state |
| Git | Local repository initialised; GitHub destination: [ThesisProject](https://github.com/yuliplanora-hue/ThesisProject) |
| Helen CSV | Full explicit lexical audit: 91,767 rows, no rejected rows, duplicate timestamps or gaps in the written-clock sequence |
| Source semantics | Timestamp convention, interval meaning, units and redistribution permission still require verification |
| FMI feasibility | Nine checks passed for candidate Kaisaniemi 100971; immutable responses/manifests retained; full-period contract still pending |
| Offline tests | 27 synthetic checks cover source parsing/keys, API validation/retries, snapshot preservation and database credential configuration |
| Database foundation | Psycopg client and checksum-tracked operational migration implemented; six isolated-database checks passed and migration applied locally |
| Database ingestion, SQL/dbt models, CI, Power BI and Fabric | Planned; production pipeline and research experiments are not implemented |

The available [CSV profiler](tools/profile_csv.py) is a generic inspection utility. Its report does not certify units, time semantics, expected-hour completeness or business-key uniqueness.

## Scope and technology choices

The required artefact integrates **two publishers and one heating system**, targets 24 consecutive overlapping months where feasible, and produces **five governed measures, three Power BI pages and seven evaluation experiments**. A justified 12-month fallback must still cover seasons and both DST transitions.

| Area | Development choice |
| --- | --- |
| Acquisition and validation | Python, Pandas, explicit CSV/WFS contracts |
| Local storage and modelling | PostgreSQL, SQL and dbt Core |
| Reproducibility and tests | Docker Compose, pytest and GitHub Actions |
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
| [07 Development plan](docs/07-development-plan.md) | Work packages, 28-week schedule, detailed backlog and release criteria |
| [08 Architecture](docs/08-architecture.md) | Component boundaries, revision processing, publication and operations |
| [09 Metric catalogue](docs/09-metric-catalog.md) | M1–M5 definitions, filters, edge cases and independent validation |
| [10 Competency evidence](docs/10-competency-evidence.md) | Sixteen skills linked to tasks, artefacts and review evidence |
| [11 Source audit](docs/11-source-audit.md) | Executed Helen/FMI checks, preliminary contracts and unresolved semantics |
| [12 Execution tracker](docs/12-execution-tracker.md) | Current task status, evidence, remaining prerequisites and next actions |

## First practical run

From this repository folder in PowerShell:

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tools/profile_csv.py data/raw/helen_open_dh_data_2015p01_2026p03b_v2.csv --output experiments/helen_profile.json
```

For a fresh checkout, create the environment and obtain an authorised source copy using the [setup guide](docs/06-local-development.md). Raw data, secrets and generated profiling reports are excluded from Git. Source download instructions and synthetic test fixtures will support reproduction without redistributing unapproved data.

Development has started with WP1.3 source feasibility and WP2.1 operational foundation. The setup guide includes working audit, bounded FMI and database commands; the execution tracker records progress. Historical sample access does not establish complete two-year weather coverage or acceptance of heating units.

## Documentation maintenance

The Word research plan governs academic scope. These Markdown documents implement that proposal; dates, detailed task allocations and schema choices are development decisions until confirmed at their gates. Record changes in the [decision register](docs/04-decisions-and-questions.md), then update affected requirements, contracts, metrics, tests and estimates together. Use actual experiment evidence before marking a task or competency complete.
