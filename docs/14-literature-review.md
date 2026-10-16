# WP1 literature search, screening and design rationale

**Version:** 0.3, 14 October 2026. **Task:** WP1.2. **Status:** initial literature selection/rationale delivered; author verification and final thesis synthesis continue. The [matrix](literature/literature-matrix.csv) contains 20 DOI-verified candidates; [initial selection](literature/source-selection.csv) retains 15 core references and five reserves. Nine candidates have [targeted critical notes](17-critical-literature-notes.md), nine retain initial abstract/section screening and L12/L13 remain bibliography-only reserves. No author-completed full-paper review or completed systematic review is claimed.

## Review purpose and inclusion rules

The review supports five questions: how to evaluate a DSR artefact; what data quality means for its consumers; how to make computational results reproducible; how temporal dependence affects validation/uncertainty; and which heating/weather interpretations survive a change from customer/building to aggregated system data.

Include peer-reviewed method/domain research, foundational work, recent relevant updates and clearly identified author manuscripts. Require a traceable original paper/DOI, a contribution relevant to an RQ or substantive design decision, and a recorded access/review level. Keep publisher documentation, data catalogues and institutional guidance in a separate evidence category. Employer advertisements are career context, not scholarly evidence.

Exclude unrelated name matches, general tutorials used as research findings, inaccessible papers presented as fully read, duplicate journal/preprint versions counted twice, and studies used to justify claims beyond their measurement grain. A forecasting paper may remain for context while forecasting implementation stays outside the core.

## Executed search log

All searches below were performed on **14 October 2026** through web discovery, primary-source lookup and a bounded Crossref metadata update. These are purposive searches and citation follow-up, not an exhaustive systematic review. No web-search totals are invented. TAMK library/Scopus searches have not been performed under the author's account; the Crossref searches below are not a substitute for that broader follow-up.

| ID | Exact search or lookup | Channel | Retained candidates / outcome |
| --- | --- | --- | --- |
| S01 | `design science research Peffers 2007 methodology information systems research DOI` | Web discovery, publisher follow-up | L01; separate earlier arXiv process paper identified, not counted as a duplicate of L01 |
| S02 | `"FEDS" "Framework for Evaluation" Venable 2016` and `site.tandfonline.com "FEDS: a Framework"` | Web discovery, original publisher sections | L02; recent MEDS extension L19 found during follow-up |
| S03 | `"Data quality assessment" "Pipino" 2002` and `"Methodologies for data quality assessment and improvement" Batini 2009` | Author/publisher discovery and registered abstracts | L04/L05; L03 retained from the proposal and original-paper copy |
| S04 | Direct DOI lookups for Sandve, Wilson, Peng and Wickham | PLOS, JSS, author manuscript and Crossref | L06–L09 |
| S05 | `site.robjhyndman.com "A note on the validity of cross-validation"` | Author page/manuscript and DOI verification | L10 |
| S06 | `"Cross-validation strategies for data with temporal" Roberts 2017` and `"The Jackknife and the Bootstrap for General Stationary Observations"` | Paper discovery, registered abstract/bibliography | L11 screened; L12 queued for primary full-text reading |
| S07 | `district heating heat load temperature regression Gadd Werner daily heat load variations 2013` and `district heating forecasting review temperature demand 2021 2024 open access` | Publisher/author repositories and citation follow-up | L14–L18 |
| S08 | `"International review of district heating and cooling" Werner 2017 DOI` | Bibliography discovery and Crossref verification | L13 queued; no detailed review findings extracted |
| S09 | 19 exact DOI requests to `api.crossref.org/works/{DOI}` | Publisher-registered bibliographic metadata | All 19 records retrieved, including bounded retry of four failed requests; files under ignored `experiments/source-audit/literature/` |
| S10 | `district heating open data quality temperature` | Crossref relevance-ranked metadata query | First 15 hits title-screened; L20 added after primary-section reading; one possible same-title/version relationship flagged |
| S11 | `reproducible data pipelines analytical data quality` | Crossref relevance-ranked metadata query | First 15 hits title-screened; four titles queued for primary reading; two possible same-title/version relationships flagged |
| S12 | `temporal cross validation forecasting evaluation` | Crossref relevance-ranked metadata query | First 15 hits title-screened; two method-related titles queued; forecasting applications/reconciliation not prioritised for the core |

