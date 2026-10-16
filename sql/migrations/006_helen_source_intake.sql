-- Source-faithful intake only; no inferred energy conversion or analytical release.
CREATE TABLE ops.helen_snapshot_load (
    snapshot_id uuid PRIMARY KEY REFERENCES ops.source_snapshot(snapshot_id),
    first_loaded_run_id uuid NOT NULL,
    parser_version text NOT NULL,
    intake_contract_sha256 text NOT NULL CHECK (intake_contract_sha256 ~ '^[0-9a-f]{64}$'),
    source_rows integer NOT NULL CHECK (source_rows >= 0),
    valid_rows integer NOT NULL CHECK (valid_rows >= 0),
    quarantined_rows integer NOT NULL CHECK (quarantined_rows >= 0),
    negative_rows integer NOT NULL CHECK (negative_rows >= 0),
    CHECK (source_rows = valid_rows + quarantined_rows),
    CHECK (negative_rows <= source_rows),
    FOREIGN KEY (first_loaded_run_id, snapshot_id) REFERENCES ops.run_input(run_id, snapshot_id)
);

CREATE TABLE silver.helen_source_record (
    snapshot_id uuid NOT NULL REFERENCES ops.helen_snapshot_load(snapshot_id),
    source_record_index integer NOT NULL CHECK (source_record_index > 0),
    source_line_end integer NOT NULL CHECK (source_line_end >= 2),
    source_fields jsonb NOT NULL CHECK (jsonb_typeof(source_fields) = 'array'),
    source_label_utc timestamptz,
    interval_start_utc timestamptz,
    interval_end_utc timestamptz,
    source_measurement numeric,
    row_status text NOT NULL CHECK (row_status IN ('valid','quarantined')),
    rejection_reasons text[] NOT NULL,
    warnings text[] NOT NULL,
    PRIMARY KEY (snapshot_id, source_record_index),
    CHECK ((source_label_utc IS NULL AND interval_start_utc IS NULL AND interval_end_utc IS NULL)
        OR (source_label_utc IS NOT NULL AND interval_start_utc IS NOT NULL AND interval_end_utc IS NOT NULL
            AND interval_end_utc = source_label_utc
            AND interval_start_utc = interval_end_utc - interval '1 hour')),
    CHECK (source_measurement IS NULL OR
        (source_measurement > '-Infinity'::numeric AND source_measurement < 'Infinity'::numeric)),
    CHECK ((row_status = 'valid' AND cardinality(rejection_reasons) = 0
            AND source_label_utc IS NOT NULL AND source_measurement IS NOT NULL
            AND extract(epoch FROM source_label_utc) % 3600 = 0)
        OR (row_status = 'quarantined' AND cardinality(rejection_reasons) > 0))
);
CREATE UNIQUE INDEX helen_valid_snapshot_hour
ON silver.helen_source_record (snapshot_id, interval_start_utc) WHERE row_status = 'valid';
