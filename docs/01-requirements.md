# Requirements baseline

**Version:** 0.3, 14 October 2026. Aligned with Sections 1–10 of the [revised thesis research plan](Li_Yu_Thesis_Research_Plan.docx). These are proposed acceptance criteria. The author confirmed supervisor approval of the revised topic and RQ1/RQ2; academic workload/dates and final experiment results remain pending.

## Purpose and research questions

Public heating and weather time series differ in schema, temporal semantics, measurement meaning and publication history. The platform must make the chain from original records to reported findings reproducible and inspectable.

The intended users are an energy analyst and a data engineer. They remain design personas until reviewed; no utility partnership or operational user requirement is assumed.

- **RQ1:** To what extent does the designed pipeline meet predefined requirements for completeness accounting, traceability, idempotency and recovery when integrating Helen and FMI data?
- **RQ2:** To what extent do the dimensional and semantic models reproduce independently calculated measures and support predefined district-heating analysis tasks?

Forecasting is a possible extension, not a third required research question. Claims of improvement require a comparable baseline; absolute reliability and correctness measurements are sufficient to answer the current questions.

## Scope and analytical tasks

Required scope: one aggregated heating system, Helen and FMI, an audited common historical period, three report pages, M1–M5 and E1–E7. Target 24 consecutive months; if infeasible, agree at least 12 months covering seasons and DST transitions and limit affected comparisons.

| Task | Reviewer should be able to do |
| --- | --- |
| AT-01 | Identify a peak and its timestamp, unit and coverage limitation |
| AT-02 | Compare two matched complete periods and explain the comparison basis |
| AT-03 | Explain a historical demand–weather pattern and its uncertainty |
| AT-04 | Diagnose missing coverage and distinguish source gaps from processing losses |
| AT-05 | Trace one reported measure through its model and run to the source revision |

## Functional requirements

Core means required for the proposed local thesis artefact. Conditional means dependent on actual cloud access. Stretch requires a scope decision after G4. IDs FR-01–FR-10 are retained for continuity; additional requirements capture the revised plan.

| ID | Requirement | Priority | Acceptance evidence | Work package |
| --- | --- | --- | --- | --- |
| FR-01 | Preserve Helen source snapshots, checksums, acquisition metadata and original values | Core | E1 lineage trace and immutable revision record | WP1, WP2 |
| FR-02 | Extract documented FMI station/temperature observations with bounded requests and provenance | Core | Repeatable source query and E1 contract checks | WP1, WP2 |
| FR-03 | Resolve source interval/timezone semantics, retain originals and model UTC plus Helsinki reporting time | Core | E1 DST, leap-day and interval fixtures | WP1, WP2, WP3 |
| FR-04 | Implement raw, validated and analytical layers with explicit contracts and rejected-record reasons | Core | E1 accounting and E3 publication checks | WP2, WP3 |
| FR-05 | Support same-revision replay, corrected revisions and overlapping backfills | Core | E2 unchanged rerun and controlled correction | WP2, WP3 |
| FR-06 | Build an hourly star model and a station-selected heat/weather view without row multiplication | Core | E1/E5 grain, relationship and cardinality checks | WP3 |
| FR-07 | Implement M1–M5 in SQL and Power BI with common definitions and explicit filter rules | Core | E5 at least 30 measure/filter comparisons | WP3, WP4 |
| FR-08 | Log stage counts, provenance, failures, retries and recovery; publish analytical output atomically | Core | E2/E3 run ledger and recovery evidence | WP2 |
| FR-09 | Compare next-day forecasts using only predictors available at issue time | Stretch | Separate chronological baseline protocol; not E1–E7 | Unallocated |
| FR-10 | Add a separately modelled contextual source such as Fingrid | Stretch | Approved unit/alignment contract and scope budget | Unallocated |
| FR-11 | Provide a clean-checkout local environment, migrations, automated tests and CI with safe fixtures | Core | E4 reproduction and deliberately failing CI check | WP2, WP3, WP7 |
| FR-12 | Separate loader/reporting privileges and demonstrate backup/restore and one measured optimisation | Core | E4 access/restore checks; performance sub-study | WP2, WP3, WP6 |
| FR-13 | Produce a reproducible historical statistical case study with uncertainty and sensitivity checks | Core | E7 model/notebook regeneration and reviewed interpretation | WP4 |
| FR-14 | Deliver three report pages, an Excel audit, a two-page memo and five analytical tasks | Core | E5–E7, three supported findings and task rubric | WP4, WP6 |
| FR-15 | Demonstrate one Fabric pipeline/Lakehouse slice, Delta/PySpark processing and operational evidence | Conditional | Executed run/replay/recovery and cloud/local result comparison | WP5 |
| FR-16 | Deliver academic answers, research evidence and two portfolio case studies with honest claims | Core | G6/G7 evidence review and competency log | WP1, WP6, WP7 |

