# Metric catalogue and analytical tasks

**Version:** 0.2, 14 October 2026. M1–M5 follow Section 5 of the [research plan](Li_Yu_Thesis_Research_Plan.docx). The filter, binning and blank-value rules below are development definitions to validate in WP4.1 and freeze before E5. [Fifty-five synthetic reference answers](19-reference-fixtures.md) now have hand controls and Python arithmetic verification; production SQL/DAX measures and reconciliation remain unimplemented. The definition version is unchanged because the fixtures operationalise these existing rules.

**Definition owner:** Li Yu, unless a different owner is explicitly agreed. **Review:** supervisor and available analyst/domain reviewer. **Execution:** SQL reference plus independently written Power BI/DAX calculation against the same accepted release.

## Shared calculation contract

- Pin source revisions, station, configuration, contract and Gold release for each comparison.
- Use UTC keys and explicit Europe/Helsinki reporting dates. Local days may contain 23, 24 or 25 expected hours.
- Apply filters to the expected calendar/system scope before computing quality denominators; do not derive expected coverage solely from surviving facts.
- Use only accepted measurements for observed aggregates. Do not replace missing demand with zero or silently fill weather.
- Distinguish no selection/no expected keys, missing measurements, incomplete coverage and invalid physical semantics. Display an appropriate blank/reason state.
- No visual should imply that an archived observation is live: show newest source observation and last successful ingestion separately.
- MW/MWh conversion is blocked until quantity and interval meaning are verified. If the source is instantaneous power and energy cannot be justified, revise the affected metric scope with the supervisor rather than fabricate M1/M3/M5 energy results.

## Metric overview

| ID | Measure | Grain and unit | Main task |
| --- | --- | --- | --- |
| M1 | Period energy | Selected system/period, MWh | AT-02 comparison |
| M2 | Peak demand and time | Selected system/period, interval-average MW plus timestamp | AT-01 peak |
| M3 | Comparable-period change | Matched complete periods, percent | AT-02 comparison |
| M4 | Data completeness | Expected system/source-hour keys, percent | AT-04 quality |
| M5 | Demand by temperature band | Aligned complete Helsinki days grouped by band, mean MWh/day and sample count | AT-03 weather pattern |

AT-05 provenance applies to all metrics. Freshness/ingestion indicators support interpretation without expanding the five-metric core.

## M1 Period energy

**Inputs:** accepted `energy_mwh` at the system × UTC-hour grain. If the publisher provides verified interval-average power, derive interval energy as average MW × elapsed interval hours before summing.

**Formula:** sum accepted interval energy within the selected period. Partial intervals require an explicitly justified allocation rule; the initial report uses whole validated hourly intervals.

**Missingness:** no accepted observations produces blank, not zero. An incomplete selection may show an explicitly labelled observed subtotal alongside M4 and a missing-hours count. It must not be presented as a complete period total. Observed zero is a valid numeric result only when supported by valid source measurements.

**Test examples:** a tiny complete fixture with energies 10, 20 and 30 MWh yields 60 MWh; removing an expected hour leaves a flagged observed subtotal and lower completeness. These are synthetic expected values, not Helen findings.

## M2 Peak demand and time

**Inputs:** verified interval-average MW, either provided directly or derived as `energy_mwh / interval_hours` when the source is interval energy. Do not treat instantaneous values as interval averages.

**Formula:** maximum accepted interval-average power in scope. Return the UTC timestamp, local timestamp with offset and number of tied intervals. Proposed tie rule for a single display label: earliest UTC interval; retain all ties in drill-through.

**Missingness:** an empty/invalid scope is blank. For incomplete coverage, label the result as the observed peak and display M4; do not claim an unobserved interval could not have a higher value.

**Test examples:** equal maxima retain a tie count; the autumn repeated local hour remains distinguishable by UTC/offset. Converting an interval-energy fixture with a non-unit duration uses the actual duration.

## M3 Comparable-period change

**Inputs:** M1 totals for explicitly paired periods A and B and completeness for both. Start with a versioned mapping of comparable calendar periods, not an unconstrained “previous period” visual shortcut.

**Formula:** `100 * (energy_A - energy_B) / energy_B`.

**Proposed eligibility:** both periods are complete for the selected system, use the same measure/unit policy and have equal expected elapsed-hour exposure under the chosen comparison mapping. For example, matching complete January periods may be eligible; leap-day or DST exposure differences must be handled explicitly. If a normalised comparison is later needed, approve and version its definition rather than silently changing M3.

**Blank cases:** missing comparison mapping, incomplete period, unequal exposure, no expected keys or zero denominator. Return the reason. A negative result is a decrease; do not present percentage change as a causal weather or efficiency effect.

**Test examples:** 120 versus 100 yields +20%; 80 versus 100 yields −20%; a zero baseline or incomplete period returns blank with a reason. Cross-check percentage-point display scales in E5.

## M4 Data completeness

