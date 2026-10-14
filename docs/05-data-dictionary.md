# Analytical data dictionary and contracts

**Version:** 0.3, 14 October 2026. Analytical fields/models below remain proposed. The first operational `ops.source_snapshot`, `ops.pipeline_run` and `ops.run_input` tables now exist, plus `ops.schema_migration`; their current columns are defined in [migration 001](../sql/migrations/001_operational_ledger.sql). Acquisition metadata still lives in file manifests pending integration. Physical analytical precision and source mappings must be confirmed in WP1.3/WP3.1. See [source evidence](02-source-inventory.md), [architecture](08-architecture.md) and [metric definitions](09-metric-catalog.md).

## Source mappings

| Source field | Observed form | Proposed mapping | Unresolved condition |
| --- | --- | --- | --- |
| Helen `datetime_utc` | Day-first text, example `12.10.2015 06:00` | Preserve as `source_timestamp`; parse using a verified format; map to interval start/end | UTC and start/end semantics need publisher evidence |
| Helen `dh_MWh` | Decimal-comma string | Preserve as `source_value`; parse a decimal; map to `energy_mwh` or verified source quantity | Header alone does not establish interval energy or permitted MW conversion |
| FMI station identity | Samples return `100971`, Helsinki Kaisaniemi, coordinates `60.17523 24.94459` | `station_id` with station metadata | Provisional main station; validate representativeness and full-period continuity |
| FMI temperature value/time | `t2m`, explicit UTC timestamps; metadata unit `degC`, one-minute average (`PT1M`) | Original value/time plus typed observation and quality flags | Request timestep selects samples, not hourly averages; freeze aggregation/coverage after full-period audit |

Keep an explicit parser/contract version. Unknown schemas fail visibly; invalid rows retain reasons. Do not silently treat invalid text as missing or convert a local time to UTC without resolving ambiguity.

## Tables and grains

| Proposed object | Grain / key | Purpose |
| --- | --- | --- |
| `ops.source_snapshot` | One acquired content revision; `snapshot_id` | Publisher/request metadata, hash, coverage and contract version; repeated acquisitions can reference the same content |
| `ops.pipeline_run` | One execution attempt; `run_id` | Config/commit, timings, counts, status and errors; relation to all input snapshots |
| `ops.run_input` | One run × snapshot | Supports a run using both sources and several query chunks |
| `silver.heat_observation` | System × UTC interval × source revision | Typed source history; retain corrected values from older revisions |
| `silver.weather_observation` | Station × parameter × observation time × source revision | Source-resolution weather history and quality metadata |
| `ops.quarantine_record` | One rejected source record × run | Original location/value, reason and contract/rule version |
| `gold.fact_heat_hour` | System × UTC hour within a published release | One active, accepted value per business key; prior releases retain lineage |
| `gold.fact_weather_hour` | Station × UTC hour within a published release, temperature only | Selected temperature aggregation plus sample count and coverage |
| `gold.dim_date` | Helsinki reporting date | Year/month/weekday and comparison labels; UTC boundaries computed explicitly |
| `gold.dim_hour` | One UTC hour in the declared period | Unique UTC key, local date/hour, UTC offset and expected interval duration |
| `gold.dim_system` | Heating system ID | Stable system identity; no invented customer/network detail |
| `gold.dim_station` | FMI station ID | Coordinates, name and selection rationale/version |
| `gold.v_heat_weather_hour` | System × UTC hour after configured station selection | Left-aligned heat/weather view without multiplying heating rows |
| `gold.quality_hour` | Expected source/system-or-station × UTC hour | Calendar-based coverage classification independent of surviving fact rows |
| `ops.release` | One accepted publication; `release_id` | References candidate output, source/config versions and publication status |

Business-key uniqueness is enforced within each released dataset. Silver retains revisions rather than overwriting history. Physical tables or views may include `release_id`; reporting views expose one pinned accepted release. Weather aggregation needs lineage from each contributing observation, not just a single arbitrary source row.

