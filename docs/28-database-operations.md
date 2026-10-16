# WP3.4 database restore and query optimisation

**Verified:** 16 October 2026. **Status:** current local database backup/restore and measured lookup optimisation delivered. The 15-hour WP3.4 estimate is unchanged; actual author hours and competency demonstration remain to record. Final E4, clean-checkout/external reproduction, full/incremental load benchmarks and accepted combined Gold remain later work.

## Run the rehearsal

From the repository folder, with Docker Compose running and the setup connection configured in ignored `.env`:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe tools/database_operations.py --help
.venv\Scripts\python.exe tools/database_operations.py --release-id f327b833-7b99-453f-b376-d1f82a0fe7d9
```

Use the setup account with database/role creation privileges and `ENERGY_DB_ROLE` unset. The pinned release must already be accepted and the candidate graph must have been built for that exact UUID. Finish ingestion/model builds before starting. The command refuses an already-running pipeline attempt; a final live fingerprint comparison also detects changes during the rehearsal.

The [operations helper](../tools/database_operations.py) uses `pg_dump`/`pg_restore` from the existing PostgreSQL 17 Compose service. `--client-mode local` instead uses installed PostgreSQL clients and the same configured connection. Both routes were verified with Python 3.13.7 and PostgreSQL 17.11. The helper checks that the client tools and Python connection reach the same server. It passes local-client passwords through an environment variable, never subprocess arguments or retained diagnostics. No extra Python modelling dependency is required.

Each invocation generates a new `energy_restore_test_<uuid>` database and separate UUID-named groups/login, creates a new local archive, verifies it, benchmarks only the restored copy and closes/removes its own temporary resources. It never selects the working database as a restore or cleanup target. No `--clean`, volume deletion or forced session termination is used. The working pipeline ledger remains at 18 successful and two retained failed runs; operations evidence has separate operation IDs.

## Backup consistency and comparison

The source connection exports a repeatable-read, read-only snapshot. `pg_dump --format=custom --snapshot <id> --no-acl` reads that snapshot while the exporter stays open. All source fingerprints are computed in the same snapshot. PostgreSQL documents [consistent single-database backups and custom archives](https://www.postgresql.org/docs/17/app-pgdump.html); cluster roles are outside a database dump.

The archive is binary-streamed directly to a fresh ignored `backup/database-<timestamp>-<uuid>/database.dump`; its SHA-256 is checked again before restoration. The helper avoids routing archive bytes through a PowerShell text pipeline. The [restore options](https://www.postgresql.org/docs/17/app-pgrestore.html) are `--no-owner --no-acl --exit-on-error --single-transaction`, directed at the newly created database. A failed restore cannot silently leave a successful partial result.

Comparison covers all **27 project tables/views** in `ops`, `silver`, `publication`, `reporting` and `dbt_weather`:

- Ordered column names/types/nullability, constraint definitions, index definitions and view definitions.
- Full row multisets, canonically ordered as PostgreSQL JSON text under UTC/ISO formatting and hashed with SHA-256; duplicates and NULLs remain significant.
- The operational migration/run/acquisition/input records, accepted-release pointers/checkpoints, chosen-source lineage, source history and all candidate reporting outputs.

Counts across these relations total 797,144, including overlapping views; this is not a count of distinct source measurements. Restored migration replay skips all seven unchanged migrations. Independent calendar checks still find 17,544 UTC hours, 731 Helsinki dates and 728 complete weather days.

Ownership and ACLs are deliberately re-established for the destination rather than compared byte-for-byte with source-cluster bindings. PUBLIC database access is revoked. Fresh loader/reporter/transformer groups receive the explicit project grants; all nine candidate objects are assigned to the destination transformer, whose safe reprovisioning and graph reads are checked. No source role is repurposed. A real temporary reporter login reads accepted weather, has no INSERT/UPDATE/DELETE grant on the reporting view, and is denied underlying writes, operations/Silver/candidate reads and temporary-table creation. The join view itself also rejects updates as non-updatable. Persistent application/BI credentials and fresh-cluster recovery are separate tasks.

After the rehearsal, a new source fingerprint must equal the saved one. The source accepted pointer/checkpoint, all source rows and candidate models remain unchanged. The trial index is absent from the working database.

## Measured query/index change

The [versioned lookup query](../sql/operations/weather_hour_lookup.sql) selects one UTC day from `dbt_weather.int_weather_hour`, filtering by release, station, parameter and half-open time bounds, ordered by UTC hour. The frozen test window is **11 September 2024 UTC**, station `100971`, `t2m`. Its **24 rows include two NULL temperatures**; both variants return exactly the same keys, values and counts on every repetition. Result SHA-256 is `c6f82c36300b1edfa81ea3199faad490a3f1a9e8159c3eca4e31e5819ba38e0b`.

The change is a B-tree on `(release_id, station_id, parameter_id, hour_start_utc)`, created only in the restored copy. It changes a sequential scan plus sort to an index scan. The index occupies **1,064,960 bytes**; latest Windows build time is **8.316 ms**. The helper records the actual build time and size separately from query timing.

For each variant, `ANALYZE` precedes one unmeasured warm-up and **five measured SELECT/fetch repetitions**, with five separate [`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` probes](https://www.postgresql.org/docs/17/sql-explain.html). Read queries share one frozen restored snapshot, so they start from unchanged data without replaying a mutation. Caches are warm and not flushed; baseline runs before indexed. Restoration, index creation, statistics collection, validation and EXPLAIN probes are excluded from client query timing. Instrumented server execution and client roundtrip/fetch timings are reported separately.

Latest Windows results (milliseconds; full samples/plans retained):

| Measurement | Baseline | Indexed |
| --- | ---: | ---: |
| Server execution median | 0.760 | 0.021 |
| Server execution range | 0.714–2.780 | 0.020–0.024 |
| Client SELECT/fetch median | 1.792 | 0.696 |
| Client SELECT/fetch range | 1.523–2.036 | 0.601–0.874 |
| Shared buffer hits per probe | 264 | 4 |
| Shared disk reads per probe | 0 | 0 |

This is a small warm-cache development lookup, with fixed ordering and local timing noise. The observed server median ratio is 36.19, while absolute client savings are about one millisecond. It does not establish a production speedup, cold-cache behaviour, full-load throughput or incremental-load performance. The live dbt table remains unindexed: materialising a new candidate replaces it, and adding a permanent post-build index should depend on the final reporting workload. Final five-repeat full/incremental experiments still require the reset/baseline procedure in the [evaluation protocol](03-evaluation-protocol.md).

## Evidence and recovery limits

Latest Windows operation: **`2e61a527badf46a7b3bd4dffbb40b8ea`**.

- Private summary/code snapshots and baseline/indexed raw plans: `experiments/source-audit/database-operations/2e61a527badf46a7b3bd4dffbb40b8ea/`.
- Archive and duplicated manifest: `backup/database-20261016T113445Z-2e61a527badf46a7b3bd4dffbb40b8ea/`.
- Archive: **4,775,792 bytes**, SHA-256 `6b86f93fe788208ce8d0e2c885e0adc6ec4aca055accc8831b225acc8db75c6f`.
- Dump/restore client durations: **0.795 / 1.478 seconds**. These exclude the full comparison and subsequent checks.

Fresh Linux uses the local-client mode with read-only project files and separate writable artifact/backup mounts. Both platforms pass the same full relation comparison, reporter boundaries, calendar checks and result equality; their source fingerprints and lookup-result hashes agree. Both archives were independently re-hashed after the runs. **94 offline tests pass on Windows/Linux**; the unchanged prior foundation/model baselines are 44 database controls and 15 synthetic scenarios/nine models/36 SQL tests.

Latest Linux operation: **`b00d5d3ee78b40d181a8294d4805d11c`**, evidence in `experiments/source-audit/linux-database-operations/b00d5d3ee78b40d181a8294d4805d11c/`; its actual host archive is `backup/linux-database-operations/database-20261016T113537Z-b00d5d3ee78b40d181a8294d4805d11c/database.dump`. The container's manifest records its mounted path as `backup/database-…`. Archive size is **4,834,727 bytes**, SHA-256 `1718875be0af7568ce18d99f0fb6b77cb93620732c7253885af7a8fcb1b8ec2c`. Dump/restore durations are 0.748/1.210 seconds. Server median is 0.664 → 0.015 ms (ranges 0.654–0.727 / 0.013–0.068); client median is 0.888 → 0.193 ms (ranges 0.833–1.156 / 0.145–0.321). These are separate measurements, not pooled with Windows timings.

`experiments/source-audit/database-operations/environment-20261016.json` records post-run resource context and the final checksum/cleanup checks: Docker exposes 16 CPUs and 16,647,372,800 bytes of RAM; the PostgreSQL container has no additional memory/CPU quota. PostgreSQL settings retain their separate numeric value and unit. This context is not a measurement of resource utilisation during individual queries.

The first attempt, `5c42ecbbafb54919a72933878a4a2838`, is retained with its archive and exact code: restore/fingerprint comparison passed, then the original reporter probe stopped on `ObjectNotInPrerequisiteState` for the non-updatable join view. Subsequent probes explicitly verify absent write grants and permission denial on the underlying table, accepting non-updatability only for that view. Intermediate successful runs are also retained; no failed evidence was overwritten.

The helper saves commands, tool/server/client versions, source/restore fingerprints, operation UUID, code/query hashes, UTC timestamps, test outcomes, raw timings and cleanup state in private manifests. It preserves exact helper source alongside the report. All invocation-created databases/roles are removed; a post-run check confirmed no `energy_restore_test_*` database or `energy_restore_*` role remained. A hard process/host kill can bypass Python cleanup; the manifest/directory UUID identifies the exact resources for diagnosis. Do not issue broad wildcard cleanup.

The archives contain private Helen source values and local provenance. They remain excluded from Git; current Helen redistribution/licence acceptance is unchanged. These are same-machine logical database restores with reconstructed groups, using the author-selected C: backup location. No independent storage, complete cluster/PITR recovery, physical-volume restore or final E4 pass is claimed. Archive retention follows the [DMP](15-data-management-plan.md). No GitHub Actions job downloads or uploads the real database archive.

Next is **WP4.1: governed metric reference SQL and synthetic-fixture validation**. Interpreted actual Helen/paired measures still require source acceptance; initial metric implementation can use the existing manufactured controls without inventing physical approval.
