# Research and evaluation protocol

**Version:** 0.5, 14 October 2026. Implements Sections 6–7 of the [research plan](Li_Yu_Thesis_Research_Plan.docx). E1–E7 are planned experiments; none is reported as passed. The initial [reference/fallback/split baseline](19-reference-fixtures.md) and [26-case execution catalogue](evaluation/case-catalogue.csv) are delivered; freeze final accepted protocol/input versions at G5 before collecting final results. Preparatory source checks are recorded separately in [the source audit](11-source-audit.md).

## Research questions and method

- **RQ1:** To what extent does the designed pipeline meet predefined requirements for completeness accounting, traceability, idempotency and recovery when integrating Helen and FMI data?
- **RQ2:** To what extent do the dimensional and semantic models reproduce independently calculated measures and support predefined district-heating analysis tasks?

Follow Design Science Research: define the problem and objectives, design/build the artefact, demonstrate it, evaluate against requirements and communicate findings. Use formative checks during development and retain a separate final evaluation dataset/result set. Implementation completion is not itself an answer to the research questions.

The WP1 [scope/method record](13-scope-and-method.md) defines personas, initial task/rubric wording and evaluation units; [the literature review](14-literature-review.md) records the scholarly rationale. Use [the data-management plan](15-data-management-plan.md) for reviewer/storage/retention preparation and [source contracts](16-source-contracts.md) for the full weather feasibility evidence. These drafts and source checks do not pass the final experiments or freeze all G5 definitions.

## Evaluation setup

Current synthetic controls include 55 hand-entered M1–M5 answers over 11 scenarios, verified by direct Python arithmetic in `tools/check_wp1_fixtures.py`. They supply the required six-filter matrix plus targeted quality/DST/blank cases. This verifies reference controls only; no SQL/DAX reconciliation or E5 result is implied. Use versioned actual-output records separately during WP4/WP6.

Before final execution, record:

1. Local PostgreSQL reference environment, versions, hardware and Git commit; record Fabric demonstration settings separately.
2. Frozen source hashes, period boundaries, station, contract versions, unit/time rules and missingness policy.
3. Synthetic fixtures with known expected rows, defects and calculated answers, distinguished from publisher data.
4. Reference queries and independent calculations, test commands, thresholds and expected failure behaviour.
5. Reviewer tasks/rubric, consent/retention arrangements or the author-only fallback.

Use the local reference for the main E1–E7 results (D-010). Report cloud demonstrations separately under WP5. A future move of the principal evaluation to Fabric requires a versioned protocol defining equivalent publication, permission, reproduction and restore procedures before execution. A failed write through a read-only Lakehouse SQL endpoint alone does not establish least privilege; cloud access tests must cover the applicable workspace/Spark/data paths. A minimal fixed-file Pandas/SQL baseline may compare the same five measures and manual steps; if a fair baseline cannot be reproduced, make absolute claims only. Never describe it as an existing Helen workflow.

## Experiment definitions

### E1 Parsing coverage and lineage

**Maps to:** RQ1; FR-01–FR-04, FR-06; NFR-02–NFR-04.

- Run a normal week, winter week, spring/fall DST boundaries and a leap-day fixture.
- Inject malformed measurements, missing/duplicate hours, conflicting keys, unexpected columns and irregular intervals into separate synthetic cases.
- Compare accepted keys against an independently prepared expected set and calendar spine. Verify one-to-one joins and trace records back to source hash/row and run.
- **Pass:** every injected defect is detected or explicitly rejected; zero unexplained loss of valid keys or join multiplication; all curated records have provenance. Real source gaps remain reported gaps.
- **Evidence:** fixture manifest, expected/actual keys, rejection reasons, source/processing coverage breakdown and lineage examples.

### E2 Replay correction and backfill

**Maps to:** RQ1; FR-05, FR-08; NFR-01–NFR-04.

- Load a fixed batch twice with unchanged revision/configuration. Compare sorted business keys and values.
- Apply a synthetic corrected revision and an overlapping historical backfill; compare with a clean full rebuild of the same final source versions.
- **Pass:** identical rerun content, zero duplicate curated keys, only intended corrections, retained prior lineage and correct backfilled results. Execution timestamps/run IDs can differ.
- **Evidence:** before/after counts and content hashes, changed-key list, both revision references and clean-rebuild comparison.

### E3 Failure and recovery

**Maps to:** RQ1; FR-04, FR-08; NFR-04, NFR-09.

