-- Weather-only accepted releases; hourly/heat/BI Gold models are still future work.
CREATE SCHEMA publication;

ALTER TABLE silver.weather_observation ADD UNIQUE
    (snapshot_id, station_id, parameter_id, observed_at_utc, source_point_index);

CREATE TABLE ops.release (
    release_id uuid PRIMARY KEY,
    stream_id text NOT NULL,
    build_run_id uuid NOT NULL REFERENCES ops.pipeline_run(run_id),
    parent_release_id uuid REFERENCES ops.release(release_id),
    plan_sha256 text NOT NULL CHECK (plan_sha256 ~ '^[0-9a-f]{64}$'),
    plan jsonb NOT NULL,
    station_id text NOT NULL,
    parameter_id text NOT NULL CHECK (parameter_id = 't2m'),
    start_utc timestamptz NOT NULL,
    end_utc_exclusive timestamptz NOT NULL CHECK (end_utc_exclusive > start_utc),
    status text NOT NULL CHECK (status IN ('accepted', 'failed')),
    content_sha256 text CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    counts jsonb NOT NULL,
    completed_at_utc timestamptz NOT NULL DEFAULT now(),
    CHECK ((status = 'accepted' AND content_sha256 IS NOT NULL)
        OR (status = 'failed' AND content_sha256 IS NULL)),
    UNIQUE (stream_id, release_id),
    UNIQUE (release_id, station_id, parameter_id)
);

CREATE TABLE ops.release_source (
    release_id uuid NOT NULL REFERENCES ops.release(release_id),
    snapshot_id uuid NOT NULL REFERENCES ops.weather_snapshot_load(snapshot_id),
    layer_index integer NOT NULL CHECK (layer_index >= 0),
    PRIMARY KEY (release_id, snapshot_id, layer_index)
);

CREATE TABLE publication.weather_point (
    release_id uuid NOT NULL,
    station_id text NOT NULL,
    parameter_id text NOT NULL CHECK (parameter_id = 't2m'),
    observed_at_utc timestamptz NOT NULL,
    temperature_c numeric,
    source_quality text NOT NULL CHECK (source_quality IN ('observed', 'source_nan', 'source_absent')),
    snapshot_id uuid,
    source_point_index integer,
    PRIMARY KEY (release_id, observed_at_utc),
    CHECK (extract(epoch FROM observed_at_utc) % 600 = 0),
    CHECK ((source_quality = 'source_absent' AND temperature_c IS NULL AND snapshot_id IS NULL AND source_point_index IS NULL)
        OR (source_quality = 'source_nan' AND temperature_c IS NULL AND snapshot_id IS NOT NULL AND source_point_index IS NOT NULL)
        OR (source_quality = 'observed' AND temperature_c IS NOT NULL AND snapshot_id IS NOT NULL AND source_point_index IS NOT NULL
            AND temperature_c > '-Infinity'::numeric AND temperature_c < 'Infinity'::numeric)),
    FOREIGN KEY (release_id, station_id, parameter_id) REFERENCES ops.release(release_id, station_id, parameter_id),
    FOREIGN KEY (snapshot_id, station_id, parameter_id, observed_at_utc, source_point_index)
        REFERENCES silver.weather_observation(snapshot_id, station_id, parameter_id, observed_at_utc, source_point_index)
);

CREATE TABLE ops.accepted_release (
    stream_id text PRIMARY KEY,
    release_id uuid NOT NULL,
    FOREIGN KEY (stream_id, release_id) REFERENCES ops.release(stream_id, release_id)
);

CREATE TABLE ops.publication_checkpoint (
    stream_id text PRIMARY KEY,
    release_id uuid NOT NULL,
    completed_end_utc timestamptz NOT NULL,
    plan_sha256 text NOT NULL CHECK (plan_sha256 ~ '^[0-9a-f]{64}$'),
    updated_at_utc timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (stream_id, release_id) REFERENCES ops.release(stream_id, release_id)
);

CREATE VIEW publication.current_weather_point AS
SELECT head.stream_id, point.* FROM ops.accepted_release head
JOIN ops.release release ON release.release_id = head.release_id AND release.status = 'accepted'
JOIN publication.weather_point point ON point.release_id = head.release_id;
