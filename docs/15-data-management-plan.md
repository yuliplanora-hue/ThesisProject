# WP1 data-management and publication plan

**Version:** 0.2, 14 October 2026. **Task:** WP1.4. **Owner:** Li Yu. **Status:** operational draft with verified local evidence copies; author-selected local-only storage, conditional reviewer arrangements, institutional retention decisions and final G5 freeze remain pending. This plan applies to the current public-source prototype and the proposed evaluation. No reviewer data has been collected by this development work.

## Data classes and handling

| Class | Current or planned material | Storage / publication rule |
| --- | --- | --- |
| Public environmental observations | FMI station temperature, original XML, query metadata and derived coverage | Locally under ignored `data/raw/` and `experiments/source-audit/`; any later release includes FMI attribution/licence and transformation description |
| Helen aggregated heating series | Existing CSV, source strings and checksum | Remains local/ignored while current-snapshot licence and semantics are unresolved; publish acquisition instructions and synthetic fixtures meanwhile |
| Research code/configuration | Parsers, SQL, tests, nonsecret contracts, dependency pins and docs | Git/GitHub; author chooses an explicit code/text licence before an open-licensed final release. Public GitHub access alone is not a licence grant |
| Selected reproducibility evidence | Safe fixtures, configuration hashes, aggregate quality counts, timings and failure/retest summaries | Review for credentials, restricted data and identity clues before publication; retain detailed lineage privately where necessary |
| Reviewer contact/consent and identity key | Only if independent reviewers participate in E6 | Institution-appropriate restricted storage outside the public repository; separate identity key from task responses |
| Reviewer responses/timings/comments | Planned pseudonymous task-attempt records | Collect the minimum needed; public report uses reviewed summaries with no identifying quotes or contact details |
| Credentials | Local database password and later cloud credentials | Ignored `.env` or an appropriate secret store; never include in command arguments, logs, screenshots, Git or source manifests |

The energy/weather prototype contains no individual-customer records. A source or scope change introducing customer or confidential employer material requires a new data-management assessment. Pseudonymous reviewer IDs do not make the underlying records anonymous while an identity key or recognisable comments remain.

## Acquisition and provenance

Preserve original source content, record content hash, exact public request parameters, retrieval time, source/contract version and parser/code identity. Record observation time separately from acquisition time. Raw source revisions are immutable; corrections produce new content identities. Never invent a retrieval date/URL for the existing Helen file from its modification time.

The source-audit report records the base Git commit, working-tree state and code/configuration hashes. Each FMI weekly chunk has its own acquisition manifest and original response hash. The initial full-period report is preserved before cached revalidation. This supports source-audit reproduction; it does not establish a complete Gold lineage or passed E1/E2.

Unknown schemas fail visibly and retain acquisition evidence. Missing/NaN observations remain explicit. The declared weather baseline uses six finite ten-minute samples per complete UTC hour, with no fill; source gaps/invalid values and processing defects are distinct concepts. Before final experiments, store fixture expected outcomes separately from actual results and preserve failed/retest evidence.

## Storage, access and backup

