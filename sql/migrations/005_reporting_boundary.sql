-- Local accepted-weather reporting boundary. Role provisioning is a separate admin action.
CREATE SCHEMA reporting;

DO $$
BEGIN
    EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA ops, silver, publication, reporting FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA ops, silver, publication, reporting FROM PUBLIC;

-- Owner privileges resolve the underlying joins; readers get SELECT on these views only.
CREATE VIEW reporting.weather_release WITH (security_barrier = true) AS
SELECT r.release_id, r.stream_id, r.station_id, r.parameter_id,
       r.start_utc, r.end_utc_exclusive, r.content_sha256, r.plan_sha256,
       r.counts, r.completed_at_utc,
       (h.release_id IS NOT NULL) AS is_current
FROM ops.release r
LEFT JOIN ops.accepted_release h ON h.stream_id = r.stream_id AND h.release_id = r.release_id
WHERE r.status = 'accepted';

CREATE VIEW reporting.weather_point WITH (security_barrier = true) AS
SELECT r.stream_id, p.release_id, p.station_id, p.parameter_id,
       p.observed_at_utc, p.temperature_c, p.source_quality,
       p.snapshot_id, p.source_point_index
FROM publication.weather_point p
JOIN ops.release r ON r.release_id = p.release_id AND r.status = 'accepted';
