# WP1 scope, analytical tasks and research method

**Version:** 0.1, 14 October 2026. **Task:** WP1.1. The author confirmed supervisor approval of the revised topic and RQ1/RQ2. This is the operational scope record; approval reference, programme workload, contribution/assessment details and official academic dates remain to be recorded.

## Problem and intended contribution

The project investigates whether explicit source contracts, controlled revisions and tested measures make an aggregated heating/weather analysis reproducible and inspectable. Parsing a file successfully does not establish its units, its time meaning or the correctness of a reported comparison. A failed pipeline must also leave the last accepted analytical output usable.

The artefact is one local Python/PostgreSQL/SQL/dbt/Power BI platform and its evaluation evidence. The expected contribution is a bounded requirement–design–experiment–result account and transferable design lessons. Combining popular tools does not establish novelty. The [targeted critical comparison](17-critical-literature-notes.md) positions the contribution against existing reproducibility/domain work, including an existing spatial open-data heating tool; final literature positioning remains provisional. Analyst/engineer competency evidence supports the portfolio but is separate from the academic contribution.

## Agreed research-question baseline

- **RQ1:** To what extent does the designed pipeline meet predefined requirements for completeness accounting, traceability, idempotency and recovery when integrating Helen and FMI data?
- **RQ2:** To what extent do the dimensional and semantic models reproduce independently calculated measures and support predefined district-heating analysis tasks?

The source pair is Helen and FMI, one aggregated Helsinki heating system, target 24 overlapping months, five measures, three report pages and E1–E7. The FMI weather window covers Helsinki calendar years 2024–2025. The paired heat/weather period is conditional on Helen timezone/interval confirmation. Forecasting and additional sources have no allocated core hours; at most one approved stretch extension follows G4. Full hydraulic modelling, operational utility control, customer-level inference and streaming remain outside the scope.

## Personas and operational tasks

These are design personas, not recruited stakeholders or a utility partnership.

| Persona | Decision or responsibility | Required evidence |
| --- | --- | --- |
| Energy analyst | Explain peaks, matched-period changes and observed weather associations with uncertainty and coverage limits | M1–M5, reference queries, a statistical case study and a decision memo |
| Data engineer | Diagnose a missing/failed batch, recover it and trace the published result to source/configuration/revision | Run/input/release ledger, coverage accounting, E1–E4 and a runbook |

The following task wording is the initial E6 pilot baseline. WP4.5 may clarify it before the G5 freeze; preserve the wording version and initial/retest evidence. Actual reference answers will be generated from the accepted frozen report release before reviewers participate.

| Task | Initial wording | Correct-answer rubric | Links |
| --- | --- | --- | --- |
| AT-01 | For the selected period, identify the observed peak, its time and any coverage limitation. | Correct peak and verified unit; unambiguous UTC/local-offset time; ties acknowledged; incomplete coverage described when present | M2/M4; FR-03/FR-07/FR-14; E5/E6 |
| AT-02 | Compare the two declared complete January periods and explain the basis and direction of change. | Correct paired periods, verified totals and percent direction; eligibility/completeness checked; invalid comparison explained rather than forced numeric | M1/M3/M4; FR-07/FR-14; E5/E6 |
| AT-03 | Describe one historical demand–temperature pattern and the uncertainty that limits its interpretation. | Supported band/model result with sample size; missingness/seasonality limitations; association kept distinct from a causal or operational effect | M5; FR-13/FR-14; E6/E7 |
| AT-04 | Investigate a declared missing-coverage case and identify where the absence arose. | Expected denominator identified; source absence/invalid source value distinguished from processing loss; relevant quality record located | M4; FR-04/FR-08/FR-14; E1/E3/E6 |
| AT-05 | Trace one reported measure to its analytical release, processing run and source revision. | Correct release/run/snapshot and source row or contributing weather samples; configuration/metric version identified | FR-01/FR-02/FR-08/FR-14; E1/E5/E6 |

