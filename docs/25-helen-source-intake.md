# WP2.2 Helen source intake and quarantine

**Delivered:** 16 October 2026. **Status:** source-faithful intake/replay complete. This implements WP2.2's parsing, immutable input, row lineage, quarantine and valid/invalid/DST controls. It supports FR-01–05/08/11 and NFR-01–04/06/12. Interpreted Helen facts and paired Gold publication remain conditional on their analytical contracts/model tasks. The 20-hour estimate is unchanged; actual author hours and competency review remain unrecorded.

## Commands

Run from the repository folder. Migrate/provision using the setup account, with `ENERGY_DB_ROLE` unset; then load with the loader role:

```powershell
.venv\Scripts\python.exe -m ingestion database migrate
.venv\Scripts\python.exe -m ingestion database roles
$previousRole = $env:ENERGY_DB_ROLE
try {
    $env:ENERGY_DB_ROLE = 'energy_loader'
    .venv\Scripts\python.exe -m ingestion helen load --manifest experiments/source-audit/helen-current-resource-acquisition.json
    # Run the same command again to verify replay.
}
finally {
    $env:ENERGY_DB_ROLE = $previousRole
}
```

The acquisition manifest and authorised raw CSV are local, ignored evidence; a fresh checkout needs a verified publisher acquisition before this command can load it. No new source request is made by the loader. PostgreSQL remains authoritative if writing the post-commit JSON summary fails.

## Contract and storage

[helen-ingestion.json](../config/helen-ingestion.json) accepts unconverted source values under the verified lexical/UTC/interval-end rules. [The author contract](../config/helen-source-contract.json), now v0.4, records the author's 16 October clarification **consumption**, alongside the previously confirmed MWh/DH and interval-end interpretation. This is author evidence; the publisher's power/production wording and precise supply/customer-meter boundary remain uncorroborated. No interval energy is calculated or published by intake, and current-edition raw redistribution remains unapproved.

The parser requires the exact two-column schema, UTF-8/BOM handling, semicolon separator, canonical `%d.%m.%Y %H:%M` labels and decimal-comma `Decimal` values. It processes at most 10 MB/250,000 records. Every CSV record retains its 1-based data-record index, ending physical line and original parsed field strings. Raw bytes remain in the content-hashed snapshot; quoting and line-ending syntax are recovered there.

| Input condition | Handling |
| --- | --- |
| Valid whole-hour UTC label and finite decimal-comma value | Retain unchanged value; canonical interval end is the label and start is one elapsed hour earlier |
| Bad timestamp/value, off-hour label or wrong field count | Retain the source record in quarantine with all applicable reasons |
| Duplicate parseable label, equal or conflicting values | Quarantine every member of the duplicate set; never choose the first silently |
| Negative finite value | Retain with `negative_source_value` warning; no unsupported physical correction or deletion |
| Unknown header, invalid CSV structure/encoding, oversized input | Stop the batch and retain a failed run; no partial links/data |
| Changed content snapshot | Preserve as a separate revision; intake does not select an active analytical revision |

Six migrations are now applied. [Migration 006](../sql/migrations/006_helen_source_intake.sql) creates:

| Object | Grain and purpose |
| --- | --- |
| `ops.helen_snapshot_load` | One loaded content snapshot; parser/contract/first-run identity and exhaustive valid/quarantine/negative counts |
| `silver.helen_source_record` | Snapshot × source-record index; original fields, optional parsed label/value, derived interval lineage, status/reasons/warnings |

The valid-row partial unique index prevents duplicate interval starts within one snapshot. CHECKs enforce source-row accounting, interval duration/end-label identity, finite numeric values and valid/quarantine consistency. All rows, header metadata, input/acquisition links and run completion commit in one transaction under the Helen intake lock. Failures roll them back and retain `HELEN_SOURCE_INGESTION_FAILED`.

Replay freshly inspects the manifest/raw checksum, parses the source and compares every stored record and count; an unchanged snapshot inserts zero records. Corrupt stored values cause visible failure. The loader has explicit SELECT/INSERT grants on these two new tables, with no UPDATE/DELETE/TRUNCATE. The reporter has no Helen source access; accepted analytical/reporting objects will be added deliberately in later tasks.

## Actual local results

- Source SHA-256: `f8363dbbfa09c8a00048de4836c4029a6f4d3482ee5e4b2f99da2b1e938cfee1`.
- Initial loader run: `68cb068e-09df-4dc0-954d-d51524fb25eb`: **91,767 source records**, all lexically valid; zero quarantine and negative warnings.
- Replay: `1807493c-ea9b-48e6-8e2d-12af022a39b4`: **zero inserted**, 91,767 records reverified; content/acquisition identities reused.
- Weather release `f327b833-7b99-453f-b376-d1f82a0fe7d9`, its content hash and original checkpoint timestamp remain unchanged. No Helen analytical release exists.
- Current ledger: 107 snapshots, 108 acquisitions, 15 successful runs, two retained earlier role-switch startup failures and 425 acquisition links. Weather retains 105,270 source-revision rows and 105,264 accepted publication keys.
- Current suite: **83 offline tests and 44 isolated database checks**. The five new database checks run intake through a real restricted login and verify quarantine accounting, zero-insertion replay, retained corrections, atomic bad-manifest failure and stored-corruption detection. Offline cases include both DST transitions in UTC, duplicate sets, strict decimals/schema/bounds and BOM/quoting.

Private reports: `experiments/source-audit/helen-runs/` and `helen-intake-verification.json`. These are development checks, not final E1–E7 execution or confirmation of physical quantity accuracy.

## Hosted CI completion evidence

WP2.5's hosted success/failure/recovery criterion is now verified for committed baseline **`9fb12dd751792c2634073cff4ec6351f2dee1959`**, which contains the 76-test/39-database-check suite:

| Run | Result |
| --- | --- |
| [Initial normal run](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38888272696) | Windows/Linux tests and PostgreSQL checks green |
| [Controlled failure](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38888672505) | Only the explicit corrupted-fixture demonstration step fails; ordinary jobs remain green |
| [Normal recovery](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38889103306) | Green on the same commit with probe disabled |

Private metadata: `hosted-ci-evidence.json`. Tokens are never written to that evidence. New local Helen changes have their own local verification and need a subsequent commit/push before hosted CI can certify them. This completes the existing executable-slice CI/scheduling/recovery task; future dbt/integrated release checks remain with their model tasks. No persistent OS scheduler, required branch rule or CD deployment was configured.

## WP1 clarifications recorded

On 16 October the author confirmed review of the selected literature and reiterated the end-of-year deadline. Initial WP1.2 author review is recorded as completed; final thesis synthesis/citation review remains ongoing. Credits, exact programme review/submission dates and the supervisor approval reference were not supplied and are not invented.

The author explicitly chose **no external backup**. The verified local `backup/` snapshots remain the selected approach; accepting their shared C: failure risk replaces the previous request for an independent destination. Independent storage is not claimed and is no longer a user-pending WP1 decision. Database restore testing remains a separate WP3.4/E4 requirement. Current-file licence, precise physical boundary/paired analytical acceptance and the later G5 freeze remain explicit conditions in [WP1 readiness](18-wp1-readiness.md).
