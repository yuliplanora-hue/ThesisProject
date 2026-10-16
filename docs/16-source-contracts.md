# WP1 source-contract decisions and acceptance conditions

**Version:** 0.5, 14 October 2026. **Task:** WP1.3. **Owner:** Li Yu. Separate verified source properties, author statements, modelling choices and unresolved publisher evidence. MWh/DH and interval-end labels are author-provided; current publisher download and declared UTC labels are verified. Weather feasibility and station sensitivity have declared baselines. Paired acceptance still requires Helen physical quantity/boundary/licence decisions. These contracts are not completed pipeline experiments.

## Helen contract: lexical rules and author-provided unit baseline

Machine-readable definition: [helen-source-contract.json](../config/helen-source-contract.json), v0.4. On 16 October the author also clarified **consumption**. This interpretation is author-provided; it does not replace the publisher’s conflicting power/production wording or confirm a customer-meter boundary. On 14 October 2026 the author stated that the unit is `mhw` and `dh` means district heating. This record normalises the unit spelling to **MWh**, matching `dh_MWh`, and records its author-provided provenance. Successful publisher reacquisition and chart `Date.UTC` parsing now establish current-file provenance and declared UTC labels. Interval-end mapping is author-confirmed. Physical quantity/system boundary and current-edition licence remain open; no publisher reply is inferred. Exact acquisition/hashes are in [the source audit](11-source-audit.md).

The author's later UTC+3 statement was clarified as **website/computer display time**. It does not change the raw UTC contract. A label `10:00` representing `[10:00,11:00)` is an interval-start label; representing `[09:00,10:00)` is an interval-end label. The author now specifies that `10:00` covers `09:00–10:00`. Although called “interval start” in the statement, that explicit coverage defines an **interval-end label**. Contract v0.3 preserves the statement and records its author-provided basis: `interval_end_utc = source_label_utc`; `interval_start_utc = source_label_utc - 1 elapsed hour`. Derive Helsinki display labels afterwards. This is not a publisher confirmation. Contract v0.2 and its audit are preserved under ignored `experiments/source-audit/contracts/` for earlier run configuration hashes.

| Property | Current decision / evidence |
| --- | --- |
| Snapshot | Existing local CSV exactly matches publisher-linked reacquisition at 14:21:23 UTC on 14 October 2026; 3,244,432 bytes, SHA-256 `f8363dbbfa09c8a00048de4836c4029a6f4d3482ee5e4b2f99da2b1e938cfee1` |
| Parser | Exact two-column semicolon schema, UTF-8 BOM support, `%d.%m.%Y %H:%M`, decimal-comma Decimal; unknown schemas/noncanonical values fail visibly |
| Coverage | 91,767 distinct hourly labels, no gaps within the observed range; declared UTC label interpretation verified separately. Both proposed paired start/end hypotheses have 17,544/17,544 labels; interval-end mapping now selected from author evidence |
| Quantity / label | Author-provided consumption/MWh, with `dh` meaning district heating; header matches this unit spelling. Publisher/city catalogue still use power/production-need wording in MW. Reconcile interval representation before any power/energy conversion |
| Time and interval | Publisher-declared UTC labels accepted from linked header and chart `Date.UTC` parser. Author confirms interval-end labels: `10:00` represents `[09:00,10:00)`; no inferred interval energy or sensor-clock accuracy certification |
| System boundary | Aggregated production need is not automatically customer consumption, useful delivered heat or efficiency; confirm boundary before report wording |
| Licence | HRI CC BY 4.0 catalogue links a byte-distinct older 2015–2024 CSV; applicability to the verified current edition remains pending. Raw redistribution not accepted |
| Original acquisition | Retrieval time/URL unknown for the existing file; do not reconstruct them from filesystem dates |
| Revisions / omissions | Preserve snapshots. Do not choose conflicting observation revisions by download time alone. Define full-snapshot versus partition/delta scope before interpreting omission as deletion |

The [source-intake contract](../config/helen-ingestion.json) now permits local unconverted typed values, row lineage and quarantine under the accepted UTC/end-label mapping; [load/replay evidence](25-helen-source-intake.md) does not approve an analytical heating release. Prior contract v0.3 is archived privately.

