select p.release_id, p.observed_at_utc
from {{ ref('stg_weather_point') }} p
left join {{ ref('stg_weather_release') }} r using (release_id)
where r.release_id is null or p.station_id is distinct from r.station_id
   or p.parameter_id is distinct from r.parameter_id or p.stream_id is distinct from r.stream_id
   or p.observed_at_utc < r.start_utc or p.observed_at_utc >= r.end_utc_exclusive
   or extract(epoch from p.observed_at_utc) % 600 <> 0
   or (p.source_point_index is not null and p.source_point_index <= 0)
   or p.source_quality not in ('observed','source_nan','source_absent')
   or (p.source_quality = 'observed' and (p.temperature_c is null or p.snapshot_id is null or p.source_point_index is null
       or not (p.temperature_c > '-Infinity'::numeric and p.temperature_c < 'Infinity'::numeric)))
   or (p.source_quality = 'source_nan' and (p.temperature_c is not null or p.snapshot_id is null or p.source_point_index is null))
   or (p.source_quality = 'source_absent' and (p.temperature_c is not null or p.snapshot_id is not null or p.source_point_index is not null))