## Nonfunctional requirements

| ID | Requirement | Acceptance rule |
| --- | --- | --- |
| NFR-01 | Repeatability | Identical revision/configuration produces identical keyed curated values; variable execution metadata is excluded from equality |
| NFR-02 | Correctness | Zero duplicate curated business keys, unexplained join multiplication or silent schema coercion |
| NFR-03 | Completeness accounting | Expected keys, source absence, validation rejects and processing loss are separately reported; actual source coverage need not be 100% |
| NFR-04 | Observability | Each run records source revisions, configuration/commit, stage counts, retries, duration and final status |
| NFR-05 | Analytical accessibility | E6 uses five fixed tasks; target 4/5 without assistance per reviewer and all five correct after resolving issues |
| NFR-06 | Security and publication | Secrets excluded; reporting writes denied; data/reviewer sharing follows documented permission and retention decisions |
| NFR-07 | Portability | Core research and safe-fixture reproduction run locally when Fabric access is unavailable |
| NFR-08 | Measured performance | Five measured repetitions after declared warm-up; median/range and environment recorded; unchanged results after optimisation |
| NFR-09 | Recovery | A failed load exposes no partial Gold release; a recovered run matches the clean reference |
| NFR-10 | Metric agreement | Exact key/count equality; numeric tolerance and empty-value behaviour follow the evaluation protocol |
| NFR-11 | Feasible scope | 500 planned hours plus 60 contingency at 20 hours/week; cloud work capped at 50 hours |
| NFR-12 | Evidence integrity | Source facts, design assumptions and actual results are distinguishable; failed criteria and limitations remain visible |

## Traceability and exclusions

Use [E1–E7](03-evaluation-protocol.md), [M1–M5](09-metric-catalog.md), the [task backlog](07-development-plan.md) and [competency IDs](10-competency-evidence.md) together when reviewing completion. Technical tests support research claims; tool installation alone does not satisfy a competency.

Excluded from the core: hydraulic simulation, DGN/CAD automation, individual-customer records, operational utility control, streaming, multi-cloud deployment, Kubernetes, full infrastructure-as-code and generative-AI applications. After G4, choose at most one stretch extension within remaining hours. Do not replace evaluation or writing with additional features.

## Approval and feasibility checks

- [x] Supervisor approval of the revised topic and RQ1/RQ2 confirmed by the author on 14 October 2026.
- [ ] Record the approval reference and confirm programme-specific contribution/assessment details with the supervisor.
- [ ] Workload, Wihi milestones and any commissioner/permit requirements settled.
- [ ] Helen units, interval/time semantics and publication permissions recorded.
- [ ] FMI station, usable common period and query constraints verified.
- [ ] Metric/filter definitions and evaluation thresholds frozen before final tests.
- [ ] Fabric access and the local fallback recorded; no cloud skill claimed from design alone.
- [ ] Reviewer arrangements or the scripted fallback selected.

G1 and G5 completion records belong in the [decision register](04-decisions-and-questions.md); unchecked items are not implied approvals.