If equal business keys conflict without a verified publisher precedence rule, retain both raw revisions and stop analytical publication of the ambiguous candidate. A later contract may explicitly choose a frozen snapshot as the evaluation reference, with limitations recorded; it must not silently treat arbitrary download order as publisher version order.

### Clarification draft for the author

Subject: Clarification of public Helsinki district-heating CSV units and timestamps

I am preparing a master's thesis using the public district-heating dataset linked from Helen's open-data page. My local file is `helen_open_dh_data_2015p01_2026p03b_v2.csv`, with columns `datetime_utc` and `dh_MWh` and hourly timestamps. The page/catalogue describes hourly power or production need in MW.

1. The author uses MWh for `dh_MWh`. Can you confirm that this is interval energy and explain its relationship to the page/catalogue's MW wording?
2. The current linked file and chart parser declare UTC. The author interprets `10:00` as the end of `[09:00,10:00)`. Can you corroborate that convention?
3. What does the aggregated series cover: required plant production, supplied network heat, delivered customer heat, and/or network losses?
4. The current CSV download has been verified, while HRI links a distinct older edition. Does the catalogue's CC BY 4.0 licence also apply to this current CSV, and what attribution/version reference should I cite?
5. How are corrections/new revisions indicated, and can a replacement snapshot remove historical values?

This is a draft only. No message has been sent and no reply/approval is inferred. Record any received statement, date and permitted reference under D-006/D-005.

## FMI weather contract: executed feasibility baseline

Machine-readable definition: [fmi-source-contract.json](../config/fmi-source-contract.json). It was declared before the full-period request; response/manifests and inspection evidence are locally retained.

WP2.3 now accepts a separate [source-resolution ingestion contract](../config/weather-ingestion.json) for these verified point semantics, source stations and missing-value rules. [The typed loader](21-weather-ingestion.md) has loaded/replayed the full retained baseline and demonstrated repeated bounded live extraction. The original feasibility contract is unchanged, preserving the period report's configuration hash. Weather-only ingestion acceptance does not resolve the paired heating contract, publish hourly values or pass final experiments.

WP2.4 now [publishes that explicit weather source set](22-weather-publication.md) with quality accounting, source-layer selection, atomic acceptance/checkpoint and interruption recovery. This is a source-point weather release, separate from hourly/paired heating Gold acceptance.

