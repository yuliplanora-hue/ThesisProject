# WP1 reference fixtures and initial evaluation baseline

**Version:** 0.1, 14 October 2026. **Task:** WP1.4. This package supplies hand-calculated controls before SQL/DAX implementation. It contains **240 manufactured heat rows, 240 manufactured weather-hour rows, 11 scenarios and 55 M1–M5 answers**. The six required filter scenarios supply 30 comparisons; five targeted scenarios supply another 25. Python reference arithmetic verifies them. SQL/DAX reconciliation and final E5 remain scheduled development/evaluation work.

Inputs: [heat.csv](../tests/fixtures/wp1/heat.csv) and [weather_hourly.csv](../tests/fixtures/wp1/weather_hourly.csv). Cases/answers: [cases.json](../tests/fixtures/wp1/cases.json). Byte hashes and counts: [manifest.json](../tests/fixtures/wp1/manifest.json). Scoped `.gitattributes` rules keep these files in LF format on Windows/Linux so the published hashes survive checkout.

## Known synthetic semantics

Each heat row is manufactured interval energy in MWh over exactly one elapsed UTC hour, with the timestamp at interval start. Each weather hour represents six identical manufactured finite Celsius samples. These are canonical analytical test inputs after validation, not publisher CSV/WFS responses or sensor evidence. The system/station IDs explicitly identify synthetic data. These fixtures already use canonical interval starts. The author now confirms Helen source labels mark interval ends, so its parser must subtract one elapsed UTC hour before producing equivalent canonical keys. Synthetic inputs themselves are unchanged.

The primary miniature reporting window is Helsinki 1–3 January 2025, paired with 1–3 January 2024. Additional rows cover both spring and autumn DST days in 2024/2025. The full-period scenario means the declared three-day miniature window; it is not the thesis's proposed 24-month source period. Month selection uses the whole January calendar: absent fixture days remain expected and reduce completeness.

## Manual calculation record

| Scenario | Arithmetic / expected interpretation |
| --- | --- |
| Full period | Three 2025 days contain 24 hours each at 10, 12 and 0 MWh/hour: `240 + 288 + 0 = 528 MWh`. Reference 2024 is `240 + 240 + 0 = 480`; M3 is `100 × 48 / 480 = 10%`. Heat/weather coverage is 72/72 |
| Month | January expects `31 × 24 = 744` hours; only 72 have fixture observations. M1 is an observed 528 MWh subtotal; M4 is `100 × 72 / 744 = 9.677419…%`. M3 is blank because periods are incomplete; M5 has three eligible and 28 temperature-unavailable days |
| Day | 2 January 2025 has `24 × 12 = 288 MWh` versus 240; M3 is 20%. Peak is 12 MW with 24 ties, earliest at local midnight |
| Empty | No expected keys: energy/peak/change/completeness are blank with reason states. M5 has zero selected/eligible days |
| Missing data | Remove one 12 MWh hour and all first-day weather: observed energy `528 − 12 = 516`; heat coverage 71/72, weather 48/72. M5 classifies one temperature-unavailable day, one heat-incomplete day and one eligible zero-energy day |
| Autumn DST | 27 October 2024 has 25 hours: `25 × 10 + 2 × 10 = 270 MWh`; reference autumn day is 250, giving 8%. The two 20 MW peaks occur at `00:00Z`/`01:00Z`, both local 03:00 with distinct offsets. Earliest UTC tie wins the display label |
| Spring DST | 31 March 2024 has 23 hours: `23 × 10 = 230 MWh`; the 2025 spring reference also has 23 hours, giving 0% change |
| Zero baseline | Complete zero-energy day: M1/M2 are valid zero values; M3 is blank because the complete baseline total is zero |
| Both sources missing | Remove one 10 MWh heat hour and all first-day weather: subtotal 518; that day retains both reason flags but is counted once as temperature unavailable. Two remaining days are eligible |
| No observations | Expected day has 24 hours but zero accepted rows: M4 is 0%, energy/peak blank, change incomplete and M5 temperature unavailable |
| Unequal exposure | Pair the complete 25-hour autumn day with a complete 24-hour reference: M3 is blank even though both individually have 100% coverage |

Temperature days at −5, 0 and 5 °C exercise exact left-closed 5-degree band boundaries. The autumn day at −0.1 °C belongs to `[−5,0)`, exercising floor rounding for negative values. M5 returns per-band mean daily energy and counts, independently of underlying calendar/source completeness. Every selected day reconciles as eligible + temperature unavailable + heat incomplete; all applicable reason flags are retained.

A verification pass caught and corrected an initial hand-entered peak label: incomplete heat coverage always produces an **observed peak**, including when the surviving maximum is unchanged. The development fixture hash was updated before declaring this v0.1 baseline; this was not a failed final E5 run.

## Executed verification and later use

```powershell
.venv\Scripts\python.exe tools/check_wp1_fixtures.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The [checker](../tools/check_wp1_fixtures.py) computes direct Decimal reference arithmetic from the pinned inputs and compares it with the separately entered answers. Three [offline regression checks](../tests/test_wp1_reference_fixtures.py) cover all answers, input checksum corruption and an incorrect expected numeric answer after a valid checksum. Total offline suite after model identity/invocation, calendar reference and operations-boundary controls: 94 tests. Numeric agreement uses an absolute tolerance of `0.000001`; identifiers, counts, memberships, states, offsets and blank reasons match exactly.

In WP4/E5, implement SQL and DAX independently and apply the same input/scenario filters. Store each implementation's actual outputs separately, alongside fixture/metric/release/version identifiers; preserve failures and retests. The checker is a reference-control utility, not production modelling code. Do not populate final SQL/DAX result records with its expected answers.

## Predeclared analytical split

[analysis-split-plan.json](../config/analysis-split-plan.json) declares calendar 2024 for development and 2025 for holdout before heat modelling, conditional on accepted paired source alignment. Both sides cover a full seasonal cycle. Learn preprocessing, feature/model choices and diagnostic-driven uncertainty settings on development data only. Use the same split for the preselected station sensitivity and report common-day eligibility and source exclusions. If the accepted period cannot support this split, record the replacement and seasonal limits before inspecting heat-model outcomes. G5 still freezes the exact accepted input/model/environment versions.

## Author-only walkthrough fallback

The author selected this fallback on 14 October 2026. If independent reviewers are unavailable, execute AT-01–AT-05 using the fixed [task/rubric](13-scope-and-method.md). Use the [empty recording template](evaluation/author-walkthrough-template.csv) for initial and retest correctness, time, assistance, evidence and limits. No scores or reviewer participation are prefilled.

Preserve the initial attempt; diagnose defects; retest each failed task against a new recorded version. All five tasks must have correct final answers and traceable evidence. Report this as author verification with no independent-user usability claim. Independent recruitment, if later possible, uses the existing E6 procedure and requires its privacy/retention arrangements before collection.