**Inputs:** the expected hourly spine for the requested system/source and period, plus accepted distinct keys. Keep separate heating and weather completeness calculations; one source’s presence does not certify the other.

**Formula:** `100 * accepted_distinct_expected_keys / expected_keys`.

**Rules:** no expected keys yields blank/not applicable; expected keys with zero accepted observations yield 0%. Duplicate records cannot inflate the numerator. A source-hour can be accepted, absent, rejected or an unexplained processing loss. The selected period, system/station and quality scope must be identical in numerator and denominator.

Keep completeness independent of temperature/value filters that would remove missing rows. For temperature-band displays, show coverage for the underlying selected calendar scope and the eligible-day count separately. Do not recalculate the denominator from rows surviving the band join.

**Test examples:** 22 accepted of 23 expected hours gives `100 * 22 / 23`; 24 accepted of 25 expected gives 96%. The expected counts come from the Helsinki day’s UTC boundaries, not a constant 24.

## M5 Demand by temperature band

**Inputs:** the station-selected hourly alignment view, complete heating days and weather days meeting the frozen sample-coverage rule. The observed-only baseline excludes days failing either condition and reports how many were excluded. Any interpolation is a separate flagged sensitivity scenario.

**Daily transformation:** sum validated daily heat energy, compute a documented daily temperature summary from the verified hourly aggregation, retain elapsed-hour count and expected/observed samples. If observations represent equal hourly coverage, the daily temperature is their mean; use justified duration weights if the verified representation requires them.

**Proposed bands:** Celsius intervals of width 5, left-closed and right-open, with lower boundary `5 * floor(daily_temperature / 5)`. This avoids arbitrary truncation of negative temperatures and is a development choice to freeze before final analysis.

**Output:** mean daily energy within each band plus eligible-day count and the band boundaries. Report the overall excluded-day count against the selected calendar, independently of band filters. Assign every selected day exactly one status: eligible; temperature unavailable/below the coverage threshold; or heat incomplete when temperature is usable. Retain all applicable reason flags while using this precedence for mutually exclusive counts. Days with unusable temperature have no analytical band and belong in an explicit quality category, never a fabricated zero-temperature band. Heat-incomplete days with usable temperature may have a per-band exclusion count; these counts must not pretend to include days whose band is unknown.

Require `selected_calendar_days = eligible_days + temperature_unavailable_days + heat_incomplete_days`. Include a fixture with an entirely missing weather day and a day missing both sources. No eligible days means blank mean and zero eligible count. Compare mean values numerically and counts/band membership exactly in E5. Display day duration/season context; 23/25-hour days require explicit treatment in the statistical sensitivity analysis.

M5 is a descriptive summary. The statistical notebook adds calendar/season adjustment, a calendar-only baseline, chronological holdout, residual diagnostics and time-series-aware uncertainty. Band differences alone do not establish a causal temperature effect or predict future demand.

## Report pages and interpretation

| Page | Content | Review check |
| --- | --- | --- |
| Demand and comparable periods | M1–M3, hourly/daily/seasonal patterns, peak drill-through and coverage cues | AT-01/AT-02 answered with correct units, periods and limitations |
| Weather and patterns | M5, scatter/distribution summaries, model interpretation and sample sizes | AT-03 distinguishes association, uncertainty and missingness |
| Quality and lineage | M4, expected/observed/flagged hours, source revision, run and freshness indicators | AT-04/AT-05 diagnose gaps and trace a measure |

Use readable units, accessible colours, tooltips, keyboard navigation and clear filter context. Retain a two-page memo with three supported findings and proposed follow-up actions. Savings, emissions reduction and operational control claims need additional data and are outside this core.

## Validation matrix and artefacts

E5 requires each metric over full period, month, day, empty selection, missing-data period and DST boundary: at least 30 comparisons. A legitimate invalid/blank result must match in SQL and DAX. Add ties, zero denominator, band boundaries and a mismatched-release failure as targeted cases.

The current [WP1 fixture cases](../tests/fixtures/wp1/cases.json) cover the six required filters and five targeted scenarios, including both DST transitions, zero baseline, missing both sources, no observations and unequal exposure. Blank reasons, observed subtotals/peaks, source-specific completeness and excluded-day precedence are explicit. Run `tools/check_wp1_fixtures.py` for reference verification; later SQL/DAX actual outputs and release-conflict tests are separate evidence.

Proposed evidence: `powerbi/` for readable measures/model definitions and exports, `analytics/` for statistical code and `experiments/e5/` for comparison records. Include metric version, exact filter parameters, SQL, DAX, release ID, values, blank reason and tolerance. See [the evaluation protocol](03-evaluation-protocol.md) for exact agreement rules.

## Change rule

Resolve source-unit decisions before finalising M1/M2 and dependent M3/M5 calculations. At G4 demonstrate the five definitions on fixtures and the accepted sample; at G5 freeze them for final evaluation. Changes after that require a decision record, new metric version and rerun of affected E5/E7 evidence.
