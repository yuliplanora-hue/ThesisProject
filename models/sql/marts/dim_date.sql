with limits as (
    select release_id, start_utc, end_utc_exclusive,
           (start_utc at time zone 'Europe/Helsinki')::date as first_date,
           ((end_utc_exclusive - interval '1 microsecond') at time zone 'Europe/Helsinki')::date as last_date
    from {{ ref('stg_weather_release') }}
), dates as (
    select release_id, start_utc, end_utc_exclusive, first_date + n as local_date
    from limits cross join lateral generate_series(0, last_date-first_date) n
), bounds as (
    select *, local_date::timestamp at time zone 'Europe/Helsinki' as day_start_utc,
           (local_date+1)::timestamp at time zone 'Europe/Helsinki' as day_end_utc
    from dates
)
select release_id, local_date, day_start_utc, day_end_utc,
       extract(year from local_date)::integer as calendar_year,
       extract(month from local_date)::integer as calendar_month,
       extract(day from local_date)::integer as day_of_month,
       extract(isoyear from local_date)::integer as iso_year,
       extract(week from local_date)::integer as iso_week,
       extract(isodow from local_date)::integer as iso_weekday,
       (extract(isodow from local_date) in (6,7)) as is_weekend,
       (extract(epoch from day_end_utc-day_start_utc)/3600)::integer as expected_day_hour_count,
       (extract(epoch from least(day_end_utc,end_utc_exclusive)-greatest(day_start_utc,start_utc))/3600)::integer as release_hour_count,
       (start_utc<=day_start_utc and end_utc_exclusive>=day_end_utc) as is_full_day_in_release
from bounds
