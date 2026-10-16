select h.release_id, h.hour_start_utc, p.observed_at_utc, p.station_id, p.parameter_id,
       p.snapshot_id, p.source_point_index, p.source_quality
from {{ ref('fct_weather_hour') }} h
join {{ ref('stg_weather_point') }} p
  on p.release_id = h.release_id and p.station_id = h.station_id and p.parameter_id = h.parameter_id
 and date_bin(interval '1 hour', p.observed_at_utc, '1970-01-01 00:00:00+00'::timestamptz) = h.hour_start_utc
