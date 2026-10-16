with spine as (
    select r.release_id, h.hour_start_utc
    from {{ ref('stg_weather_release') }} r
    cross join lateral generate_series(r.start_utc, r.end_utc_exclusive - interval '1 hour',
                                       interval '1 hour') h(hour_start_utc)
), labels as (
    select *, hour_start_utc at time zone 'Europe/Helsinki' as local_hour_start,
           hour_start_utc at time zone 'UTC' as utc_hour_start
    from spine
)
select release_id, hour_start_utc, hour_start_utc + interval '1 hour' as hour_end_utc,
       local_hour_start, local_hour_start::date as local_date,
       extract(hour from local_hour_start)::integer as local_hour,
       (extract(epoch from local_hour_start - utc_hour_start)/60)::integer as utc_offset_minutes,
       case when (hour_start_utc - interval '1 hour') at time zone 'Europe/Helsinki' = local_hour_start
            then 1 else 0 end as local_fold
from labels