| Property | Baseline |
| --- | --- |
| Source/query | FMI WFS `fmi::observations::weather::timevaluepair`, explicit `fmisid=100971`, `parameters=t2m` |
| Station | Helsinki Kaisaniemi; returned EPSG:4258 coordinates `60.17523 24.94459` |
| Parameter semantics | Celsius (`degC`), one-minute source average (`PT1M`), point timestamp in UTC; a request timestep selects samples rather than averaging them |
| Weather window | `2023-12-31T22:00:00Z` to exclusive `2025-12-31T22:00:00Z`; Helsinki calendar years 2024–2025 |
| Acquisition | Ten-minute samples, at most seven days/request; bounded retries/timeouts and 2 MB response limit; endpoint points outside the project half-open interval excluded |
| Hourly baseline | Mean of exactly six finite sampled one-minute temperatures per UTC hour; otherwise missing analytical value and explicit quality status |
| Daily baseline | Complete weather days only; expected 23/24/25 hours from the Helsinki calendar. Heat completeness is checked independently later |
| Missingness | No fill. An absent timestamp and a returned NaN have different accounting states. No interpolation or silent zero |
| Revision | Immutable response snapshots plus retrieval attempts. Use an explicitly frozen response set for evaluation; conflicting future corrections need the declared precedence/review policy |
| Licence/attribution | [FMI CC BY 4.0](https://en.ilmatieteenlaitos.fi/open-data-licence); cite Finnish Meteorological Institute, access date, licence link and derived transformations |

Kaisaniemi is selected as the **project baseline station** because it is an identified central urban Helsinki point with successful explicit historical extraction and a well-accounted 24-month temperature window. This is a pragmatic proxy decision, not proof that one station represents temperature across the whole heating network. D-022 preselects Helsinki-Vantaa airport for the later WP4/E7 sensitivity comparison before heat modelling.

### Preselected station sensitivity

Definition: [station-sensitivity-plan.json](../config/station-sensitivity-plan.json). Alternative `100968` is identified as **Vantaa Helsinki-Vantaan lentoasema** in [FMI's station table](https://www.ilmatieteenlaitos.fi/1991-2020-auringonpaiste-ja-sateilytilastot) and the inspected WFS responses, which return coordinates `60.32937 24.97274`. Its airport setting provides a practical comparison with the central urban station; neither is asserted to measure network-average temperature.

Four predeclared UTC-day samples (15 January/15 July in 2024 and 2025) each return 144/144 expected ten-minute temperatures, all finite, no duplicates or missing timestamps: 576 distinct scoped sample keys in total. Five acquisition manifests exist because the first winter sample was acquired again while finishing the audit wrapper; repeated response hashes match. Raw responses/manifests remain local and ignored. Report: `experiments/source-audit/station-sensitivity/feasibility.json`.

Before the final comparison, audit the alternative's accepted-period history, apply identical six-sample/hour and complete-day rules, and compare on common eligible heat/weather days. Report station-specific exclusions separately; hold model specification, split boundaries and uncertainty policy fixed. Fit any learned sensitivity model on development data only. The four checks prove bounded extraction feasibility, not complete alternative-station history or a passed E7.

The hourly mean is the mean of sampled one-minute source averages, not a continuous time-weighted hourly temperature. Full finite-value coverage does not certify meteorological sensor accuracy or all source quality flags. Range/profile checks and sensitivity remain part of validation/analysis. The baseline threshold was recorded before the full audit, so it is not chosen to conceal observed gaps.

## Full weather-window evidence

| Count | Result |
| --- | --- |
| Weekly half-open chunks | 105; all inspected |
| Expected / returned sample timestamps | 105,264 / 105,264 |
| Finite samples / absent timestamps / NaN samples | 105,248 / 0 / 16 |
| Expected / complete six-sample hours | 17,544 / 17,539 |
| Expected / complete weather days | 731 / 728; no partial local days |
| Calendar distribution | Two 23-hour days, 727 24-hour days, two 25-hour days |
| Finite source temperature range | −21.1 to 28.2 °C; plausibility profile, not independent accuracy certification |
| Accounting | Expected samples equal finite + absent + NaN; duplicate in-scope/chunk-overlap keys rejected |

Five incomplete hours (UTC): 2024-09-11 10:00 and 11:00; 2024-11-18 10:00; 2025-12-05 08:00 and 09:00. Three Helsinki weather days fail the complete baseline: 11 September 2024, 18 November 2024 and 5 December 2025. Report these in later quality/eligibility outputs; do not call the whole period 100% complete.

Full report: ignored `experiments/source-audit/fmi-full-period.json`. Initial acquisition ran 11:59:09–12:00:04 UTC on 14 October 2026; its report is preserved as `fmi-full-period-initial-2026-10-14.json`. Cached revalidation rechecks request/hash/point-grid identity and regenerates coverage without new source requests. Exact raw/manifests identify observations independently of the report's execution time.

## Paired-period acceptance and decisions

The weather window is a fixed feasibility reference. The paired Helen/FMI reporting-period decision is still **conditional**: UTC observation-label accounting is now evidenced, and both possible start/end label ranges are complete. Author evidence now selects interval-end labels; coverage alone does not. Required labels are `[2023-12-31T23:00:00Z,2025-12-31T23:00:00Z)`, representing canonical intervals `[2023-12-31T22:00:00Z,2025-12-31T22:00:00Z)`. Review heating/weather eligibility together after physical quantity/boundary acceptance. Do not interpret available labels as accepted physical measures or as permission to derive M1/M2.

The weather-only audit can be reused for WP2.3 implementation. Before declaring WP1.3 done, close Helen physical quantity/boundary and current-edition licence evidence, and record final accepted source keys, boundary/revision policies and paired period. Download provenance and declared UTC labels are closed for this reacquisition; original local retrieval details remain unknown. Before G5, freeze the precise source snapshot set, station sensitivity choice and all relevant contract/configuration versions.

See [the source audit](11-source-audit.md), [the inventory](02-source-inventory.md), [the data-management plan](15-data-management-plan.md) and [the decision register](04-decisions-and-questions.md).
