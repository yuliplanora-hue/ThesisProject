-- Metadata only: source semantics are not yet accepted for analytical loading.
CREATE TABLE ops.source_snapshot (
    snapshot_id uuid PRIMARY KEY,
    source_id text NOT NULL CHECK (source_id <> ''),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    source_locator text NOT NULL,
    first_recorded_at_utc timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, content_sha256)
);

CREATE TABLE ops.pipeline_run (
    run_id uuid PRIMARY KEY,
    purpose text NOT NULL,
    configuration_sha256 text NOT NULL CHECK (configuration_sha256 ~ '^[0-9a-f]{64}$'),
    code_version text NOT NULL,
    status text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at_utc timestamptz NOT NULL DEFAULT now(),
    completed_at_utc timestamptz,
    stage_counts jsonb NOT NULL DEFAULT '{}',
    error_code text,
    CHECK ((status = 'running' AND completed_at_utc IS NULL AND error_code IS NULL)
        OR (status = 'succeeded' AND completed_at_utc IS NOT NULL AND error_code IS NULL)
        OR (status = 'failed' AND completed_at_utc IS NOT NULL AND error_code IS NOT NULL))
);

CREATE TABLE ops.run_input (
    run_id uuid NOT NULL REFERENCES ops.pipeline_run(run_id),
    snapshot_id uuid NOT NULL REFERENCES ops.source_snapshot(snapshot_id),
    PRIMARY KEY (run_id, snapshot_id)
);
