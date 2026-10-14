# Competency development and portfolio evidence

This tracker operationalises Appendices A1–A2 of the [research plan](Li_Yu_Thesis_Research_Plan.docx). It supports a balanced Finnish data analyst/data engineer career goal while keeping the research contribution central.

The author reports strong SQL, Python and Power BI skills. That self-assessment guides the level of work; it is not an independently verified project score. All evidence below is **planned** until an artefact and successful explanation/check are linked. No skill is marked complete by this documentation update.

The first source-audit helpers and synthetic checks now exist; see [the execution tracker](12-execution-tracker.md). They provide partial artefact evidence for SK-03/SK-09/SK-12. The author still needs to reproduce and explain the work, and the full competency completion criteria below remain unmet.

## Assessment and reviews

| Level | Evidence required |
| --- | --- |
| 0 | No demonstrated project evidence yet |
| 1 | Can explain the concept or complete the task with guidance |
| 2 | Independently implements and reproduces the task and explains its design |
| 3 | Tests failure/edge cases, diagnoses issues and critically evaluates the result |

Target level 2 for every core skill, and level 3 for reliability, metric correctness and one analytical method. Assess actual baseline at G1, progress at G4 and final evidence at G7. Keep conditional cloud results separate. If a component is not executed, describe it as a design or learning gap.

## Analyst and shared competencies

| ID | Competency | Development tasks | Evidence and completion check | Target |
| --- | --- | --- | --- | --- |
| SK-01 | Business framing and requirements | WP1.1, WP4.5 | AT-01–AT-05 map to data/metrics/tests; explain one rejected requirement and reviewer-driven change if available | 2 |
| SK-02 | Advanced analytical SQL | WP3.2–WP3.4, WP4.1 | CTE/window/calendar queries, missing-key checks and a measured optimisation with identical results | 2 |
| SK-03 | Python and reproducible analysis | WP2.1–WP2.3, WP4.3 | Explicit parsers and reusable analysis; clean execution regenerates outputs with input/config/version records | 2 |
| SK-04 | Statistics and critical interpretation | WP4.3, WP6.2 | Calendar-only baseline, adjusted association model, holdout, diagnostics, uncertainty and sensitivity; E7 passes | 3 |
| SK-05 | Power BI DAX and Power Query | WP4.1–WP4.2, WP6.2 | Five metrics pass E5 including empty/missing/DST cases; three pages and filter/join diagnosis demonstrated | 3 |
| SK-06 | Excel and independent checking | WP4.4 | Refreshable audit workbook reconciles one monthly total and one quality count without manual source edits | 2 |
| SK-07 | Visual communication and decisions | WP4.2, WP4.4–WP4.5, WP6.3, WP7.3 | Three supported memo findings, limitations, task rubric, accessible report and nontechnical demo | 2 |
| SK-08 | Metric governance and domain reasoning | WP1.3, WP3.3, WP4.1 | Defend grain, MW/MWh, time/DST, completeness denominator and lineage; explain what sources cannot answer | 2 |

## Engineering and cloud competencies

| ID | Competency | Development tasks | Evidence and completion check | Target |
| --- | --- | --- | --- | --- |
| SK-09 | API and batch ingestion | WP2.2–WP2.3 | Two adapters, bounded queries/retries and provenance; malformed/timeout/schema fixtures behave as declared | 2 |
| SK-10 | Relational design and SQL/dbt | WP3.1–WP3.3 | Fresh migrations, model graph/docs, keys and relationship tests; explain grain/revision decisions | 2 |
| SK-11 | Incremental processing and recovery | WP2.4–WP2.5, WP6.1 | E2/E3 replay, corrections, backfill and interrupted-run recovery without partial publication | 3 |
| SK-12 | Software quality and DataOps | WP2.1, WP2.5, WP3.2, WP7.4 | Modular code, meaningful tests, dependency pinning and CI; deliberately bad fixture fails; self/peer review labelled | 2 |
| SK-13 | Operations security and performance | WP3.1, WP3.4, WP6.1 | Read-only denial, separate-database restore, runbook and measured optimisation with environment details | 2 |
| SK-14 | Cloud orchestration and Delta/PySpark | WP5.1–WP5.3 | Actual Fabric deployment, typed transformation, replay/recovery and matching frozen-sample output | 2, conditional |
| SK-15 | Cloud governance and cost | WP5.1, WP5.3–WP5.4 | Executed access test, capacity/refresh observation, cost assumptions and export/teardown plan | 2, conditional |
| SK-16 | Architecture and technical handover | WP1.2, WP7.3–WP7.4 | At least three substantive decisions, model/architecture diagrams and reproducible technical handover | 2 |

## Evidence record

Create one entry per competency and link actual artefacts rather than copying tool names into a CV:

```text
Competency ID:
Baseline level, date and evidence:
Task IDs and actual hours (already counted within work packages):
Artefact path and commit/release:
Experiment or demonstration result:
Independent explanation / failure diagnosis demonstrated:
Reviewer or self-review and date:
Current level and remaining limitation:
Next action:
```

A review should ask the author to reproduce a result, explain a design choice and diagnose a related failure without following a tutorial. Record guided work honestly. An unavailable cloud environment leaves SK-14/SK-15 incomplete even if the local core is excellent.

## Portfolio releases

| Narrative | Evidence to present | Claims to avoid |
| --- | --- | --- |
| Data analyst | Decision question, SQL/statistical reasoning, model/measure correctness, Power BI pages, three findings and a concise memo | Causal/financial effects unsupported by the source data; unperformed user studies |
| Data engineer | Contracts, ingestion, revision/backfill, SQL/dbt, CI, run logs, failure recovery and deployment trade-offs | Production scale, team leadership or employment by a publisher inferred from solo project work |
| Related analytics engineer | Tested SQL models, lineage, governed measures, documentation and business interpretation | Claiming every tool mentioned in a job description from one implementation |

Maintain one coherent repository and two case studies, not two separate platforms. Use measured results only after evaluation. Explain the small-data/local/cloud trade-off as part of technical judgment.

## Finland career context and follow-up

The research plan’s Appendix B contains the dated employer-source sample and its limits. Use actual vacancy requirements to choose application level, language preparation and later learning. Prepare an English case study; a short reviewed Finnish summary and domain vocabulary can support language practice if useful, but do not claim fluency from that exercise.

Additional clouds, orchestration products, full infrastructure-as-code, real product A/B testing and production team responsibility remain separate follow-up goals. Certification preparation and unrelated interview/language courses are outside the 560-hour thesis budget. Choose one later gap based on target roles instead of expanding the core thesis indefinitely.
