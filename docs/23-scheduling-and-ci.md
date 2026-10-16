# WP2.5 bounded scheduling and CI operations

**Initial local delivery:** 15 October 2026; **hosted status updated:** 16 October 2026. **Status:** executable-slice scheduling/recovery and the original controlled green/red/green criterion are verified. The expanded Helen/dbt/calendar workflow is also published and green on c25c87f; the earlier dated evidence below is retained. This work supports FR-11, NFR-01/04/09/12, E2/E3/E4 preparation and SK-12. Actual author hours and competency review remain unrecorded; the task estimate stays 15 hours. Final E1–E7 execution remains separate.

## Run the accepted weather plan

From the repository folder, with PostgreSQL healthy:

```powershell
docker compose up -d --wait
.venv\Scripts\python.exe -m ingestion schedule --runs 2 --interval-seconds 1 --timeout-seconds 300 --max-seconds 900
```

The Windows wrapper resolves the repository and its interpreter from its own location, so it also works when invoked from another directory:

```powershell
powershell.exe -NoProfile -File tools/run_weather_schedule.ps1 -Runs 2 -IntervalSeconds 1 -TimeoutSeconds 300 -MaxSeconds 900
```

[The runner](../ingestion/scheduling.py) invokes the existing release CLI in an owned child process with an argument list and no shell. It replays an explicit, already accepted plan. Loading retained acquisitions and deliberately publishing a new plan remain separate steps in [the weather ingestion](21-weather-ingestion.md) and [publication runbooks](22-weather-publication.md). There is no live request, automatic source selection or automatic takeover of a failed publication.

| Control | Default / supported bound | Behaviour |
| --- | --- | --- |
| Executions | 1 / 1–24 | Finite number of ticks; first failure stops the batch |
| Delay | 60 seconds / 0–3,600 | Delay after the previous tick completes; no overlapping or catch-up ticks |
| Child timeout | 300 seconds / 1–900 | Kill and wait for the owned child on timeout; server statement timeout also applies, with a five-second lock timeout |
| Scheduling budget | 900 seconds / 1–3,600 | Monotonic deadline bounds remaining delays and each child; connection, file-write and process cleanup overhead can extend wall-clock completion |
| Plan identity | SHA-256 of reviewed bytes | Must match the accepted release; rechecked each tick and by the child before database access |
| Release identity | Accepted UUID at batch start | Passed as the expected parent; a concurrent publication causes a safe failure |
| Overlap control | Session advisory lock per stream | A second scheduler exits with `SCHEDULE_ALREADY_RUNNING`; the publisher retains its transaction locks |
| Output | Exit 0 success, 2 failure | UUID report in ignored `experiments/source-audit/schedule-runs/`; links each successful tick to its pipeline run/release |

The report is written before execution and atomically replaced as ticks progress. Child stderr and raw exception messages are excluded. Credentials come from the existing ignored `.env` or process environment, with no password argument. PostgreSQL remains authoritative if a child commits successfully but writing its JSON summary fails. A hard termination of the scheduler can leave a `running` report or a child still finishing; inspect database ownership and status before another attempt. The runner is a bounded local command; no persistent Windows task has been registered.

For a future Windows Task Scheduler trigger, use the wrapper's absolute path in the action, select the existing user account with access to this checkout, set the working directory to the repository, set “Do not start a new instance”, and use one bounded invocation per trigger. Verify Docker availability and the task's Last Run Result plus the JSON/database run IDs. Record the actual task name, trigger, account and first execution before claiming unattended scheduling. Do not put database credentials in the task action. Registration and unattended execution remain pending.

## Diagnose and recover

