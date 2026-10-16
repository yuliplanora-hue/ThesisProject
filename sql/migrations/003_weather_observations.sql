-- Typed FMI source-resolution revisions; no hourly aggregate or Gold publication.
CREATE SCHEMA silver;

CREATE TABLE ops.weather_snapshot_load (
    snapshot_id uuid PRIMARY KEY REFERENCES ops.source_snapshot(snapshot_id),
    first_loaded_run_id uuid NOT NULL,
    contract_sha256 text NOT NULL CHECK (contract_sha256 ~ '^[0-9a-f]{64}$'),
    parser_version text NOT NULL,
    station_id text NOT NULL,
    parameter_id text NOT NULL CHECK (parameter_id = 't2m'),
    unit text NOT NULL CHECK (unit = 'degC'),
    start_utc timestamptz NOT NULL,
    end_utc_exclusive timestamptz NOT NULL CHECK (end_utc_exclusive > start_utc),
    timestep_minutes integer NOT NULL CHECK (timestep_minutes = 10),
    expected_samples integer NOT NULL CHECK (expected_samples > 0),
    returned_samples integer NOT NULL CHECK (returned_samples >= 0),
    source_nan_samples integer NOT NULL CHECK (source_nan_samples >= 0),
    absent_samples integer NOT NULL CHECK (absent_samples >= 0),
    excluded_endpoint_samples integer NOT NULL CHECK (excluded_endpoint_samples >= 0),
    station_metadata jsonb NOT NULL,
    UNIQUE (snapshot_id, station_id, parameter_id),
    CHECK (expected_samples = returned_samples + absent_samples),
    CHECK (source_nan_samples <= returned_samples),
    FOREIGN KEY (first_loaded_run_id, snapshot_id) REFERENCES ops.run_input(run_id, snapshot_id)
);

CREATE TABLE silver.weather_observation (
    snapshot_id uuid NOT NULL,
    station_id text NOT NULL,
    parameter_id text NOT NULL CHECK (parameter_id = 't2m'),
    observed_at_utc timestamptz NOT NULL,
    temperature_c numeric,
    source_value text NOT NULL,
    source_point_index integer NOT NULL CHECK (source_point_index > 0),
    source_quality text NOT NULL CHECK (source_quality IN ('observed', 'source_nan')),
    first_loaded_run_id uuid NOT NULL,
    CHECK (extract(epoch FROM observed_at_utc) % 600 = 0),
    PRIMARY KEY (snapshot_id, station_id, parameter_id, observed_at_utc),
    UNIQUE (snapshot_id, source_point_index),
    CHECK ((source_quality = 'source_nan' AND temperature_c IS NULL AND lower(source_value) = 'nan')
        OR (source_quality = 'observed' AND temperature_c IS NOT NULL
            AND temperature_c > '-Infinity'::numeric AND temperature_c < 'Infinity'::numeric)),
    FOREIGN KEY (first_loaded_run_id, snapshot_id) REFERENCES ops.run_input(run_id, snapshot_id),
    FOREIGN KEY (snapshot_id, station_id, parameter_id)
        REFERENCES ops.weather_snapshot_load(snapshot_id, station_id, parameter_id)
);