The recent-search [query specification](literature/search-queries.json), [retrieval manifest](literature/search-manifest.json) and [complete screening CSV](literature/search-screening.csv) preserve exact queries, filters, rank, DOI, decisions, timestamps and response hashes. [Crossref's API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) searches publisher-deposited scholarly metadata. These free-text queries do not have Boolean semantics. Each was limited to the first 15 relevance-ranked `journal-article` records dated 2020–14 October 2026. DOI/type metadata does not establish peer review, and rankings/metadata can change.

Accounting: 45 returned hits, 45 distinct case-folded DOIs; one new matrix candidate (L20), six primary-reading queues, three possible same-title/version flags and 35 titles not prioritised. Distinct DOIs are not necessarily independent studies. The first broad query retrieves many technology papers: this is a search-specificity limitation, not evidence of a research gap. Raw responses remain ignored; the public manifest records the API's point-in-time totals without presenting them as relevant-study counts. A first acquisition attempt stopped during Unicode title rendering; the completed retrieval is separately timestamped and hashed.

Primary-source summaries in the matrix are short paraphrases of the accessible abstract/selected sections. The file distinguishes a screened interpretation from an unread candidate. Bibliographic year follows the cited journal issue where available; an online/repository upload date is not automatically the publication year. L17 is cited as the 2021 journal issue and records its December 2020 online date. L18's author version and published paper are one source.

## Preliminary synthesis

The current evidence supports planning a chain from problem/objectives to demonstration and explicit evaluation ([Peffers et al., L01](https://doi.org/10.2753/MIS0742-1222240302)), with formative and summative evaluation distinguished by purpose ([Venable et al., L02](https://www.tandfonline.com/doi/full/10.1057/ejis.2014.36)). It does not make a functioning implementation sufficient evidence of a research contribution.

Quality needs to include the context and interpretation of the task ([Wang and Strong, L03](https://courses.washington.edu/geog482/resource/14_Beyond_Accuracy.pdf)). The project's expected-key accounting and reviewer tasks address different aspects of that concern. A source gap can be fully accounted for while still limiting an analytical comparison; a nominally complete table can still have ambiguous units.

Reproduction needs the input/code/version/parameter chain ([Sandve et al., L06](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003285)). Modular scripts, raw-data preservation and an organised project provide a practical route for a small study ([Wilson et al., L07](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005510)). Re-executing the same data/code is distinct from replication on independently collected data, and neither automatically establishes scientific validity ([Peng, L08](https://pmc.ncbi.nlm.nih.gov/articles/PMC3383002/)).

Validation must match the intended inference and dependence structure. [Bergmeir et al., L10](https://robjhyndman.com/papers/cv-wp.pdf) discuss conditional validity of ordinary cross-validation for particular autoregressive models; this cannot simply be transferred to the proposed seasonal temperature/calendar model. [Roberts et al., L11](https://doi.org/10.1111/ecog.02881) also caution that blocking can create extrapolation. Record both the temporal split and the seasons it covers, then justify uncertainty assumptions after residual diagnostics.

Domain papers also reveal a grain/boundary problem. Substation patterns in [Gadd and Werner, L14](https://www.sciencedirect.com/science/article/pii/S0306261913001803) do not establish customer behaviour in a single whole-city aggregate. [Triebs and Tsatsaronis, L16](https://doi.org/10.1016/j.apenergy.2022.118571) distinguish customer demand from plant supply. Keep Helen's production-need wording visible until the dataset boundary is confirmed.

An existing [open-data district-heating tool, ODHeatMap (L20)](https://journals.aau.dk/index.php/sepm/article/view/8812), is relevant prior work at a spatial modelling grain. Its presence sharpens the proposed contribution: evaluate the particular Helen/FMI temporal reliability, metric correctness and analytical tasks. The [critical comparison](17-critical-literature-notes.md) records a bounded applied contribution and case-specific evidence gap. A field-wide absence or first-tool novelty claim is not established.

## Literature-to-design rationale

These applications are project decisions inferred from literature and requirements; the cited papers do not prescribe a specific vendor stack or publication mechanism.

| Rationale | Evidence basis | Project decision / alternative considered | Validation link |
| --- | --- | --- | --- |
| RAT-01 Preserve auditable inputs | L06/L07; traceability requirements | Immutable source snapshots and manifests; editing raw spreadsheets would lose the reproducible transformation chain | D-014; E1/E2/E4 |
| RAT-02 Make quality meaningful to the task | L03/L04; consumer/context quality | Expected calendar independent of surviving facts; report invalid values/source gaps separately instead of treating every joined row as completeness evidence | NFR-03; M4; E1/E6 |
| RAT-03 Separate reproducibility from correctness | L08; RQ2 correctness requirement | Independent SQL/DAX plus hand-calculated fixtures; agreement alone can reproduce a shared mistake | E5/E7 |
| RAT-04 Preserve temporally defensible evaluation | L10/L11; seasonal source structure | Declare holdout before modelling and fit learned preprocessing on development data; random splitting is not adopted without evidence for its assumptions | WP4.3; E7 |
| RAT-05 Keep measurement grain explicit | L09/L14/L15/L16/L18 | Separate heating-system and station observations, state sampled-temperature aggregation, avoid customer/consumption claims from a production aggregate | D-006/D-007; FR-06; E1/E7 |
| RAT-06 Use staged evaluation within capacity | L01/L02; 560-hour envelope | Early fixture/source checks and a frozen local final evaluation, with a separately bounded cloud slice | D-010; WP1.4/WP5/WP6 |

## Initial reference selection

The 15 core references cover DSR/evaluation (L01/L02), consumer/metric quality (L03/L04), reproducibility and data structure (L06–L10), structured validation (L11), heating grain/system boundary (L14–L16/L18) and a relevant existing open-data tool (L20). The selection CSV records a reason for every retained/reserve candidate. The five reserves are L05/L12/L13/L17/L19; they are not silently counted as critically read core papers. This meets the plan's initial 15–20 reference target and six design-rationale links, while retaining exact reading levels and remaining thesis-review work. Author verification, broader library/citation follow-up and final bibliographic/synthesis review continue before academic submission.

## Remaining reading and synthesis

1. The author confirms selected-literature review completed on 16 October. Use the nine notes and 15 core references in the report synthesis and verify final quotations/citations against the primary copies. Follow up uncertain assumptions or reserve L12/L13 only if the thesis needs them; reserve reading is not part of the confirmation.
2. Perform broader TAMK library/Scopus searches with explicit topic/Boolean queries, or document an alternative route if unavailable. Follow up the six queued metadata-search titles and verify version relationships; export candidates and record inclusions/exclusions. These account-based searches have not occurred.
3. Add recent reproducibility/analytics-evaluation studies if they change the design rationale; retain a justified final set around the proposed 15–20 scholarly-source target.
4. Write the critical comparison that establishes the specific research gap and justified design contribution; review it with the supervisor. A citation count is not completion evidence.

The initial WP1.2 selection/rationale deliverable is available: 20-candidate matrix, 15-reference core selection, 45-hit screening export, nine targeted critical notes, bounded contribution comparison and six rationale links. The initial selected-literature author review is now **author-confirmed complete**; final report synthesis/citation review continues. See [the scope record](13-scope-and-method.md) and [the execution tracker](12-execution-tracker.md).

## Author review update, 16 October 2026

The author reports reviewing the selected literature. Record the initial 15-core-reference author-review step as completed, while preserving the actual passage/access levels of the assisted notes and five reserve candidates. No new per-paper reading depth, hours or agent full-text access is inferred. Final thesis synthesis, citation accuracy and supervisor/report revisions continue; this confirmation does not complete later academic submission tasks.
