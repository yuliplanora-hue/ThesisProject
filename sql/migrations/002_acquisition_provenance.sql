-- Acquisition evidence is independent of analytical acceptance and loading.
CREATE TABLE ops.source_acquisition (
    acquisition_id uuid PRIMARY KEY,
    snapshot_id uuid NOT NULL REFERENCES ops.source_snapshot(snapshot_id),
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    manifest_locator text NOT NULL,
    raw_bytes bigint NOT NULL CHECK (raw_bytes > 0),
    retrieved_at_utc timestamptz NOT NULL,
    request_url text NOT NULL,
    request_parameters jsonb NOT NULL,
    source_status text NOT NULL CHECK (source_status IN ('acquired', 'inspected')),
    registered_at_utc timestamptz NOT NULL DEFAULT now(),
    UNIQUE (snapshot_id, manifest_sha256),
    UNIQUE (acquisition_id, snapshot_id)
);

CREATE TABLE ops.run_acquisition (
    run_id uuid NOT NULL,
    acquisition_id uuid NOT NULL,
    snapshot_id uuid NOT NULL,
    PRIMARY KEY (run_id, acquisition_id),
    FOREIGN KEY (run_id, snapshot_id) REFERENCES ops.run_input(run_id, snapshot_id),
    FOREIGN KEY (acquisition_id, snapshot_id)
        REFERENCES ops.source_acquisition(acquisition_id, snapshot_id)
);