1. Check `docker compose ps` and `release status` before changing the accepted data. This session initially found Docker stopped; starting the engine/container restored database access.
2. Open the schedule report. `PLAN_CHANGED` requires review of the plan; a new plan needs deliberate publication first. `SCHEDULE_ALREADY_RUNNING` means another owner holds the stream lease. `SCHEDULE_DEADLINE` means the batch ran out of its execution budget.
3. For `CHILD_FAILED`, `CHILD_TIMEOUT`, an interrupted process or an ambiguous file-write outcome, inspect `ops.pipeline_run`, `ops.release` and `ops.publication_checkpoint`. Keep the accepted release pinned while inspecting; do not infer failure or success solely from a terminal message.
4. If the child committed, verify its accepted UUID/hash/checkpoint and replay normally. If publication failed or its backend disappeared, correct the input/configuration and use the existing same-plan resume procedure below. Resume verifies that the earlier backend is gone and that the accepted parent is unchanged; it rejects live or stale attempts.
5. Verify release status, then rerun the bounded schedule. A checkpoint represents completed quality accounting, including explicit NaNs; it does not certify full finite coverage.

```powershell
.venv\Scripts\python.exe -m ingestion release status --plan config/weather-release-plan.json
# Only when a matching failed/abandoned publication is verified:
.venv\Scripts\python.exe -m ingestion release resume --plan config/weather-release-plan.json
```

The isolated database checks cover both publication fault boundaries, a killed process, recovery versus clean rebuild, cross-connection schedule exclusion, real scheduled child replays and stopping after a controlled failed tick. Time-budget, plan mutation, interruption, secret-safe output and invalid child-result handling also have offline controls. These establish the current weather path; Helen/hourly/combined Gold acceptance and database restore remain later work.

## CI checks and visible failure demonstration

The [workflow](../.github/workflows/ci.yml) runs safe synthetic tests on Windows/Linux and 44 isolated PostgreSQL controls on Ubuntu, plus a separate weather dbt/Helsinki calendar job with 15 scenarios/nine models/36 SQL tests. It checks the scheduler, model and database-operations CLI help. An optional `failure_probe` Boolean input defaults to `false`. Normal checks still execute when the probe is selected. The separate probe job deliberately corrupts a temporary synthetic fixture and exits nonzero, producing a failing check without modifying retained fixtures or application data.

Local reproduction of the probe:

```powershell
.venv\Scripts\python.exe tools/ci_failure_probe.py
$LASTEXITCODE # Expected: 1, deliberate rejection of the corrupted fixture
```

To repeat the optional controlled-failure demonstration on a deliberately selected default-branch commit:

1. Record the normal green workflow URL, commit SHA and individual job conclusions.
2. In Actions → CI → Run workflow, enable `failure_probe`. Record the red workflow URL and the failing “Controlled failure demonstration” job/log. Do not use `continue-on-error` to hide this failure.
3. Dispatch again with `failure_probe=false` and record green recovery on the same commit. Keep all three URLs and explain the intentional failure in the tracker. Configure required branch checks separately if desired.

