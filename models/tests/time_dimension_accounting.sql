with missing_hours as (
    (select release_id,hour_start_utc from {{ ref('fct_weather_hour') }}
     except all select release_id,hour_start_utc from {{ ref('dim_hour') }})
    union all
    (select release_id,hour_start_utc from {{ ref('dim_hour') }}
     except all select release_id,hour_start_utc from {{ ref('fct_weather_hour') }})
)
select 'hour_keys' as failure from missing_hours
union all
select 'day_coverage' from {{ ref('dim_date') }}
where expected_day_hour_count not in (23,24,25)
   or release_hour_count not between 1 and expected_day_hour_count
   or is_full_day_in_release is distinct from (release_hour_count=expected_day_hour_count)
union all
select 'hour_labels' from {{ ref('dim_hour') }}
where local_date is distinct from local_hour_start::date
   or local_hour not between 0 and 23 or utc_offset_minutes not in (120,180)
   or local_fold not in (0,1)
   or (local_hour_start - utc_offset_minutes*interval '1 minute')
      is distinct from (hour_start_utc at time zone 'UTC')
