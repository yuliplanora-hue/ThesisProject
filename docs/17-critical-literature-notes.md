# WP1 critical reading and contribution comparison

**Version:** 0.2, 14 October 2026. **Task:** WP1.2. Nine targeted critical notes extend the initial screening. These are Codex-assisted readings of identified primary/author-copy passages; author-completed full-paper review is not claimed. The [matrix](literature/literature-matrix.csv) retains access/review levels; [initial source selection](literature/source-selection.csv) selects 15 core references from 20 candidates. Source PDFs and retrieval/hash manifests remain locally under ignored `experiments/source-audit/critical-reading/`; PDFs are not redistributed in Git.

## L01: distinguish construction, demonstration and evaluation

Source: [Peffers et al., author-hosted JMIS paper](https://scholar.cgu.edu/samir-chatterjee/wp-content/uploads/sites/6/2013/07/jmis-article.pdf), DOI `10.2753/MIS0742-1222240302`. **Read:** selected activity definitions and methodology evaluation/discussion; printed pp. 55–56 and 70–71.

DSRM supplies six activities and permits different entry points and iteration. Its four demonstration cases support a process framework; they are not a controlled comparison proving that every DSR artefact is effective. Construction, demonstration and assessment against objectives are separate obligations. For this thesis, map requirements to experiments and observed results; treat a working prototype as demonstration until its correctness/recovery/task criteria are measured. A framework's applicability does not establish the proposed artefact's novelty or programme-level contribution.

## L02: evaluation purpose and setting

Source: [Venable et al., coauthor-institution copy](https://rucforsk.ruc.dk/ws/files/58874543/art_10.1057_ejis.2014.36.pdf), DOI `10.1057/ejis.2014.36`. **Read:** framework dimensions and application/discussion/limits; PDF pp. 5–6 and 12–13, including the repository cover.

FEDS separates formative/summative purpose from artificial/naturalistic setting and supports selecting evaluation episodes. Evidence includes interpretation of two prior studies and a case applying the framework; the paper acknowledges limited evaluation breadth. Frequent fixture checks can improve the design before frozen summative execution. An author walkthrough remains controlled verification. Even real reviewers answering constructed tasks do not establish effectiveness in a deployed utility organisation. Declare what each episode establishes and retain the local reference's external-validity limits.

## L03: quality dimensions arise from consumers and tasks

Source: [Wang and Strong (1996), original-paper copy](https://courses.washington.edu/geog482/resource/14_Beyond_Accuracy.pdf), DOI `10.1080/07421222.1996.11518099`. **Read:** selected two-stage survey/method, factor interpretation and conclusion passages; printed pp. 10, 12–13 and 21–22.

Survey and grouping work support intrinsic, contextual, representational and accessibility dimensions; the importance-rating stage includes 355 consumers. Attribute interpretation, sampling through a US university and factor stability constrain transfer. This is evidence for considering consumer context, not a universal numeric completeness threshold or a study of Finnish heating analysts. Use explicit task/rubric definitions, visible quality denominators and verified units. A clean table or 100% key count cannot settle fitness for a particular analytical claim.

## L06: reproducibility as an evidence chain

Source: [Sandve et al. (2013)](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003285). **Read:** introduction and Rules 1–10 in publisher HTML.

The paper gives practice guidance rather than a controlled evaluation of a particular stack. Inputs, software versions, parameters, intermediate results and claim-to-result links make computational work inspectable. Its prescriptions do not supply project-specific coverage thresholds or prove scientific correctness. For this thesis, manifests and pinned environments support E4/E7; independent expected answers remain necessary for E5. Public reproducibility also needs a lawful acquisition/fixture route when raw inputs cannot be redistributed. Reading supports the design rationale, not a passed reproduction experiment.

## L07: practical methods for a small research project

Source: [Wilson et al. (2017)](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005510). **Read:** introduction, Box 1, Data management, Software, Collaboration, Project organization and Keeping track of changes.

Recommendations target small research teams and adoption in everyday work. Raw-data preservation, explicit dependencies, simple examples, modular code and backups fit this study's capacity. These are practice recommendations, not comparative evidence that a particular CI workflow prevents research errors. A Git repository cannot back up files it excludes. Use fixture CI for frequent checks and verify source backups separately. Assess source licences and reviewer storage independently of software organisation. Production availability, role separation and release recovery need their own implementation and experiments.

## L09: preserve observational units while tidying

Source: [Wickham (2014), author copy](https://vita.had.co.nz/papers/tidy-data.pdf), journal DOI `10.18637/jss.v059.i10`. **Read:** observational units, missingness and Section 2.3, plus selected discussion text; author-copy pp. 4 and 20.

Tidy form organises variables, observations and observational units consistently. Distinguishing missing observations from structural absence matters before reshaping. The paper provides a data-structure framework and examples rather than proof of source accuracy or metric correctness. Keep heating system-hours and weather station-samples/hours distinct, with explicit keys and units. Reshaping must preserve expected-but-missing records and avoid multiplying heat rows in a one-to-many weather join. A tidy header cannot resolve the publisher's time/interval semantics.

## L10: conditional validity of time-series cross-validation

Source: [Bergmeir, Hyndman and Koo (2018), author manuscript](https://robjhyndman.com/papers/cv-wp.pdf). **Read:** model/assumptions in Sections 2–3, experimental setup in Section 4.1, real-data example and conclusions in Sections 6–7; manuscript pp. 2–7 and 12–14. The appendix proof has not been independently verified.

The argument concerns autoregressive models under specified stationarity, estimator and error assumptions; simulations and a sunspot example supplement it. Passing a residual test alone does not establish every theorem condition. The thesis's temperature/calendar association model is not automatically covered. Keep the chronological holdout, document season coverage and assess residual dependence on development data before choosing uncertainty methods. Neither the paper nor a successful holdout turns an observational coefficient into a causal heating effect.

## L18: customer-level pattern discovery and its exclusions

Source: [Calikus et al. (2019), author-repository paper](https://arxiv.org/pdf/1901.04863), journal DOI `10.1016/j.apenergy.2019.113409`. **Read:** Sections 3.1–3.6, 4 and 5.1–5.2, with selected passages from 5.3 and 6; printed pp. 4–6 and 12.

The study starts with 2,239 buildings in two Swedish networks for 2016; preprocessing leaves 1,385, with 1,222 assigned to 15 clusters. Methods include interpolation, normalisation, k-shape clustering and expert inspection. Exclusion and preprocessing affect the represented population; unusual profiles are not necessarily verified faults. This thesis has one aggregate heating series, not those building inputs. Retain calendar/grain awareness, but do not import its interpolation, thresholds or customer-control claims into the no-fill baseline. Any claimed operational saving would need additional evidence.

## L20: an existing open-data heating tool

Source: [Moreno et al. (2024), ODHeatMap](https://journals.aau.dk/index.php/sepm/article/view/8812), with the [author-institution PDF](https://vbn.aau.dk/ws/portalfiles/portal/762273555/IJSEPM8812.pdf). **Read:** architecture Section 2.2, validation Section 4 and discussion Section 6; printed pp. 52–54 and 58–60. The repository PDF adds a cover page.

The Python/GIS workflow estimates spatial heat demand and heating potential, demonstrated in Ulaanbaatar. Validation matches 9,158 of 13,010 reference buildings and compares system/grid outputs. Assumed building characteristics and reference coverage limit inference; aggregate agreement can conceal local differences. Its existence rules out positioning this thesis as the first open-data heating tool. The proposed Helen/FMI work instead evaluates temporal accounting, provenance/recovery and governed measures. It is not a like-for-like performance comparator for a spatial demand model.

## Comparison and bounded contribution

The following is a project interpretation of the reviewed material. Different questions, input grains and evaluation units explain the proposed choices; they do not establish that no other paper addresses them.

| Evidence strand | What it supplies | What this thesis must evaluate directly |
| --- | --- | --- |
| L06/L07 reproducible research practice | Practical evidence preservation and workflow organisation | Rebuild from a clean environment; retain exact inputs; verify recovery and access with executed checks |
| L03/L04 consumer-oriented data quality | Reasons to consider meaning, representation and intended use | Confirm Helen semantics; independently count expected keys and distinguish source missingness from processing defects |
| L10/L11 structured-data validation | Conditions and cautions about dependent observations | Declare development/holdout boundaries; assess calendar coverage, diagnostics and uncertainty assumptions |
| L14/L18 customer/substation analysis | Domain methods at a finer measurement grain | Limit claims to one aggregate system; document what cannot be inferred about customers or controls |
| L20 spatial open-data heating workflow | Relevant prior tool development and contextual validation | Evaluate the different temporal pipeline/metric/task requirements in RQ1/RQ2 |

**Working contribution statement:** design and evaluate a local, reproducible Helen/FMI analytical platform with explicit source contracts, expected-calendar accounting, traceable inputs, replay/recovery tests and independent validation of five measures and five analysis tasks. Report which requirements pass or fail and explain the design lessons and limits. The vendor combination and portfolio skills are not the research contribution by themselves.

The **case-specific evidence gap** is the still-unverified chain from these particular published source values to reliable, interpretable system-level measures in the proposed artefact. This justifies an applied evaluation question; it is not a field-wide absence or novelty claim. Final positioning still requires the method/domain reading queue, broader library/citation follow-up and supervisor review.

## Review actions

1. The author checks the nine notes against their stated source passages, records corrections and prepares an explanation of the associated design choice.
2. Prioritise remaining method/evaluation reading of the 15 selected references, including L11/L14/L16, and inspect unverified assumptions/remaining sections in these notes. L12/L13 are reserved reading candidates; obtain them lawfully if their methods/background are needed.
3. Use [the 45-hit search-screening record](literature/search-screening.csv) to follow up six queued titles and verify three possible version relationships. DOI registration and a `journal-article` metadata type do not certify peer review.
4. Select the final justified source set and complete the critical comparison before marking WP1.2 done. Preserve excluded/version records; do not add every discovered candidate to the final bibliography.

## Author review update, 16 October 2026

The author reports reviewing the selected literature. Record the initial 15-core-reference author-review step as completed, while preserving the actual passage/access levels of the assisted notes and five reserve candidates. No new per-paper reading depth, hours or agent full-text access is inferred. Final thesis synthesis, citation accuracy and supervisor/report revisions continue; this confirmation does not complete later academic submission tasks.