The default-branch requirement and manual-input procedure follow [GitHub's manual workflow documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). The updated workflow passes [actionlint 1.7.12](https://github.com/rhysd/actionlint/releases/tag/v1.7.12); its official release archive was checked against the published SHA-256 file before use. Local lint and a local exit code do not establish hosted success/failure. The original delivery had no hosted run URL; the subsequent verified runs are recorded below. No live-source CI schedule or deployment step is configured.

## Actual execution evidence

| Evidence | Result |
| --- | --- |
| Offline suite | 72 tests pass on Windows and fresh Linux Python 3.13.7; dependency checks pass |
| Database suite | 28 checks pass against local PostgreSQL 17.11; only the newly created UUID test database is removed |
| Schedule batch | `c6a5a547-f999-4c36-bb87-09d2738fe2dd`, two successful ticks, one-second delay |
| Pipeline runs | `cfdf1348-57ce-4547-8e2b-8c5b4bdea220`, `a06d5fdb-575b-4e23-920e-d487b20a237d` |
| Accepted release | `f327b833-7b99-453f-b376-d1f82a0fe7d9`, unchanged |
| Published keys | 105,264; 105,248 finite, 16 source NaNs, zero absent |
| Content SHA-256 | `ca80125fb35a1c2a288041523326469c6c7c87808279110936bfad0447093008`, unchanged |
| Checkpoint | Exclusive end `2025-12-31T22:00:00Z`; timestamp still equals the original publication transaction timestamp |
| Current ledger | 12 successful runs, 107 content snapshots, 108 acquisitions, 423 acquisition links, one accepted release, zero failed working-database candidates |
| CI failure preparation | Local probe exits 1; workflow lint passes; hosted run URLs remain pending |

Private evidence: `experiments/source-audit/scheduling-verification.json`, `schedule-runs/<schedule-id>.json` and `database-foundation.json`. Historical publication code hashes remain reproducible from the verified private `code-snapshots/wp2.4-utc/` archive. Raw data, credentials and private reports remain excluded from Git. See [the tracker](12-execution-tracker.md) for remaining completion conditions.

## Subsequent WP3.1 status

On 16 October 2026, [accepted-weather reporting views and loader/reporter groups](24-database-permissions.md) were verified. The current suite is 76 offline tests and 39 database checks on Windows/Linux. The loader-role replay keeps the original release/checkpoint; the working ledger has 13 successful runs and two retained failed startup attempts from the corrected session-visibility issue. Earlier counts above describe their dated delivery. Latest local evidence backup: 415 files/three sample restores, still on C:. Hosted CI, persistent application/BI logins and full Gold/E4 remain pending.

## Subsequent Helen and hosted CI delivery

[Helen source intake](25-helen-source-intake.md), delivered 16 October 2026, adds migration 006 and explicit loader-only SELECT/INSERT on two intake tables. That delivery had 83 offline tests/44 DB checks on Windows/Linux. Actual intake/replay retains 91,767 source records without changing weather publication. Hosted CI green/red/green is verified for 9fb12dd (76/39 baseline); Helen publication was pending at that delivery and is now verified in the expanded run below. The author confirms selected-literature review and consumption interpretation, and chooses local-only backup with shared-drive risk acceptance. Earlier counts above describe their dated delivery.

## Expanded hosted workflow and Windows correction

On 16 October 2026 the application/model/calendar/operations work and workflow were published together as `bdb1fcb`. The workflow now runs on pushes, pull requests and manual dispatch:

| Job execution | Verified scope |
| --- | --- |
| Offline tests (Ubuntu 24.04) | 95 unit/reference controls, dependency compatibility and main/scheduler/model/operations CLI help |
| Offline tests (Windows 2025) | The same 95 controls and CLI checks on Python 3.13.7 |
| PostgreSQL foundation | Seven migrations and 44 isolated ingestion/publication/permission controls on PostgreSQL 17.11 |
| Weather dbt and Helsinki calendar | Optional pinned dbt stack; 15 synthetic scenarios, nine models/36 SQL tests, DST/leap/ISO/partial-day coverage, deliberate bad-data rejection and recovery |

The optional controlled-failure job remains skipped on ordinary pushes. It was not dispatched again as part of this publication. The original 9fb12dd green/red/green evidence remains separate.

The [initial expanded run](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38895706029) failed in the Windows identity test; Ubuntu, PostgreSQL and weather/calendar jobs passed. Windows exposed the same temporary directory as both `RUNNER~1` and `runneradmin`. `project_path` resolved the model directory, while the caller's root still used the short alias; `Path.relative_to` therefore rejected it. Commit `c25c87f` resolves the root once before discovering and hashing files. A new portable relative-versus-canonical-root regression accompanies the original test that exposed the hosted Windows alias.

The [corrected push run](https://github.com/yuliplanora-hue/ThesisProject/actions/runs/38896004389) passes all four required job executions on commit `c25c87faf6a6b836090f2e234db0c7070d502d67`. This is real hosted certification of the expanded executable slice, not just workflow lint or a local result. Private metadata retains exact commit/run/job IDs, conclusions and UTC verification time in `experiments/source-audit/hosted-ci-bdb1fcb.json` and `hosted-ci-c25c87f.json`; the failed job log is retained privately too. Historical actual-model code remains checksum-verified in its prior code snapshot; the path fix does not reinterpret source observations.

The workflow grants only `contents: read`, pins actions by commit, uses disposable PostgreSQL fixture credentials and cancels superseded runs on the same ref. Ordinary CI uses manufactured inputs, never the local Helen/FMI downloads, `.env`, evidence backups or database archives. The WP3.4 real-data restore/index rehearsal remains local; its boundary guards and CLI import/help are checked offline. No continuous deployment, branch protection or persistent scheduler is enabled by this update.