Task success requires the mandatory rubric parts. Record assistance separately from correctness. The target remains four of five correct without assistance per reviewer, with all five correct after issues are resolved; retests do not erase initial scores. The author-only fallback is verification evidence and cannot establish independent-user usability.

## Design Science Research implementation

Use the six-stage DSRM baseline from Peffers et al. ([L01](literature/literature-matrix.csv)); distinguish formative development checks from the final summative evaluation using FEDS ([L02](literature/literature-matrix.csv)). Application of those frameworks to this project is a design choice, not a claim that they prescribe PostgreSQL or Power BI.

| Stage | Project activity | Evidence location or gate |
| --- | --- | --- |
| Problem and motivation | Source-semantic ambiguity, reproducibility and analytical-task framing | This scope record, literature matrix, G1 |
| Objectives | Operationalise reliability, correctness, coverage and task success | FR/NFR, metric catalogue and E1–E7 protocol |
| Design and development | Build and test small source-to-model-to-report increments | Code, contracts, migrations, decisions, WP2–WP4 |
| Demonstration | Show accepted historical examples and controlled replay/recovery | G2–G4 demonstrations; clearly labelled formative evidence |
| Evaluation | Execute frozen engineering/analytical procedures in the declared local reference | G5 protocol/configuration freeze; G6 final results |
| Communication | Report RQ answers, failed criteria, limitations and design lessons | Academic report, runbook, memo and portfolio |

E1–E5 and E7 mainly use controlled artificial/computational checks. E6 offers bounded task feedback from independent reviewers if available; its convenience sample and lack of a utility deployment limit external validity. No final evaluation is considered passed by writing a protocol or running preparatory source audits.

## Unit of analysis and validity

- Source reliability: one observation key, source revision, execution attempt and accepted release. Raw sample counts and hourly aggregates remain separate.
- Analytics: one system-hour for heating, one station-sample/hour for weather, Helsinki reporting days for the descriptive/statistical case study, and one reviewer-task attempt for E6.
- Reliability/correctness: compare known expected keys, values and fault outcomes with actual results; do not infer correctness from agreement between two implementations alone.
- Statistical interpretation: predeclare the chronological split before model selection, use development-only learned preprocessing and preserve the holdout. Source coverage audits over the full window do not constitute fitting a heat-demand model.
- External validity: limit claims to the source pair, selected station, period and local reference. Customer/building results from other studies do not establish equivalent behaviour for aggregated Helsinki production need.

## Approval and completion record

| Item | Status | Owner / next record |
| --- | --- | --- |
| Revised topic and RQ1/RQ2 | Supervisor approval confirmed by author on 14 October 2026 | Li Yu; record reference, supervisor and approval date when provided |
| 50–55 hours/week and end-of-2026 deadline | Author-confirmed replacement for the earlier 20-hour/May baseline; full scope retained | Revised 11-week calendar allocates the 560-hour estimate; academic workload sufficiency remains pending |
| Personas, scope and task/rubric draft | Documented | Pilot/review later; no independent validation claimed |
| Master’s-level contribution/assessment details | Pending | Supervisor/programme agreement |
| Submission target and programme milestones | End-of-2026 deadline author-confirmed; exact Wihi/review dates pending | November–May assumptions superseded; confirm exact submission route/date |
| Fabric access | Available, author-confirmed 14 October 2026 | D-011; verify workspace/capacity/permissions, expiry and deployment route in WP5.1 |
| Commissioner/permit route and reviewer arrangements | Pending where applicable | D-013 and data-management decisions |
| Author-only task walkthrough fallback | Selected by author on 14 October 2026 | Fixed rubric and initial/retest template in [the initial evaluation baseline](19-reference-fixtures.md); independent availability unknown |

The scope/method/task baseline is delivered; WP1.1 remains **in progress** until its academic completion conditions are recorded. Reference fixtures and a predeclared statistical split are in [the initial evaluation baseline](19-reference-fixtures.md). See [the execution tracker](12-execution-tracker.md).
