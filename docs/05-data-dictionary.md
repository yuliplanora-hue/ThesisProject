# Analytical data dictionary and contracts

**Version:** 0.8, 16 October 2026. Operational provenance and FMI source-resolution Silver tables are implemented; Helen source intake, private weather-hour/calendar candidates and hourly/daily reporting are implemented; interpreted Helen, integrated station/system dimensions and accepted Gold remain proposed. Migrations 001–007 define current objects, including accepted-weather reporting views and PUBLIC access hardening; [typed weather ingestion](21-weather-ingestion.md) preserves Decimal values, NULL/source_nan states, original source text/index and run/snapshot lineage. Acquisition manifests are linked to PostgreSQL, with raw XML retained. Physical analytical precision and source mappings must be confirmed in WP1.3/WP3.1. See [source evidence](02-source-inventory.md), [architecture](08-architecture.md) and [metric definitions](09-metric-catalog.md).

## Source mappings

| Source field | Observed form | Proposed mapping | Unresolved condition |
| --- | --- | --- | --- |
| Helen `datetime_utc` | Day-first text, example `12.10.2015 06:00` | Preserve as `source_timestamp`; parse as UTC interval end, derive start by subtracting one elapsed hour | Publisher-declared UTC; author-confirmed end labels (`10:00` covers `[09:00,10:00)`); quantity/boundary still pending |
| Helen `dh_MWh` | Decimal-comma string | Preserve as `source_value`; parse a decimal; map to `energy_mwh` or verified source quantity | Header alone does not establish interval energy or permitted MW conversion |
| FMI station identity | Full weather audit uses `100971`, Helsinki Kaisaniemi, returned coordinates `60.17523 24.94459` | `station_id` with station metadata | Project baseline is a single central urban proxy; station sensitivity and paired alignment remain to validate |
| FMI temperature value/time | `t2m`, explicit UTC, `degC`, one-minute source average (`PT1M`), sampled every ten minutes | Original value/time plus typed observation and quality flags | Baseline mean needs six finite samples/hour; 16 NaNs/five incomplete hours retained. Six-sample hourly candidate aggregation is implemented/tested in dbt; final analytical acceptance remains separate |

Keep an explicit parser/contract version. Unknown schemas fail visibly; invalid rows retain reasons. Do not silently treat invalid text as missing or convert a local time to UTC without resolving ambiguity.

## Tables and grains

| Proposed object | Grain / key | Purpose |
| --- | --- | --- |
| `ops.source_snapshot` | Source ID × content hash; `snapshot_id` | Implemented raw-content identity and first locator; repeated acquisitions can reference the same content |
| `ops.source_acquisition` | Snapshot × manifest-byte hash; `acquisition_id` | Implemented retrieval time, request URL/parameters, byte count, status and manifest locator; distinct retrieval evidence retained |
| `ops.pipeline_run` | One execution attempt; `run_id` | Config/commit, timings, counts, status and errors; relation to all input snapshots |
| `ops.run_input` | One run × snapshot | Supports a run using both sources and several query chunks |
| `ops.run_acquisition` | One run × acquisition | Implemented link to retained acquisition evidence; composite foreign keys enforce agreement with the run's snapshot |
| `silver.heat_observation` | System × UTC interval × source revision | Typed source history; retain corrected values from older revisions |
| `silver.weather_observation` | Snapshot × station × parameter × UTC observation time | Implemented source-resolution history; numeric value, original text/point index, quality and first-loaded run |
| `ops.weather_snapshot_load` | One loaded content snapshot | Implemented first-run/contract/parser identity, station/query bounds and expected/returned/NaN/absent/endpoint counts |
| `ops.quarantine_record` | One rejected source record × run | Original location/value, reason and contract/rule version |
| `gold.fact_heat_hour` | System × UTC hour within a published release | One active, accepted value per business key; prior releases retain lineage |
| `gold.fact_weather_hour` | Station × UTC hour within a published release, temperature only | Selected temperature aggregation plus sample count and coverage |
| `gold.dim_date` | Helsinki reporting date | Year/month/weekday and comparison labels; UTC boundaries computed explicitly |
| `gold.dim_hour` | One UTC hour in the declared period | Unique UTC key, local date/hour, UTC offset and expected interval duration |
| `gold.dim_system` | Heating system ID | Stable system identity; no invented customer/network detail |
| `gold.dim_station` | FMI station ID | Coordinates, name and selection rationale/version |
| `gold.v_heat_weather_hour` | System × UTC hour after configured station selection | Left-aligned heat/weather view without multiplying heating rows |
| `gold.quality_hour` | Expected source/system-or-station × UTC hour | Calendar-based coverage classification independent of surviving fact rows |
| `ops.release` | One accepted/failed weather candidate; `release_id` | Implemented plan/parent/build-run/content identity; combined Gold integration remains planned |
| `ops.release_source` | Release × snapshot × layer | Implemented frozen source selection/precedence metadata |
| `publication.weather_point` | Release × expected ten-minute key | Implemented weather value/quality and chosen raw-point lineage, including source-absent grid slots |
| `ops.accepted_release`, `ops.publication_checkpoint` | One current pointer/checkpoint per weather stream | Implemented atomic acceptance and completed-window marker |
| `reporting.weather_release` | One accepted weather release | Implemented current/historical accepted metadata; failed candidates excluded |
| `reporting.weather_point` | Accepted release × expected ten-minute key | Implemented SELECT-only reporter boundary with chosen lineage; queries must pin one release |
| `ops.helen_snapshot_load` | One source-content snapshot | Implemented parser/intake-contract/first-run identity and exhaustive source/valid/quarantine counts |
| `silver.helen_source_record` | Snapshot × source-record index | Implemented original fields, unconverted numeric value, interval lineage and quarantine/warnings; no analytical heat approval |
| `dbt_weather.stg_weather_release`, `stg_weather_point` | Explicit selected UUID / release × ten-minute slot | Implemented private staging views from accepted reporting sources |
| `dbt_weather.int_weather_hour`, `fct_weather_hour` | Selected release × station × parameter × UTC hour | Implemented candidate counts and six-finite-sample mean; incomplete hours remain NULL, no fill |
| `dbt_weather.weather_hour_lineage` | Selected slot × its UTC hour | Implemented complete chosen snapshot/index/quality lineage; not a published Gold object |
| `dbt_weather.dim_hour` | Selected release × UTC hour | Implemented expected-hour spine, Helsinki timestamp/date/hour, offset minutes and fold; civil labels are not keys |
| `dbt_weather.dim_date` | Selected release × intersecting Helsinki date | Implemented calendar/ISO attributes, full local-day UTC bounds, expected 23/24/25 hours and release coverage |
| `dbt_weather.weather_report_hour` | Selected release × station × parameter × UTC hour | Implemented one-to-one left-aligned fact/calendar candidate; every incomplete hour retained |
| `dbt_weather.weather_report_day` | Selected release × station × parameter × Helsinki date | Implemented coverage/missingness candidate; temperature only for a fully covered day with all expected hours complete |

