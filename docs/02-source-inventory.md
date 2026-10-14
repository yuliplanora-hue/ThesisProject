# Data source inventory and feasibility audit

**Version:** 0.3, 14 October 2026. Supports FR-01–FR-03 and WP1.3 in the [development plan](07-development-plan.md). The Helen file has now passed an explicit parsing audit, and nine FMI feasibility checks passed. Helen semantics and the final FMI station/aggregation/common-period contract remain open. See [the detailed source audit](11-source-audit.md).

## Sources and current status

| Source | Evidence available | Intended role | Open checks |
| --- | --- | --- | --- |
| [Helen open data](https://www.helen.fi/en/about-us/helen/open-data) | Publisher page checked during plan revision describes hourly district-heating power; a local CSV and profile exist | One aggregated heating-system series | Reconcile `dh_MWh` with the page’s power wording; interval meaning; UTC convention; coverage; licence/attribution |
| [FMI WFS](https://en.ilmatieteenlaitos.fi/open-data-manual-fmi-wfs-services) | Nine successful checks for candidate Kaisaniemi 100971, including repeat, seasons and 23/25-hour days | Observed temperature at one justified Helsinki station | Full-period continuity, final station rationale and hourly aggregation/coverage; parameter metadata and CC BY 4.0 licence recorded |
| Fingrid or another contextual source | No source selected or tested for this project | Possible stretch extension | Scope decision after G4; separate units, grain, credentials and licence audit |

## Helen local audit evidence

Source file: `data/raw/helen_open_dh_data_2015p01_2026p03b_v2.csv`.

Local report: `experiments/helen_profile.json`, created with `tools/profile_csv.py`. Both are ignored by Git; obtain an authorised copy to reproduce the audit. The file checksum was rechecked during this documentation update.

| Observation | Recorded value | Interpretation |
| --- | --- | --- |
| SHA-256 | `f8363dbbfa09c8a00048de4836c4029a6f4d3482ee5e4b2f99da2b1e938cfee1` | Identifies this snapshot only |
| File size | 3,244,432 bytes | Local file size |
| Rows / columns | 91,767 / `datetime_utc`, `dh_MWh` | Parsed row count and literal headers |
| Separator / encoding | Semicolon / UTF-8 with BOM support | Settings used by the generic profiler |
| Imported types | Both `object` | Timestamp and numeric contracts have not been applied |
| Missing fields | Zero reported in either column | Does not establish complete expected hourly coverage |
| Fully duplicated rows | Zero | Does not establish unique timestamp/business keys |
| Example timestamp | `12.10.2015 06:00` | First displayed record, not a verified minimum or timezone |
| Example value | `1000,0446680068969` | Decimal-comma text; physical meaning remains unverified |
| Explicit timestamp audit | 91,767 parsable rows; no duplicate timestamps, off-hour records or missing keys in the written-clock sequence | `2015-10-12 06:00` through `2026-03-31 20:00`; timezone and interval meaning remain unverified |

Verified lexical parsing rules are `%d.%m.%Y %H:%M` and decimal comma. Apply them with explicit failure reporting to each new snapshot. Do not use ambiguous automatic date parsing to establish the contract. Keep the unmodified timestamp and measurement strings.

Those lexical rules have now been exercised over the full local file with `tools/audit_helen.py`; report: `experiments/source-audit/helen-explicit-audit.json`. They establish parsability and written-clock continuity, not physical units or UTC semantics. The original generic report remains unchanged.

The [official open-data catalogue](https://www.opendata.fi/data/fi/dataset/helsingin-kaukolammon-tuotantotarve) describes Helen production need in MW and lists CC BY 4.0. Its recorded resource points to an older filename, so confirm applicability to the current snapshot before redistribution. Record catalogued evidence separately from publisher confirmation of the current file's interval/time semantics.

## Source contract checklist

For each publisher, record the following in a source manifest and a human-readable contract:

1. Publisher, dataset identity, original download/request URL, retrieval time and file/response checksum.
2. Licence version/link, required attribution and permitted redistribution; do not infer permission from public access alone.
3. Actual schema, encoding, delimiter, date format, decimal format, null markers and quality codes.
4. Timestamp timezone and whether it marks interval start, end or an instantaneous observation; retain supporting publisher evidence.
5. Physical quantity, unit, interval duration and permitted conversions.
6. Natural key, duplicate/conflict rules, source revision identity and expected update behaviour.
7. Observed coverage, expected keys, gaps, irregular intervals and out-of-range values with explanations.
8. For weather: station ID, coordinates, parameter and its unit, selection rationale, hourly aggregation and minimum coverage.
9. Query chunking, timeout/retry policy and current service limits before bulk requests.

Use [the data dictionary](05-data-dictionary.md) for canonical fields and [the architecture](08-architecture.md) for snapshot/revision handling. Exact retrieval time and original download URL are not recoverable merely from a local file’s modification timestamp.

## FMI first feasibility query

The original discovery query below returned Helsinki Kaisaniemi 100971 on 14 October 2026. The saved representative matrix uses `fmisid=100971` explicitly; exact parameters and hashes are retained in acquisition manifests:

```text
endpoint=https://opendata.fmi.fi/wfs
service=WFS
version=2.0.0
request=GetFeature
storedquery_id=fmi::observations::weather::timevaluepair
place=helsinki
parameters=t2m
starttime=2025-01-01T00:00:00Z
endtime=2025-01-02T00:00:00Z
timestep=60
```

Inspect the response and its metadata before fixing the production query. `place=helsinki` may select multiple or unexpected stations. Choose the station explicitly once verified, test representative winter/summer and DST dates, then audit the target historical range. Follow the [FMI examples and guidance](https://en.ilmatieteenlaitos.fi/open-data-manual-wfs-examples-and-guidelines) when checking request limits and licence conditions.

Verified sample metadata: station name Helsinki Kaisaniemi, coordinates `60.17523 24.94459`, `t2m` unit `degC`, aggregation period `PT1M` with statistical function `avg`, and explicit UTC observation timestamps. A `timestep=60` request samples these observations hourly; it does not compute an hourly temperature average. The [FMI licence](https://en.ilmatieteenlaitos.fi/open-data-licence) specifies CC BY 4.0. Retain attribution and identify derived transformations. See the source audit for sample results and remaining acceptance conditions.

## Common period and missing data policy

Target 24 consecutive overlapping months after both source audits. A minimum 12-month fallback must include seasons and both DST transitions; document its effect on year-to-year comparisons. Freeze start/end boundaries as a half-open UTC interval and derive Helsinki calendar labels independently.

Do not fill missing demand silently. For weather, start with an unfilled analysis; any interpolation needs a bounded rule, a flag and a sensitivity comparison. Preselect the main station and any backup before final analysis. A scheduled source check is not evidence that the publisher released new observations.

## Go or no-go evidence

| Decision | Pass evidence | Current status |
| --- | --- | --- |
| Helen analytical use | Verified quantity/unit, interval/time convention, parsable keys and documented coverage | Lexical audit passed; semantics pending |
| Helen redistribution | Applicable licence/permission and attribution instructions retained | CC BY 4.0 catalogue evidence found; current-snapshot applicability pending |
| FMI integration | Repeated query works for the selected station and representative dates; usable common history confirmed | Sample/repeat checks passed; full-period and aggregation acceptance pending |
| Common period | Frozen boundaries, calendar spine and coverage summary; limitations accepted | 2024–2025 proposed; not frozen or fully acquired |

A source may be usable for private research while redistribution remains unresolved. Publish safe synthetic fixtures and acquisition instructions in that case. If basic semantics or sufficient common history cannot be established, record the issue in D-006/D-007 and seek a revised source/scope decision instead of silently changing the dataset.

## Audit record template

```text
Source and dataset:
Publisher URL and access date:
Retrieval timestamp and request parameters:
File/response hash:
Licence and attribution evidence:
Schema/parser contract version:
Quantity, unit and interval semantics:
Timezone evidence and conversion rule:
Station and aggregation rule, if applicable:
Observed versus expected keys and exceptions:
Source update/revision behaviour:
Decision: pass / conditional pass / fail
Conditions, owner and next action:
```