## Canonical fields

| Field | Proposed type | Meaning and constraint |
| --- | --- | --- |
| `system_id` | text | Stable identifier, e.g. `HELSINKI_HELEN`; documented project label |
| `station_id`, `parameter_id` | text | Exact publisher identifiers; never inferred from display names alone |
| `interval_start_utc`, `interval_end_utc` | timezone-aware timestamp | Half-open interval `[start, end)`; end strictly after start |
| `observed_at_utc` | timezone-aware timestamp | Original observation instant when the source is instantaneous; do not invent interval energy |
| `interval_hours` | decimal | `(end - start)` expressed in elapsed hours, not local clock subtraction |
| `local_date`, `local_hour`, `utc_offset_minutes` | date, integer, integer | Derived Europe/Helsinki labels; local clock time alone is not a key |
| `source_timestamp`, `source_value`, `source_unit` | text | Original content retained for audit |
| `energy_mwh` | decimal, nullable | Verified interval energy only; missing stays null, not zero |
| `average_power_mw` | decimal, nullable | Verified interval-average power, or interval energy divided by confirmed duration |
| `temperature_c` | numeric, nullable | Verified observed/aggregated temperature; aggregation rule recorded |
| `observed_sample_count`, `expected_sample_count` | nonnegative integer | Weather aggregation coverage using the verified source resolution |
| `is_imputed`, `imputation_rule` | boolean, nullable text | False for observed-only baseline; any approved fill is explicit |
| `snapshot_id`, `source_hash`, `source_row_locator` | text | Snapshot plus row number or stable response locator; many-source lineage stored separately |
| `ingested_at_utc`, `run_id`, `release_id` | timestamp, text, text | Acquisition, execution and publication identities are distinct |
| `contract_version`, `configuration_hash`, `git_commit` | text | Transformation/evaluation reproducibility |
| `validation_status`, `rejection_reason` | controlled text | Accepted or quarantined; reason required for rejection |
| `revision_status` | controlled text | Current or superseded; correction is not a missingness state |

Choose decimal precision/scale after profiling magnitudes and publisher precision; retain original strings so rounding choices are auditable. Use independently checked conversion functions and exact business keys before aggregating into Power BI.

## Quality accounting

For a fixed expected hourly spine, classify each key as accepted, source-absent, rejected or unexplained processing loss. Duplicate/revision conflicts are reported separately and resolved under the contract. Every expected key has one coverage classification; rejected source rows are not counted as accepted observations.

At raw ingestion, classify every row as accepted candidate, rejected or duplicate/conflict according to the source contract. Do not require raw and hourly weather counts to match after aggregation: report input samples and resulting hours separately. Test that each join and aggregation preserves the intended grain.

## Temporal and physical rules

1. Verify timezone and interval-start/end conventions before conversion. Preserve both original and canonical representations.
2. Use UTC keys and derive Europe/Helsinki labels. Repeated autumn local hours remain distinct; spring days have fewer expected hours. Test leap days and period boundaries.
3. Align weather only after station selection and a documented hourly aggregation. Keep unmatched heat rows and quality flags; an inner join must not hide missing weather.
4. `energy_mwh = average_power_mw * interval_hours` is valid only for verified interval-average power. Instantaneous MW does not establish interval energy.
5. Current source revision selection follows a declared precedence rule; acquisition time alone is not a proven publisher version order.
6. Add slowly changing dimensions only if real changing metadata requires them. Forecast facts belong to an approved stretch extension.

Observed FMI details and the still-unresolved Helen semantics are recorded in [the source audit](11-source-audit.md). Current source helpers inspect points and file manifests; they do not populate analytical tables. The database foundation separately verifies operational tables using synthetic records in an isolated test database.

## Contract approval record

Before G2, complete source parsing/time/unit evidence and record remaining conditions. Before G3, freeze model keys and relationship tests. Before G5, freeze period, station, metric policies and the final evaluation contract versions. Record these decisions under D-006–D-010.
