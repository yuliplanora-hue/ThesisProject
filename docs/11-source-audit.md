# Executed source audit and preliminary contracts

**Audit date:** 14 October 2026. **Task:** WP1.3. **Requirements:** FR-01–FR-03, NFR-02–NFR-04. **Status:** Helen lexical audit and full FMI weather-window feasibility verified; paired source acceptance still needs Helen semantics. The checks prepare E1/E2; they are not final E1–E7 experiments. The executed baseline is defined in [the source contracts](16-source-contracts.md).

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

The [Helen publisher page](https://www.helen.fi/en/about-us/helen/open-data) describes hourly district-heating power. The [official data catalogue](https://www.opendata.fi/data/fi/dataset/helsingin-kaukolammon-tuotantotarve) describes Helsinki production need in MW and lists CC BY 4.0. Its resource URL names an older CSV. The author provided MWh (`mhw` spelling normalised to match `dh_MWh`) and `dh` = district heating; this is an author statement in [the Helen contract](../config/helen-source-contract.json). Interval/system-boundary and publisher-wording reconciliation remain open. An earlier direct fetch returned HTTP 403; subsequent successful acquisitions below provide new evidence without changing that historical failure record.

Interval-end mapping is now author-confirmed. Pending contract fields: quantity and physical representation; applicable current-edition licence/attribution; system boundary, final revision precedence and deletion/overlap rules. Original retrieval timestamp/URL remain unknown for the existing local file. The verified reacquisition below does not reconstruct them. No M1/M2 conversion or canonical Gold loading is approved.

### Verified publisher reacquisition and UTC label evidence

On 14 October 2026 both the Finnish and English Helen publisher pages were acquired successfully and retained with checksums. Both link the [current CSV](https://www.helen.fi/contentassets/7a09af6d184447d6982a6f80e3bd3e29/helen_open_dh_data_2015p01_2026p03b_v2.csv). A fresh download at **14:21:23 UTC**, HTTP 200, returned **3,244,432 bytes** and SHA-256 **`f8363dbbfa09c8a00048de4836c4029a6f4d3482ee5e4b2f99da2b1e938cfee1`**, exactly matching the existing local file. This verifies current publisher provenance for those bytes, while leaving the original local retrieval details unknown.

The page's chart `parseDate` matches day/month/year/hour/minute strings and constructs `Date.UTC(...)`. Together with the linked CSV's `datetime_utc` header, this supports accepting **publisher-declared UTC observation labels**, recorded in contract v0.2 as `accepted_utc_mapping: true`. This is not an independent sensor-clock accuracy test and does not identify interval start/end or establish physical energy representation. A commented chart unit suffix is not treated as unit evidence.

The author subsequently clarified that **UTC+3 refers to the website/computer display**, not the timestamps written in the CSV. Raw UTC interpretation therefore remains unchanged. Helsinki local time uses UTC+3 in summer and UTC+2 in winter, as [FMI's open-data FAQ](https://en.ilmatieteenlaitos.fi/open-data-questions) explains. Derive display labels using `Europe/Helsinki`, rather than adding three hours throughout the year.

The author subsequently specifies that `10:00` covers `09:00–10:00`. Despite calling it “interval start”, its explicit coverage defines an **interval-end label**. Contract v0.3 preserves this author statement; no publisher reply is inferred. Subtract one elapsed UTC hour to obtain canonical start, then derive local labels. A raw `10:00Z` end label pairs with weather samples at `09:00Z` through `09:50Z`, the six-sample hour beginning `09:00Z`. Physical quantity/boundary and licence acceptance remain separate.

The [live HRI catalogue](https://hri.fi/data/dataset/helsingin-kaukolammon-tuotantotarve) API and its [linked older CSV](https://www.helen.fi/contentassets/7a09af6d184447d6982a6f80e3bd3e29/helen_2015_2024_v2.csv) were also acquired. That CSV is **2,224,466 bytes**, SHA-256 `c98df0c7fe3ad7e6d24a269bdce85442b11cbf76461f859b20f074f266314851`, and differs from the current edition. CC BY 4.0 is explicit in the catalogue, but its resource points to this older edition; applicability to the newer current edition remains unconfirmed. Neither raw CSV is added to Git, and the older edition does not replace the working snapshot or change the predeclared split.

Retained ignored manifests: `experiments/source-audit/helen-publisher-page-lookup.json`, `helen-current-resource-acquisition.json`, `helen-hri-catalogue.json` and `helen-hri-resource-acquisition.json`. Content-addressed publisher HTML, catalogue JSON and CSV copies are under `data/raw/source-documents/`. The English publisher page hash is `1054dbe8d4e9e21b12d9d605b9998d820ae0ee1ef0898a56ab30d0808fd1c213`.

### Proposed paired-window label audit

[audit_paired_labels.py](../tools/audit_paired_labels.py) verifies the contracted heat-file hash/schema and completed weather-report boundaries, then counts heat labels without reading measurement values into an analysis. For the Helsinki 2024–2025 window (`2023-12-31T22:00:00Z` to exclusive `2025-12-31T22:00:00Z`), both hypotheses have **17,544/17,544 distinct labels, zero absent labels and zero duplicate rows**:

| Hypothesis | Required heat-label range, half-open UTC |
| --- | --- |
| Labels mark interval start | `2023-12-31T22:00:00Z` to `2025-12-31T22:00:00Z` |
| Labels mark interval end | `2023-12-31T23:00:00Z` to `2025-12-31T23:00:00Z` |

Coverage therefore cannot determine the correct interval convention. The original v0.2 audit selected neither hypothesis and is preserved under `experiments/source-audit/contracts/paired-label-window-v0.2.json`. The v0.3 rerun selects **timestamp_as_interval_end from author evidence**, with all 17,544 labels present without duplicates. No heat values are aggregated, and `paired_physical_contract_accepted` remains false. Weather eligibility remains 17,539 complete hours/728 complete days; matching available labels does not erase weather NaNs or establish accepted paired measures. Report: ignored `experiments/source-audit/paired-label-window.json`, with contract/source/weather-report hashes.

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

An hourly request returns a one-minute temperature average sampled once per hour. A ten-minute request returns six such samples per complete project hour. Neither request automatically creates an hourly average. The recorded feasibility baseline retrieves ten-minute samples and declares a mean of exactly six finite sampled one-minute temperatures per complete UTC hour, with no fill. The helper currently audits coverage rather than publishing hourly means. This is not a continuous time-weighted temperature mean; retain the source times and sample-count/quality evidence. Reconcile later analytical implementation and any sampling sensitivity against the versioned contract.

The [FMI licence page](https://en.ilmatieteenlaitos.fi/open-data-licence) states CC BY 4.0. Attribute Finnish Meteorological Institute, retain the licence link and access date, and identify derived transformations. Do not imply endorsement. Metadata/query/catalogue responses and their hash/retrieval manifests are retained under `data/raw/source-documents/` and `experiments/source-audit/`.

## Proposed common period and next acceptance checks

Propose **1 January 2024–1 January 2026 in Helsinki reporting time** for the paired analysis, subject to resolving Helen physical quantity/boundary/licence; interval-end mapping is author-confirmed. Those local boundaries correspond to `2023-12-31T22:00:00Z` and `2025-12-31T22:00:00Z`; publisher-declared heat UTC labels are now evidenced. Both start/end label hypotheses have complete available-key coverage, as audited above. The full weather window has been acquired in 105 bounded chunks and audited: 105,264 expected/returned timestamps, 105,248 finite values, 16 NaNs, zero absent timestamps, 17,539/17,544 complete six-sample hours and 728/731 complete local weather days. This is not yet final paired-period acceptance or a claim of 100% weather completeness.

The five incomplete hours affect 11 September 2024, 18 November 2024 and 5 December 2025 in Helsinki time. The audit accounts for two 23-hour days, 727 24-hour days and two 25-hour days; no partial local days. Saved report: `experiments/source-audit/fmi-full-period.json`; original acquisition report preserved separately. All cached requests/content hashes/grids were revalidated without new requests. See [source contracts](16-source-contracts.md) for exact UTC missing-hour labels, source temperature range, modelling choices and limitations.

1. Resolve remaining Helen physical quantity/boundary evidence; interval-end mapping is recorded from the author; prepare a question for the author if public documentation remains insufficient. No external message has been sent.
2. Confirm applicability of the catalogue licence to the current edition; its reproducible publisher download route and exact hash match are now verified.
3. Main-station rationale/full-period coverage and the preselected alternative 100968 are recorded. Four alternative seasonal checks return 576/576 finite scoped readings without absent/duplicate keys; five saved acquisition manifests include one repeated winter response with an identical hash. Full alternative-period coverage and the fixed WP4/E7 comparison remain pending; retain the single-point proxy limitation. See [the sensitivity plan](../config/station-sensitivity-plan.json).
4. Weather baseline/coverage rules and full acquisition are recorded under D-019. Validate their analytical implementation later; do not mark the source audit as a completed model experiment.
5. Accept contracts and record decisions D-006/D-007 before source-dependent database loading or energy metrics.

See [working commands](06-local-development.md), [the decision register](04-decisions-and-questions.md) and [task status](12-execution-tracker.md).

## Subsequent WP2.3 weather implementation

[Typed FMI ingestion](21-weather-ingestion.md) now accepts the verified weather point semantics under a separate source-only contract. The full retained period has been loaded and replayed with exact row/key/NaN accounting; two bounded live requests return identical keyed/raw content. No hourly values, Gold release, heating conversion or final experiment result is implied. This extends implementation evidence without changing the original weather-audit baseline or physical paired acceptance.