Business-key uniqueness is enforced within each released dataset. Silver retains revisions rather than overwriting history. Physical tables or views may include `release_id`; reporting views expose accepted current/historical revisions; each analysis must filter one pinned accepted release. [Role and view permissions](24-database-permissions.md) deny reporter writes and direct source/operational access. Weather aggregation needs lineage from each contributing observation, not just a single arbitrary source row.

## Canonical fields

| Field | Proposed type | Meaning and constraint |
| --- | --- | --- |
| `system_id` | text | Stable identifier, e.g. `HELSINKI_HELEN`; documented project label |
| `station_id`, `parameter_id` | text | Exact publisher identifiers; never inferred from display names alone |
| `interval_start_utc`, `interval_end_utc` | timezone-aware timestamp | Half-open interval `[start, end)`; end strictly after start |
| `observed_at_utc` | timezone-aware timestamp | Original observation instant when the source is instantaneous; do not invent interval energy |
| `interval_hours` | decimal | `(end - start)` expressed in elapsed hours, not local clock subtraction |
| `local_date`, `local_hour`, `utc_offset_minutes` | date, integer, integer | Derived Europe/Helsinki labels; local clock time alone is not a key |
| `local_fold` | integer, 0 or 1 | Helsinki first occurrence / repeated autumn occurrence, derived from the instant even at a partial-window boundary |
| `expected_day_hour_count`, `release_hour_count`, `is_full_day_in_release` | integer, integer, boolean | Full civil-day elapsed hours, hours within the pinned release, and full-window coverage |
| `is_complete_weather_day` | boolean | Full local day covered and every expected elapsed hour complete; otherwise daily temperature is NULL |
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

Observed FMI details and the still-unresolved Helen semantics are recorded in [the source audit](11-source-audit.md). Standalone audit helpers inspect points/manifests; [the weather loader](21-weather-ingestion.md) now populates typed Silver observations with lineage and replay checks. Operational provenance, weather-load metadata, accepted weather source-point publication and Helen source-value Silver intake are implemented. Private hourly/calendar/daily candidates are verified in [WP3.3](27-weather-time-model.md); interpreted Helen and accepted combined Gold remain proposed. See the current weather runbook for input-set and database counts; the earlier operational runbook preserves the WP2.1 delivery baseline.

## Contract approval record

Before G2, complete source parsing/time/unit evidence and record remaining conditions. Before G3, freeze model keys and relationship tests. Before G5, freeze period, station, metric policies and the final evaluation contract versions. Record these decisions under D-006–D-010.