- Inject HTTP timeout/transient failure, a missing input, incompatible schema and an interruption before publication.
- Inspect the current Gold release while the candidate run fails, then remove the fault and rerun from the documented checkpoint.
- **Pass:** no partial Gold publication, bounded retries, actionable failure status, no incorrectly advanced checkpoint and recovered output equal to a clean run.
- **Evidence:** injected condition, logs, visible release before/after, run statuses, diagnosis/recovery duration and manual steps. Simulate network faults in controlled tests; do not disrupt public services.

### E4 Reproduction access and restore

**Maps to:** RQ1; FR-11, FR-12; NFR-06, NFR-07.

- From a clean checkout, build the documented environment, apply migrations, load a licensed or synthetic fixture and run the checks.
- Verify that a reporting account can read approved objects and cannot modify data. Restore a backup into a separate test database.
- **Pass:** documented commands reproduce expected outputs; denied-write checks work; restored keys, values and audit records match the saved snapshot.
- **Evidence:** setup transcript, versions, fixture hash, test results, role-check outcome and restore comparison. Record external reproduction separately from author reproduction.

### E5 Metric correctness

**Maps to:** RQ2; FR-06, FR-07, FR-14; NFR-02, NFR-10.

Compare **each of M1–M5 across at least six filter cases**, yielding at least 30 comparisons: full period, month, day, empty selection, missing-data period and DST boundary. Include tiny hand-calculated fixtures; match units, revision, timezone, grain and filters. M5 comparison includes each temperature band’s mean and sample count. A defined blank/invalid result is a testable outcome.

Counts, keys, band membership and blank/reason states must agree exactly. Proposed numeric tolerance:

```text
abs(DAX_value - SQL_value) <= max(0.001 measurement_unit, 0.000001 * abs(SQL_value))
```

For percentages, compare percentage points after converting both values to the same scale. Do not convert blanks to zero to force a pass. Predefine any justified measure-specific tolerance before final execution; investigate discrepancies before changing thresholds.

**Pass:** no unexplained mismatch. Retain independent SQL, DAX definitions, filter parameters, results and comparison output. SQL–DAX agreement alone is insufficient: hand-calculated fixtures address shared errors.

### E6 Analytical tasks and reviewer feedback

The author confirmed the author-only walkthrough fallback on 14 October 2026. Its initial/retest procedure and empty recording template are in [the reference baseline](19-reference-fixtures.md). All five final answers must be correct and traceable; initial failures remain recorded. This fallback does not establish independent-user usability. Independent reviewer availability remains unknown; apply the independent-study procedure below only if participation is arranged.

**Maps to:** RQ2; FR-14; NFR-05.

Invite 2–3 reviewers, aiming for analytical/domain and technical perspectives. Use the same five [AT-01–AT-05 tasks](01-requirements.md), wording, dataset and reference rubric. Record answer correctness, time, assistance and clarity comments. If comparing with a baseline, counterbalance order where feasible and discuss learning effects.

Target at least **4/5 tasks without assistance per reviewer**, and correct answers for all five after resolving issues. Keep original and retest scores separate. A small convenience sample supports formative findings, not population-wide usability claims.

If reviewers are unavailable, execute a scripted author walkthrough and label it accordingly; it cannot establish usability for independent users. Record the fallback decision rather than inventing participation or converting the missing study into a pass.

### E7 Analytical reproducibility and interpretation

**Maps to:** RQ2; FR-13, FR-14, FR-16; NFR-01, NFR-12.

Before WP4.3 exploratory modelling or feature selection, record chronological development/holdout dates, eligible-day rules and evaluation measures in versioned analytical configuration. Source-coverage inspection may cover the full period, but use development data for model choices and fit any learned scaling, imputation or feature selection there only. Preserve the holdout for the declared final comparison. An early look at holdout performance must be logged and prevents treating that same sample as untouched final evidence. G5 confirms this earlier split; it is not the first point at which the split is chosen.

