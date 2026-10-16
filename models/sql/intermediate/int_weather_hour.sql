with spine as (
    select r.release_id, r.station_id, r.parameter_id, h.hour_start_utc
    from {{ ref('stg_weather_release') }} r
    cross join lateral generate_series(r.start_utc, r.end_utc_exclusive - interval '1 hour',
                                       interval '1 hour') h(hour_start_utc)
), samples as (
    select release_id, station_id, parameter_id,
           date_bin(interval '1 hour', observed_at_utc, '1970-01-01 00:00:00+00'::timestamptz) as hour_start_utc,
           count(*)::integer as published_slot_count,
           count(*) filter (where source_quality = 'observed' and temperature_c is not null)::integer as finite_sample_count,
           count(*) filter (where source_quality = 'source_nan')::integer as source_nan_count,
           count(*) filter (where source_quality = 'source_absent')::integer as source_absent_count,
           avg(temperature_c) as sampled_mean
    from {{ ref('stg_weather_point') }}
    group by release_id, station_id, parameter_id, hour_start_utc
)
select s.release_id, s.station_id, s.parameter_id, s.hour_start_utc,
       6::integer as expected_sample_count,
       coalesce(p.published_slot_count,0) as published_slot_count,
       coalesce(p.finite_sample_count,0) as finite_sample_count,
       coalesce(p.source_nan_count,0) as source_nan_count,
       coalesce(p.source_absent_count,0) as source_absent_count,
       (6-coalesce(p.published_slot_count,0)) as missing_published_slot_count,
       case when p.published_slot_count=6 and p.finite_sample_count=6
            then p.sampled_mean else null::numeric end as temperature_c
from spine s left join samples p
using (release_id, station_id, parameter_id, hour_start_utc)
