# Design decisions and supervisor questions

**Version:** 0.3, 14 October 2026. The [research plan](Li_Yu_Thesis_Research_Plan.docx) is the academic proposal; [the development roadmap](07-development-plan.md) turns it into work. A development baseline is not supervisor approval.

## Decision statuses

- **Baseline:** selected for project planning from the revised thesis plan; can be revisited with recorded reasons.
- **Pending evidence:** requires source, access or evaluation evidence before implementation can depend on it.
- **Pending academic agreement:** requires the relevant supervisor/programme decision.
- **Implemented locally:** verified setup work only, with evidence and date.

## Decision register

| ID | Decision | Status | Rationale and next action |
| --- | --- | --- | --- |
| D-001 | Retain district heating; replace CAD/hydraulic implementation with data engineering and analytics | Topic approved, author-confirmed 14 October 2026 | Author confirmed supervisor approval of the revised topic; supervisor/date/reference details and official milestones still to record |
| D-002 | Require RQ1/RQ2; keep forecasting as stretch without a required third RQ | RQs approved, author-confirmed 14 October 2026 | Author confirmed approval in response to the combined topic/RQ question. Preserve the two-question scope and 560-hour capacity; academic workload/dates remain separate decisions |
| D-003 | Core sources are Helen and FMI; at most one stretch extension after G4 | Baseline | One system and two publishers form a coherent demonstrator |
| D-004 | Use a local reference implementation and a bounded conditional Fabric demonstration | Baseline | Supersedes the earlier Fabric-first assumption; preserve local research execution |
| D-005 | Publish source data only where actual licence/permission allows; otherwise use synthetic fixtures | Baseline; licences pending | Record attribution and redistribution evidence per source |
| D-006 | Confirm Helen quantity, unit, timestamp convention and interval semantics | Parsing verified; semantics pending | Explicit audit parses all 91,767 rows with no duplicate/gapped written-clock hours. Publisher/city catalogue describes MW, while the local header says MWh; no conversion accepted. See the source audit |
| D-007 | Select FMI station, aggregation and common period | Representative access verified; final contract pending | Candidate Kaisaniemi 100971; nine sample/repeat checks pass. `t2m` metadata specifies one-minute average degC, sampled at requested times. Propose 2024–2025; full-period coverage and station/aggregation acceptance remain open |
| D-008 | Use SQL/dbt Core with PostgreSQL for the local model | Baseline; implementation pending | One tested transformation graph and documented star schema |
| D-009 | Freeze M1–M5 and six filter cases per measure | Pending evidence | Detailed candidate rules in the metric catalogue need source audit and tiny fixtures |
| D-010 | Use the local reference for principal E1–E7 measurements | Baseline decision, 14 October 2026 | Matches PostgreSQL publication, migrations, role and restore procedures. Freeze exact configuration at G5; Fabric remains a separate WP5 demonstration. A change requires equivalent versioned procedures |
| D-011 | Obtain Fabric capacity and sharing access close to the bounded demonstration | Pending evidence | Confirm route at G1; no paid resource assumed; if unavailable, mark cloud skill incomplete |
| D-012 | Use 20 hours/week and 560 hours including 60 contingency | Baseline; academic workload agreement pending | User confirmed weekly capacity and strong SQL/Python/Power BI skills |
| D-013 | Use five analytical tasks and aim for 2–3 reviewers | Baseline; reviewer arrangements pending | Agree consent/retention and recruit early; author walkthrough if unavailable |
| D-014 | Preserve a single accepted Gold release while candidate transformations are tested | Baseline design; implementation pending | A failed run must not expose partially updated reports |
| D-015 | Separate loader and reporting accounts; test backup/restore | Baseline design; implementation pending | Existing `energy` superuser is only a setup account |
| D-016 | Build reproducible evidence for 16 competencies; label conditional cloud outcomes separately | Baseline | Review at G1/G4/G7 using the competency evidence log |
| D-017 | Schedule 28 active weeks with two proposed year-end break weeks | Scheduling assumption | November–May dates are a working calendar, not institutional commitments |
| D-018 | Apply the four documentation-review clarifications before affected implementation | Recorded, 14 October 2026 | Protect holdout before WP4.3, reset benchmark state per repetition, declare local main evaluation, and reconcile M5 unclassifiable/excluded days. Scope and 560-hour budget unchanged; tests/models remain to implement |

## Verified preparation

| Evidence | Date | Limit |
| --- | --- | --- |
| Python environment and Pandas dependency check | 14 October 2026 | Dependency reproducibility/CI still needs implementation |
| PostgreSQL Compose startup, health and SQL checks | 14 October 2026 | Does not establish current uptime, role separation or pipeline readiness |
| Helen generic audit: 91,767 rows | 14 October 2026 | Physical/time semantics and business-key completeness remain open |
| Revised research plan and documentation alignment | 14 October 2026 | Development and academic gates are not passed by drafting documents |
| Explicit Helen audit, nine FMI checks and synthetic source tests | 14 October 2026 | Preparatory evidence only; no Gold release or completed E1–E7. Details and commands in the source audit and execution tracker |
| Operational metadata migration and database-client checks | 14 October 2026 | Six isolated-database checks passed, including migration checksum rejection; `001_operational_ledger.sql` applied locally. Loader/reporting roles, analytical ingestion and final E4 still pending |

## Questions to resolve with the supervisor

1. How should the earlier thesis topic be formally revised in Wihi, and who supervises the new scope?
2. Are the two research questions, Design Science Research approach and planned evaluations sufficient for this master’s programme?
3. Does the available 560-hour project budget meet the expected academic workload, or should the schedule extend?
4. Which commissioner, contract, research-permission and data-management arrangements apply?
5. Which official submission, seminar/presentation and review dates should replace the working calendar?
6. Is institutional Microsoft Fabric/Power BI capacity available, with suitable deployment and sharing permissions?
7. Are the proposed reviewer tasks and fallback suitable, and what consent/retention procedure applies?
8. What final-report template, AI-use disclosure, publication and portfolio-sharing conditions apply?

## Change control

Li Yu owns technical and scheduling decisions; the supervisor owns academic approval within the programme process. A reviewer provides feedback but does not automatically approve the thesis or source licence.

For each change, identify affected FR/NFR, M, E, WP/task and competency IDs. Update the research plan when academic scope changes; update related Markdown definitions and estimates together. Source/metric changes after G5 need a versioned protocol and rerun of affected experiments. Log reserve consumption and any removed stretch work.

```text
Decision ID and date:
Owner and people consulted:
Problem and alternatives:
Evidence links:
Decision and status:
Affected requirements, metrics, experiments and tasks:
Hours added/removed; contingency remaining:
Consequences and unresolved conditions:
Academic approval reference, if required:
Review date and superseded decision:
```
