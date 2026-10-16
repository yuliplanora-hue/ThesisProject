# WP2.3 FMI source-resolution ingestion

**Delivered:** 14 October 2026. **Status:** implemented and locally verified. The accepted [weather ingestion contract](../config/weather-ingestion.json) covers FMI `t2m` observations in Celsius and UTC, sampled every ten minutes. It does not accept Helen physical semantics, publish hourly aggregates or pass final E1–E7 experiments. Source evidence remains in [the source contracts](16-source-contracts.md); [FMI's licence](https://en.ilmatieteenlaitos.fi/open-data-licence) requires attribution under CC BY 4.0.

This records the WP2.3 delivery baseline (52 tests, 16 database checks and seven runs). Subsequent [WP2.4 weather publication](22-weather-publication.md) now provides explicit active source selection, accepted source-point releases and checkpoint recovery; current totals/checks are recorded there. Hourly/heating Gold remains future work.

## Working commands

Run from the repository root after starting PostgreSQL and installing the pinned requirements:

```powershell
.venv\Scripts\python.exe -m ingestion database migrate
.venv\Scripts\python.exe -m ingestion weather --help
.venv\Scripts\python.exe -m ingestion weather load --period-report experiments/source-audit/fmi-full-period.json
```

The retained-period command makes no new source requests. It verifies the completed report against its baseline contract hash, station, dates and complete chunk grid, then checks each request/manifest/raw hash and re-inspects the XML. A repeat inserts zero rows and verifies the existing values, source text, point indexes and quality flags against the raw snapshots.

For a bounded live extraction, followed by typed loading in the same run:

```powershell
.venv\Scripts\python.exe -m ingestion weather acquire --station 100971 --start 2025-01-01T00:00:00Z --end 2025-01-01T01:00:00Z
```

`acquire` requests at most seven days of one station/temperature parameter, using the existing 20-second timeout, at most three attempts and a 2 MB response bound. Explicit default station is Kaisaniemi 100971; preselected alternative 100968 is also permitted for source-level ingestion. No place-name discovery is performed by this command. Raw XML and attempt manifests remain immutable and ignored; failed inspection preserves the acquired raw/manifest evidence, while a transport failure retains a failed database run.

To load individually selected manifests, repeat `--manifest` instead of `--period-report`:

```powershell
.venv\Scripts\python.exe -m ingestion weather load --manifest experiments/source-audit/fmi-period-manifests/<manifest-id>.json
```

Replace the placeholder with an actual retained manifest. `--raw-directory` selects another project-local raw directory, including `data/raw/fmi-station-sensitivity`; `--weather-contract` selects a compatible versioned point-ingestion contract. Batch size is capped at 110 manifests. Do not combine retained inputs with acquisition arguments.

## Stored data and lineage

[Migration 003](../sql/migrations/003_weather_observations.sql) adds two objects:

| Object | Grain and behaviour |
| --- | --- |
| `ops.weather_snapshot_load` | One loaded raw-content snapshot; first-loaded run, station/query bounds, parser/contract identity, station metadata and expected/returned/NaN/absent/endpoint counts |
| `silver.weather_observation` | Snapshot × station × parameter × UTC observation time; exact Decimal value, original source text, one-based point index within the raw XML, quality flag and first-loaded run |

Finite source values use PostgreSQL `numeric`; parsing retains their decimal text precision. A source `NaN` becomes a NULL value with `source_nan` quality and original `NaN` text. An absent timestamp has no fabricated observation row and is counted separately in the load metadata. Observations at the FMI inclusive end are retained in raw XML but excluded from the project `[start,end)` load. No interpolation, zero substitution or hourly averaging occurs.

Weather timestamps remain observation instants. Helen's author-confirmed interval-end-to-start adjustment is not applied to weather. The baseline hourly calculation from six finite samples remains future SQL/dbt work.

Every row links to a content snapshot and its first-loaded run. That run links to retained acquisition evidence through the operational ledger. Foreign keys enforce the snapshot/station/parameter relationship; checks reject nonfinite numeric values and off-grid times. The ledger code/configuration identity captures the new loader and migration. WP2.1's earlier source bytes are preserved under ignored `experiments/source-audit/code-snapshots/wp2.1/`, with prior contracts/audits retained separately.

## Replay, revisions and failure

A replay reuses snapshot/acquisition identities and preserves first-loaded row lineage, while creating a distinct run. It compares existing snapshot metadata and every stored row to the verified source; detected corruption fails visibly. Different source content creates another retained revision rather than overwriting earlier observations. Repeated or overlapping query snapshots may legitimately contain the same station/time keys in separate revisions.

**Do not sum or average the entire Silver history.** WP2.4 will define a frozen snapshot set, conflict handling and active-revision selection before reporting. A later download alone does not establish publisher precedence. The period baseline and the small live sample below are distinct input sets.

Snapshot/load/observation writes, acquisition links and successful completion share one transaction. An invalid later input rolls back the whole batch and retains a separate `FMI_INGESTION_FAILED` run. Local weather-load transactions are serialized with an advisory lock; HTTP acquisition occurs before taking that lock. No checkpoint or Gold release is published. Initial configuration/connection errors occur before run creation.

PostgreSQL is authoritative. Successful-run summaries are written after commit to ignored `experiments/source-audit/weather-runs/<run_id>.json`; a subsequent summary-file write failure does not undo committed rows and should be checked in the ledger before retrying.

## Verification and actual evidence

- **52 offline tests** pass on Windows and disposable Linux Python 3.13.7. New controls cover exact decimals, UTC instants, original point locators, NaN/absent accounting, endpoint exclusion, station/grid/type defects and three-attempt timeout exhaustion. Pinned dependencies pass compatibility checks.
- **16 isolated PostgreSQL checks** pass: nine foundation checks plus seven weather checks for typed values/lineage, replay, retained corrected revisions, batch rollback, failed acquisition status, stored corruption detection and the finite-value constraint. The exact invocation-created database is removed afterwards. These development checks are not final experiments.
- The selected **105-chunk baseline** contains **105,264 distinct UTC times/rows**, **105,248 finite values**, **16 source NaNs**, **zero absent samples**, and **105 excluded endpoint samples**. Bounds are `2023-12-31T22:00:00Z` to exclusive `2025-12-31T22:00:00Z`; last included sample is `2025-12-31T21:50:00Z`. The first load inserts 105,264 rows; replay inserts zero and verifies all 105,264.
- Two live one-hour requests for station 100971 return identical raw/keyed content. First load inserts six finite rows; second inserts zero and verifies those six. Two acquisition manifests and distinct runs remain retained.
- Current database totals are **107 content snapshots, 108 acquisitions, seven successful runs, 423 run/acquisition links, 106 loaded weather snapshots and 105,270 weather revision rows**. The extra six rows are the separate one-hour snapshot, not six new baseline observation times or a second selected reporting dataset.

Actual runs: full load `b4ac0c53-7c01-4f63-a3bd-ffc688a9b2a5`; full replay `ee1c55e8-026a-41b9-89ec-8f30f7ea185a`; live attempts `83f20507-b248-4586-8d8d-b794eccddf26` and `4041bed3-511c-4d5d-a03d-f73bd8e0d02a`. Detailed verification is retained in ignored `experiments/source-audit/weather-ingestion-verification.json`. The source-audit backup was refreshed to 330 files with three verified sample restores; it remains on C:, not an independent database backup.

The existing [CI workflow](../.github/workflows/ci.yml) automatically includes the 52 tests and expanded 16-check database command; hosted execution remains pending. WP2.3 is technically complete. Next weather-only reliability work is WP2.4: revision/conflict policies, backfills, checkpoints and accepted-release publication. SQL/dbt hourly models, least-privilege application roles, database restore, BI/cloud work and final evaluation retain their own completion criteria. See [the tracker](12-execution-tracker.md).
