# Executed source audit and preliminary contracts

**Audit date:** 14 October 2026. **Task:** WP1.3. **Requirements:** FR-01–FR-03, NFR-02–NFR-04. **Status:** lexical parsing and representative FMI access verified; source contracts are not yet accepted for analytical loading. The checks prepare E1/E2; they are not final E1–E7 experiments.

## Helen full-file evidence

The unchanged local file is `data/raw/helen_open_dh_data_2015p01_2026p03b_v2.csv`; SHA-256 `f8363dbbfa09c8a00048de4836c4029a6f4d3482ee5e4b2f99da2b1e938cfee1`.

| Check | Observed result |
| --- | --- |
| File size / rows | 3,244,432 bytes / 91,767 |
| Exact schema | `datetime_utc;dh_MWh` |
| Explicit timestamp format | `%d.%m.%Y %H:%M`; all rows parse |
| Measurement parser | Decimal comma and arbitrary-precision Decimal; all rows parse |
| Rejected rows | 0 |
| Duplicate / conflicting timestamp keys | 0 / 0 |
| Off-hour / descending timestamp records | 0 / 0 |
| Written-clock range | `2015-10-12T06:00:00` through `2026-03-31T20:00:00` |
| Expected / observed written-clock hourly keys | 91,767 / 91,767; zero gaps |
| Negative measurements | 0; source-domain validity still needs a contract |
| Minimum / maximum values as written | `30.1108349609375` / `2603.0272657568366`; no physical unit asserted |

`tools/audit_helen.py` and `ingestion/audit.py` implement this inspection. Full report: ignored `experiments/source-audit/helen-explicit-audit.json`. The source strings remain unchanged in the original file. Coverage is the naive written-clock sequence between first and last recorded timestamps; it does not establish UTC interpretation, coverage outside those bounds or complete Helsinki calendar periods.

The [Helen publisher page](https://www.helen.fi/en/about-us/helen/open-data) describes hourly district-heating power. The [official data catalogue](https://www.opendata.fi/data/fi/dataset/helsingin-kaukolammon-tuotantotarve) describes Helsinki production need in MW and lists CC BY 4.0. Its API metadata was saved locally and identifies Helen Oy as maintainer, but the resource URL names an older CSV. This corroborates power terminology without proving the local column is interval-average power, instantaneous power or hourly energy. The public publisher page was readable through web browsing; a direct Python page fetch returned HTTP 403 and was not treated as source evidence.

Pending contract fields: timestamp timezone; interval start/end convention; quantity and physical representation; applicable current-snapshot licence/attribution; revision precedence and deletion/overlap rules. Original retrieval timestamp/URL remain unknown for the existing local file. Do not invent them from filesystem dates. No M1/M2 conversion or canonical Gold loading is approved.

## FMI executed sample matrix

The first `place=helsinki` discovery response identified **Helsinki Kaisaniemi**, FMI station **100971**, coordinates **60.17523 24.94459** in the returned EPSG:4258 point. The saved matrix selects `fmisid=100971` explicitly and requests only `t2m` through `fmi::observations::weather::timevaluepair`.

| Sample | Exclusive project interval in UTC | Timestep | Expected / valid samples |
| --- | --- | --- | --- |
| Winter 2024 | 2024-01-01 00:00 to 2024-01-02 00:00 | 60 minutes | 24 / 24 |
| Winter 2024 repeat | Same interval, separate acquisition | 60 minutes | 24 / 24; keyed content equal |
| Summer 2024 | 2024-07-01 00:00 to 2024-07-02 00:00 | 60 minutes | 24 / 24 |
| Spring Helsinki day | 2024-03-30 22:00 to 2024-03-31 21:00 | 60 minutes | 23 / 23 |
| Autumn Helsinki day | 2024-10-26 21:00 to 2024-10-27 22:00 | 60 minutes | 25 / 25 |
| Winter 2025 | 2025-01-01 00:00 to 2025-01-02 00:00 | 60 minutes | 24 / 24 |
| Summer 2025 | 2025-07-01 00:00 to 2025-07-02 00:00 | 60 minutes | 24 / 24 |
| End of 2025 | 2025-12-31 00:00 to 2026-01-01 00:00 | 60 minutes | 24 / 24 |
| Finer sample | 2025-01-01 00:00 to 2025-01-01 01:00 | 10 minutes | 6 / 6 |

All nine checks passed with zero duplicate in-scope keys, absent samples or NaN values in these samples. The API also returned an inclusive endpoint; inspection excludes that point under `[start,end)` and records the exclusion. The repeated request has identical keyed station/time/raw-value content; this tests source extraction repeatability, not database-pipeline idempotency.

Configuration: [feasibility-samples.json](../config/feasibility-samples.json). Saved run: `experiments/source-audit/fmi-matrix-9ff3227db8d04b30b5530ff073a2e1e6.json`, executed 11:29:56–11:29:57 UTC. Each entry links an acquisition manifest containing exact parameters, retrieval time, HTTP status, response size/hash and inspection results. Raw XML is content-addressed under `data/raw/fmi-feasibility/`. These outputs are locally retained and ignored by Git; the selected summary above is the publishable record.

## Verified weather semantics and licence

The [parameter metadata](https://opendata.fmi.fi/meta?observableProperty=observation&param=t2m&language=eng) identifies air temperature, unit `degC`, statistical function `avg` and aggregation period `PT1M`. The [stored-query description](https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=DescribeStoredQueries&storedquery_id=fmi::observations::weather::timevaluepair) specifies point observations and a default UTC timezone. The inspected points explicitly end in `Z`.

An hourly request returns a one-minute temperature average sampled once per hour. A ten-minute request returns six such samples per complete project hour. Neither request automatically creates an hourly average. Proposed modelling choice to assess: retrieve ten-minute samples, compute a clearly labelled mean of sampled one-minute temperatures per UTC hour, record observed/expected sample counts and retain the original observation times. This is not a proven continuous time-weighted temperature mean. Freeze the aggregation and minimum sample coverage before analytical use; compare an hourly sampling alternative as a sensitivity check if justified.

The [FMI licence page](https://en.ilmatieteenlaitos.fi/open-data-licence) states CC BY 4.0. Attribute Finnish Meteorological Institute, retain the licence link and access date, and identify derived transformations. Do not imply endorsement. Metadata/query/catalogue responses and their hash/retrieval manifests are retained under `data/raw/source-documents/` and `experiments/source-audit/`.

## Proposed common period and next acceptance checks

Propose **1 January 2024–1 January 2026 in Helsinki reporting time**, subject to resolving Helen timezone and interval convention. If Helen timestamps are UTC, those local boundaries correspond to `2023-12-31T22:00:00Z` and `2025-12-31T22:00:00Z`. The written Helen sequence spans both candidate boundaries, and representative FMI samples succeed. Full weather coverage across this interval has not been acquired or certified, and this is not yet a frozen period decision.

1. Resolve Helen unit/representation/time convention using publisher evidence; prepare a question for the author if public documentation remains insufficient. No external message has been sent.
2. Confirm applicability of the catalogue licence to the existing snapshot and recover a reproducible download route.
3. Justify the main station for aggregated Helsinki heating demand; check continuous station history and declare a backup/sensitivity station before final analysis.
4. Freeze hourly aggregation and weather coverage rules, then acquire/audit the full candidate period in bounded chunks.
5. Accept contracts and record decisions D-006/D-007 before source-dependent database loading or energy metrics.

See [working commands](06-local-development.md), [the decision register](04-decisions-and-questions.md) and [task status](12-execution-tracker.md).
