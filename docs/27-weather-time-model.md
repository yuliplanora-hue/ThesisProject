# WP3.3 Helsinki time model and weather reporting

**Verified:** 16 October 2026. **Status:** weather time/reporting slice delivered. The integrated heat/weather view, station/system dimensions and accepted Gold activation remain dependent on Helen analytical acceptance. WP3.3 retains its 15-hour estimate; actual author hours and competency demonstration remain to record. These are development checks, separate from final E1–E7.

## Reproduce

Run from the repository folder with the setup coordinator connection and `ENERGY_DB_ROLE` unset:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-models.txt
.venv\Scripts\python.exe -m unittest discover -s tests -q
.venv\Scripts\python.exe -m ingestion database migrate
.venv\Scripts\python.exe -m ingestion database model-role
.venv\Scripts\python.exe -m ingestion models check
.venv\Scripts\python.exe -m ingestion models build --release-id f327b833-7b99-453f-b376-d1f82a0fe7d9
```

The final command requires the existing local accepted weather release and retained inputs. A fresh checkout can run the synthetic model check without downloading Helen/FMI data. See the [dbt setup and role boundaries](26-weather-dbt-models.md). No migration was changed or added for this extension: the candidate schema remains migration 007.

## Model grains and calendar rules

The graph now has **nine models and 36 dbt data tests**, adding four views to the five-model WP3.2 baseline:

| View in `dbt_weather` | Grain | Behaviour |
| --- | --- | --- |
| `dim_hour` | Selected release × UTC hour | Independent expected-hour spine; elapsed-hour end, Helsinki civil timestamp/date/hour, UTC offset minutes and autumn fold |
| `dim_date` | Selected release × intersecting Helsinki date | Full local-midnight UTC bounds; calendar/ISO week attributes; expected 23/24/25 hours, hours inside the release and full-day flag |
| `weather_report_hour` | Selected release × station × parameter × UTC hour | Left-aligned fact/calendar joins; preserves every hourly fact, quality count and incomplete value |
| `weather_report_day` | Selected release × station × parameter × Helsinki date | Retains every intersecting date; coverage and missingness counts; temperature only for a complete, fully covered civil day |

Dimensions are scoped to the explicitly pinned source release, rather than a global calendar or a moving current pointer. UTC hour is the join key. `local_hour_start` is a timestamp without timezone used as a display label; it cannot uniquely identify the repeated autumn hour. `utc_offset_minutes` and `local_fold` distinguish the two occurrences: fold 0 is the first occurrence, fold 1 the second. Fold is determined from the actual instant, including when a partial release starts at the second occurrence.

Calendar expressions explicitly use `Europe/Helsinki` and `UTC`. Local midnight and the next local midnight are each converted to an instant before their elapsed duration is measured. The implementation uses PostgreSQL's documented [`AT TIME ZONE` semantics](https://www.postgresql.org/docs/17/functions-datetime.html#FUNCTIONS-DATETIME-ZONECONVERT); it never derives the expected day length by assuming 24 hours or using the session's implicit timezone.

A spring Helsinki day has no 03:00 hour and contains 23 elapsed hours. An autumn day has two 03:00 labels, offsets +180 and +120 minutes, and contains 25 elapsed hours. ISO week year is separate from calendar year; 30 December 2024 belongs to ISO week 1 of 2025. Leap day is retained. The manufactured graph checks compare these cases to independent Python `zoneinfo` calculations.

## Daily eligibility and gaps

Each complete hour still requires six finite, published ten-minute samples. A daily temperature requires a full Helsinki day inside the declared release window, all its expected elapsed hours present and every hour complete. The daily mean averages those equally long UTC hours; on DST days its denominator is 23 or 25. It is a mean of sampled hourly estimates, not a new continuous measurement.

An incomplete or partial day retains its counts and has NULL temperature. Even a partial release containing only finite hours cannot become a complete day. Counts distinguish incomplete observed hours, hours outside the release, missing model hours, source NaNs, source absence and missing published slots. Processing loss fails tests. No interpolation, zero substitution or omission of ineligible dates occurs. This prepares the weather-day eligibility needed for M5; HDD, paired heating measures, DAX and final E5 are not delivered by this task.

## Executed verification

**Windows and fresh Linux Python 3.13.7 / PostgreSQL 17.11:** 92 offline tests pass; all 44 database foundation controls pass in fresh Linux (prior Windows result retained); 15 isolated model-control scenarios pass on both platforms. Every valid synthetic build passes nine models/36 data tests. Duplicate keys and a removed published sample intentionally fail the expected SQL tests, then repaired data builds green. The eight synthetic builds cover spring missingness, fall, two deliberate failures, recovery, leap day, ISO year boundary and a partial repeated-hour day. Generated documentation/catalog and restricted-login boundaries also pass; disposable databases and roles are removed.

The independent [Python calendar/report oracle](../tools/time_model_checks.py) checks all SQL dimension labels, date boundaries, day lengths, calendar fields, daily counts and mean eligibility, plus one-to-one fact/report accounting. Session timezone checks use UTC, America/New_York and Asia/Kathmandu. Five [offline reference checks](../tests/test_time_model_checks.py) separately cover DST folds/gaps, partial-day semantics, leap/ISO boundaries and invalid windows.

Actual candidate build **`32a516b0-3eab-4a0d-9008-4ea2775aea9d`** pins accepted weather release **`f327b833-7b99-453f-b376-d1f82a0fe7d9`**, source content SHA-256 `ca80125fb35a1c2a288041523326469c6c7c87808279110936bfad0447093008`, and links all 105 input snapshots. Verification of the full 2024–2025 Helsinki window found:

| Control | Verified result |
| --- | ---: |
| UTC hours / independent hourly arithmetic and calendar comparisons | 17,544 |
| Complete / incomplete hours | 17,539 / 5 |
| Source NaN samples / lineage slots | 16 / 105,264 |
| Helsinki dates / complete weather days | 731 / 728 |
| 23-hour / 24-hour / 25-hour dates | 2 / 727 / 2 |
| Partial dates in this actual release | 0 |
| Autumn second occurrences retained | 2 |
| Hourly/daily numeric comparison tolerance | 1e-12 |

The three ineligible dates are **11 September 2024, 18 November 2024 and 5 December 2025**. Their five incomplete hours remain in the hourly view; all three daily temperatures are NULL. Every reporting-hour label/calendar field was independently compared too. A six-slot trace from the first hour resolves back to source snapshot and point indices through `weather_hour_lineage`.

Private evidence is under ignored `experiments/source-audit/`:

- `model-runs/32a516b0-3eab-4a0d-9008-4ea2775aea9d/`: summary, source/model/dependency identities, dbt invocation/results, compiled SQL and documentation/catalog.
- `weather-time-verification.json`: full-window calendar/arithmetic/count/lineage verification and unchanged publication/permission checks.
- `model-checks/` and `linux-model-checks/`: synthetic build/failure/recovery results.
- `code-snapshots/wp3.2-verified/` and `code-snapshots/wp3.3-verified/`: checksum-verified prior/current source and model versions; the latter also preserves the verification helpers and CI definition.

The operational ledger now has 18 successful runs and the two previously retained startup failures, with no running attempt. Accepted source publication/checkpoint is unchanged. The existing CI model-check command exercises the extended graph locally in fresh Linux; these changes are now published and [hosted CI passes on c25c87f](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38896004389) with 95 offline tests, 44 foundation controls and the 15 dbt/calendar scenarios.

## Query and lineage example

These candidate queries require the setup account or a connection allowed to assume `energy_transformer`; `energy_reporter` is deliberately denied access:

```sql
SELECT local_date, expected_day_hour_count, complete_hour_count,
       is_complete_weather_day, temperature_c
FROM dbt_weather.weather_report_day
WHERE NOT is_complete_weather_day
ORDER BY local_date;

SELECT h.hour_start_utc, h.local_hour_start, h.utc_offset_minutes, h.local_fold,
       p.observed_at_utc, p.source_quality, p.snapshot_id, p.source_point_index
FROM dbt_weather.weather_report_hour h
JOIN dbt_weather.weather_hour_lineage p
  USING (release_id, station_id, parameter_id, hour_start_utc)
WHERE h.hour_start_utc = timestamptz '2023-12-31 22:00:00+00'
ORDER BY p.observed_at_utc;
```

The trace intentionally expands one hour to its six slots; aggregate weather values from the hourly view, not this expanded lineage result. Candidate objects can be replaced individually by dbt and are not an atomic accepted release. Do not connect BI/reporters to these candidates as if they were accepted Gold. [WP3.4 database backup/restore and measured query optimisation](28-database-operations.md) are now verified for the current local prototype. Next is WP4.1 synthetic metric reference SQL; integrated Helen/Gold acceptance continues under its existing source conditions.