- Regenerate notebook/model outputs, charts and the memo from the frozen Gold data and configuration.
- Check chronological holdout boundaries, calendar-only baseline, seasonal/calendar adjustment, residual autocorrelation and the chosen uncertainty method.
- [analysis-split-plan.json](../config/analysis-split-plan.json) predeclares 2024 development/2025 holdout before heat modelling, conditional on accepted paired alignment. Any replacement split must be declared before heat-model outcome exploration, with seasonal/exposure limits recorded.
- Run the declared weather-fill/station sensitivity check. Confirm that each of three memo findings has a reproducible query/chart and a limitation.
- D-022 preselects station 100968 in [the sensitivity plan](../config/station-sensitivity-plan.json). Audit its accepted-period coverage, apply identical aggregation/no-fill rules and compare on common eligible heat/weather days; report station-specific exclusions. Hold specification/split/uncertainty rules fixed and fit each sensitivity model on development data only. Four seasonal extraction checks are preparatory evidence, not an E7 pass.
- **Pass:** findings regenerate; sample sizes, missingness, uncertainty and confounding are disclosed; statements follow the evidence. Weak associations and null findings are valid outcomes.

## Performance sub-study

Within E4/WP6.1, measure full-load and incremental durations/throughput with **five measured repetitions** after any declared warm-up. Record hardware, cache state, capacity, input size and start/end boundaries; report median and range. Compare one indexing/query/materialisation change with the unoptimised version and verify unchanged results.

Reset the declared starting database state before every repetition. Full-load cases start from the same empty migrated database; incremental cases restore the same frozen baseline and apply the same nonempty delta. Record baseline/input hashes and the expected changed-key count, and verify the ending state each time. Measure unchanged replay separately so four replay runs cannot replace four incremental runs. State whether acquisition, migrations, restoration and validation are inside the timing boundary; keep that boundary and starting state identical across optimisation comparisons. Record warm-up/cache policy without assuming restoration clears caches.

Label any larger deterministic synthetic dataset. Small real data cannot establish production-scale throughput. Keep estimated cost assumptions separate from actual billed amounts. Predefine the scenario without claiming an improvement before it is measured.

## Optional forecasting experiment

Forecasting is outside E1–E7 and has no allocated core hours. If selected after G4, approve a separate bounded protocol: seasonal-naive versus one simple model, rolling-origin evaluation, MAE/RMSE by window and predictors available at issue time. Future observed temperatures are prohibited in a genuine next-day forecast; a historical-weather scenario must be labelled as such.

## Evidence records and storage

The [case catalogue](evaluation/case-catalogue.csv) assigns stable IDs, inputs/faults, actions, criteria and evidence to 26 planned cases: eight E1, four E2, four E3, three E4, one E5 matrix, one five-task E6 walkthrough, three E7 and two performance cases. Every entry is `not_run`. An entry can require several executions; E5-01 expands to at least 30 SQL/DAX comparisons and the manual controls, rather than counting one comparison. The initial 55-answer Python fixture check is preparatory evidence only.

Before each final execution, materialise exact fixture IDs/hashes and fault parameters, then retain a separate result record with the fields below. Preserve failures and link retests to the same case ID and changed release/protocol version. Hosted unit tests, existing ledger checks and file-copy restores do not substitute for these final system experiments. The catalogue adds detail within WP1.4's existing allocation and does not change the experiment definitions or pass thresholds.

Evidence locations to populate during development (source-helper tests already exist):

- `tests/fixtures/`: small safe inputs and expected results.
- `tests/`: executable unit/integration/data checks.
- `experiments/e1/` through `experiments/e7/`: manifests and selected publishable summaries.
- `experiments/performance/`: raw timings, configuration and summary.
- `powerbi/`: DAX/model definitions and metric comparison exports.

The current `.gitignore` ignores top-level experiment JSON/CSV files and `experiments/source-audit/`, not every nested result. Review file contents and ignore rules before collecting/publishing new evidence. Keep reviewer identities/consent records and unapproved data outside the public repository.

```text
Experiment ID and protocol version:
Execution timestamp and run/release ID:
Commit, environment and dependency/image versions:
Source hashes, period and station:
Contract/configuration/metric versions:
Fixture ID and injected fault:
Expected outcome and threshold:
Actual outcome, row counts, retries and duration:
SQL/DAX/filter details, if relevant:
Result: pass / fail / not run / not applicable
Evidence location and publication classification:
Deviation, explanation, owner and retest link:
```

Changing code or protocol after a final failure requires a new version and retest while preserving earlier evidence. At G6, map every conclusion back to requirements and results, including failed criteria and external-validity limits.

## Experiment ID migration

The revised plan supersedes the starter numbering: former E4 KPI reconciliation is now E5; former E5 task review is now E6. Former E6 forecasting becomes a separate stretch experiment. New E4 covers operations/reproduction and E7 covers analytical reproducibility. Do not mix historical IDs with the revised results folders.