Current code/docs are versioned, and the initial baseline was pushed to [ThesisProject](https://github.com/yuliplanora-hue/ThesisProject). Raw observations and audit details currently reside on this workstation. At the author's request, local evidence was copied into the project's ignored `backup/` directory on 14 October 2026. **This is a verified local copy; no independent raw-data backup has been verified.** Both working files and this copy reside on C:. GitHub excludes these raw files and is not their backup.

The [backup helper](../tools/backup_evidence.py) copies `data/raw/`, `experiments/source-audit/`, nonsecret `config/` and the new `tests/fixtures/wp1/` reference inputs into a fresh UUID-named snapshot without overwriting existing backups. It hashes every input before copying, checks source/copy hashes afterwards, then restores representative CSV/XML/JSON files into the snapshot's separate `restore-check/` directory and verifies their hashes. A destination inside an input directory is rejected before writing. Secrets, virtual environments and the PostgreSQL volume are outside its scope. The earlier snapshot below preceded the fixture addition and therefore covered the original three input directories.

Executed snapshot: `backup/evidence-20261014T132028Z-7f21516ed3c442b9aff6b25cc951282b/manifest.json`; **282 files, 47,597,108 input bytes and three sample restores passed**. Copies reflect evidence available at that execution, not later documentation or acquisitions. The manifest retains per-file checksums and failures if a run stops. This exercise does not test restoration into the live working directory or a PostgreSQL database; those are separate recovery/E4 procedures.

After method-paper/reference-fixture additions, a new snapshot was verified at `backup/evidence-20261014T135819Z-2b9bb7c1757544d594e54ffdab66d15e/manifest.json`: **294 files, 50,958,675 input bytes and three sample restores passed**. It includes the synthetic controls and preserves the earlier snapshot. Same-drive independence remains unverified.

The WP1 snapshot after publisher/HRI acquisition and paired-label auditing is `backup/evidence-20261014T144440Z-cc053e1ad45c443eb798be5cfaf7e064/manifest.json`: **304 files, 56,734,842 input bytes and three sample restores passed**. It preserves both earlier snapshots and covers evidence available at that point.

The WP2.3 snapshot is `backup/evidence-20261014T180945Z-4eeb8620a305423a95e41fddebfd2d09/manifest.json`: **330 files, 56,816,841 input bytes and three sample restores passed**. It preserves earlier backups and covers the weather evidence available at that point.

The WP2.4 snapshot is `backup/evidence-20261014T184003Z-b7b6cd54ea0d4ede92a2ff60462b4bb2/manifest.json`: **361 files, 56,979,584 input bytes and three sample restores passed**. It includes the publication plan/run evidence and archived earlier source versions. Detailed manifests remain ignored. These are file copies on C:, not independent storage or PostgreSQL recovery; Silver/publication database state still needs the separately planned database backup/restore procedure.

```powershell
.venv\Scripts\python.exe tools/backup_evidence.py --destination backup
```

On 16 October 2026, the author explicitly chose **no external backup**. Continue verified local snapshots under the ignored project `backup/` folder; the author accepts their shared C: failure risk. An independent copy is not claimed and is no longer a WP1 decision awaiting an external path. This replaces the earlier request for institutional/external storage. No reviewer records are collected; any future recruitment must establish its own applicable storage/privacy arrangements first.

The WP2.5 snapshot, verified 15 October 2026, is `backup/evidence-20261015T175443Z-e0e7a102d8bd43b1986497684b5cfb5a/manifest.json`: **379 files, 57,073,526 input bytes and three sample restores passed**. It adds scheduled-run evidence and verified archived publication code; previous snapshots remain preserved. Storage is still on the same C: drive and is not a database backup.

The latest WP3.1 snapshot, verified 16 October 2026, is `backup/evidence-20261016T103215Z-822c4590049348e58e4bdca1a0944c06/manifest.json`: **415 files, 57,273,156 input bytes and three sample restores passed**. It retains current role/replay evidence, both unsuccessful startup records and exact prior code versions. Independent storage and database restore remain pending.

Helen/CI delivery snapshot: `backup/evidence-20261016T104701Z-2429dbad61c6492786469e8879c741e7/manifest.json`; **438 files, 57,394,141 input bytes and three sample restores passed**. Earlier snapshots are preserved.

WP3.2 model delivery snapshot: `backup/evidence-20261016T110931Z-4a65bcde0e02417ba189e596f37790df/manifest.json`; **1,316 files, 87,986,004 input bytes and three sample restores verified**. It preserves model manifests/catalogs/controls and archived source versions alongside raw evidence. Author-selected local-only storage remains unchanged; no database restore is implied.

WP3.3 time/reporting snapshot: `backup/evidence-20261016T112300Z-9ddf790c69ce4edeac64818d1ca16de2/manifest.json`; **3,112 files, 126,727,874 input bytes and three sample restores verified**. It includes the calendar/reporting model artifacts, Windows/Linux controls and checksum-verified prior/current source snapshots. This remains the author-selected same-drive evidence backup; the subsequent WP3.4 database restore is documented separately.

Proposed schedule: back up changed source snapshots/manifests after acquisition and before source cleanup; back up database state before migrations/final evaluation; verify restoration after the first backup and at the final release. Store backup location/access details privately if they identify accounts or devices. Weather reporting-role denial is verified under [WP3.1](24-database-permissions.md); separate-database restore is now verified under [WP3.4](28-database-operations.md), while final E4 remains future work. The foundation's migration checks are distinct from that actual backup/restore.

Latest WP3.4 evidence copy: `backup/evidence-20261016T113850Z-c269cd921acd454b9042506628a6b1f7/manifest.json`; **3,146 files, 127,318,832 input bytes and three sample restores verified**. This file snapshot includes operations manifests, exact helper code, raw query plans and post-run environment context; the compressed database archives are separately retained under ignored `backup/database-*` and `backup/linux-database-operations/`.

The current database now has actual checksum-verified logical backups and successful isolated restores on Windows/Linux: all 27 project table/view fingerprints, schema/audit records and accepted pointers/checkpoints match. Destination-only roles and candidate ownership are reconstructed and restricted reporter access is verified; source data and permissions remain unchanged. [The operations runbook](28-database-operations.md) records archive locations/hashes and retained failed/successful attempts. Dumps contain private Helen values; do not publish them. These same-drive archives do not add independent storage or prove fresh-cluster/PITR recovery/final E4.

## Proposed retention and disposal

These are project proposals, not institutional retention requirements. Confirm them with the supervisor/programme before collecting reviewer data and record any replacements under D-020/D-013.

| Material | Proposed retention basis | Decision still needed |
| --- | --- | --- |
| Public code, nonsecret contracts and selected evidence | Maintain the portfolio/research release with versioned provenance; retain a stable final archive | Final licence/archive location and citation/version identifier |
| Licensed public source snapshots and private detailed experiments | Proposed five years after thesis acceptance for reproducibility, where permissions/storage allow; do not publish restricted raw data | Acceptance date, applicable permissions, storage owner and final disposal date |
| Reviewer contact details and identity key | Keep only as long as consent/withdrawal, study administration and the agreed review process require | Exact purpose/basis, calendar deadline, owner and storage before recruitment |
| Pseudonymous reviewer records/consent evidence | Proposed until thesis approval and any specifically agreed verification/review period; follow applicable institutional guidance | Exact retention end dates and disposal procedure before collection |
| Temporary files and redundant source downloads | Remove only after preserved source identity and verified backup/reproduction path are established | Record retained versions and cleanup evidence; preserve failed final experiments |

The [student data-management guide](https://libguides.tuni.fi/open-science-for-students/data-management-and-data-protection) notes that personal thesis data is usually destroyed after completion/approval and that later use must be addressed. The [institution's policy](https://www.tuni.fi/en/data-protection-and-processing-personal-data/data-protection-policy) requires the research retention period to be specified in planning/privacy documentation. A five-year proposal for public observations is not a five-year rule for reviewer identities.

## Reviewer preparation and fallback

On 14 October 2026 the author selected the **author-only walkthrough as the fallback**. Its fixed rubric, empty recording template and initial/retest procedure are in [the initial evaluation baseline](19-reference-fixtures.md). This settles the fallback route; independent reviewer availability remains unknown and no reviewer responses/scores have been collected. The personal-data arrangements below apply if independent participation is later organised.

Before recruitment, settle controller/responsibilities, lawful processing basis, participant information/privacy notice, consent arrangements where applicable, storage/access, retention/disposal dates and any programme-specific permission/ethical-review requirements. Use current TAMK forms/guidance; the project's task rubric is not a substitute for those documents. [TAMK's student instructions](https://opiskelijanopas.tuni.fi/fi/tamk/opintojen-suorittaminen/opiskelun-etiikka-ja-saannot/tietosuojaohje-opinnaytetyon-tekijalle) explain controller responsibility and preparation of appropriate notices before collection.

Collect only task ID, pseudonymous reviewer ID, correctness, assistance, elapsed time and necessary clarity feedback. No audio/video recording or sensitive background questionnaire is planned. Preserve original and retest scores separately. If reviewers are unavailable, execute the scripted author walkthrough and clearly limit the usability claim. Do not invent independent participation.

No recruitment message or publisher clarification has been sent. Communication drafts remain for the author to use; sending messages requires an explicit instruction.

## Publication and assistance record

Check source licence/attribution, identifiable information, secrets, screenshots and claims before a final public release. Source/metric/contract versions should accompany each result. Explain gaps, invalid comparisons and failed criteria. Retain synthetic examples that reproduce the methods without redistributing unresolved Helen material.

Record AI assistance by date/task, affected artefacts, verification performed and author review. The author must understand and defend the work. Follow [TAMK's thesis instructions](https://opiskelijanopas.tuni.fi/en/tamk/studying-0/thesis/instructions-thesis) and [report guide](https://opiskelijanopas.tuni.fi/en/tamk/studying-0/tamks-report-guide) for the final disclosure, citation, publicity and reporting requirements. This draft neither certifies institutional approval nor replaces the official submission process.

## Completion checklist

- [x] Data classes, owner, current storage and publication boundary recorded.
- [x] Source hash/manifests and actual versus proposed results distinguished.
- [x] Reviewer-only records separated from public-source research evidence in the proposed handling plan.
- [x] Author-only walkthrough fallback selected and empty initial/retest recording template prepared.
- [x] Local evidence copy and representative restore verified; latest snapshot includes reference fixtures.
- [ ] Confirm retention calendar dates and applicable institutional requirements; independent-reviewer arrangements are conditional on later recruitment.
- [x] Author chose local-only backup and accepted shared-drive risk on 16 October; local hash/sample restores verified, no storage independence claimed.
- [ ] Confirm current-snapshot Helen licence and final code/text licence.
- [ ] Freeze the complete source/metric/fixture/protocol/input manifest at G5.

See [the source contracts](16-source-contracts.md), [evaluation protocol](03-evaluation-protocol.md) and [execution tracker](12-execution-tracker.md).
