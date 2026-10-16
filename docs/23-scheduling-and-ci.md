# WP2.5 bounded scheduling and CI operations

**Verified locally:** 15 October 2026. **Status:** local weather scheduling and recovery checks delivered; WP2.5 remains in progress until hosted CI success and deliberate failure evidence are recorded. This work supports FR-11, NFR-01/04/09/12, E2/E3/E4 preparation and SK-12. Actual author hours and competency review remain unrecorded; the task estimate stays 15 hours. Final E1–E7 execution remains separate.

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

The [workflow](../.github/workflows/ci.yml) runs safe synthetic tests on Windows/Linux and the current 39 isolated PostgreSQL checks on Ubuntu. It adds a scheduler help check and an optional `failure_probe` Boolean input, default `false`. Normal checks still execute when the probe is selected. The separate probe job deliberately corrupts a temporary synthetic fixture and exits nonzero, producing a failing check without modifying retained fixtures or application data.

Local reproduction of the probe:

```powershell
.venv\Scripts\python.exe tools/ci_failure_probe.py
$LASTEXITCODE # Expected: 1, deliberate rejection of the corrupted fixture
```

After publishing the reviewed workflow to the repository's default branch:

1. Record the normal green workflow URL, commit SHA and individual job conclusions.
2. In Actions → CI → Run workflow, enable `failure_probe`. Record the red workflow URL and the failing “Controlled failure demonstration” job/log. Do not use `continue-on-error` to hide this failure.
3. Dispatch again with `failure_probe=false` and record green recovery on the same commit. Keep all three URLs and explain the intentional failure in the tracker. Configure required branch checks separately if desired.

The default-branch requirement and manual-input procedure follow [GitHub's manual workflow documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). The updated workflow passes [actionlint 1.7.12](https://github.com/rhysd/actionlint/releases/tag/v1.7.12); its official release archive was checked against the published SHA-256 file before use. Local lint and a local exit code do not establish hosted success/failure. There is no hosted run URL yet, live-source CI schedule or deployment step.

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
