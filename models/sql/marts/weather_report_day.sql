with daily as (
    select release_id, station_id, parameter_id, local_date,
           count(*)::integer as present_hour_count,
           count(*) filter (where is_complete)::integer as complete_hour_count,
           sum(source_nan_count)::integer as source_nan_count,
           sum(source_absent_count)::integer as source_absent_count,
           sum(missing_published_slot_count)::integer as missing_published_slot_count,
           avg(temperature_c) as complete_hour_mean
    from {{ ref('weather_report_hour') }}
    group by release_id,station_id,parameter_id,local_date
), coverage as (
    select c.*, r.station_id, r.parameter_id,
           coalesce(d.present_hour_count,0) as present_hour_count,
           coalesce(d.complete_hour_count,0) as complete_hour_count,
           coalesce(d.source_nan_count,0) as source_nan_count,
           coalesce(d.source_absent_count,0) as source_absent_count,
           coalesce(d.missing_published_slot_count,0) as missing_published_slot_count,
           d.complete_hour_mean
    from {{ ref('dim_date') }} c
    join {{ ref('stg_weather_release') }} r using (release_id)
    left join daily d using (release_id,station_id,parameter_id,local_date)
), eligibility as (
    select *, (is_full_day_in_release and present_hour_count=expected_day_hour_count
               and complete_hour_count=expected_day_hour_count) as is_complete_weather_day
    from coverage
)
select release_id,station_id,parameter_id,local_date,day_start_utc,day_end_utc,
       expected_day_hour_count,release_hour_count,present_hour_count,complete_hour_count,
       expected_day_hour_count-release_hour_count as out_of_window_hour_count,
       release_hour_count-present_hour_count as missing_model_hour_count,
       present_hour_count-complete_hour_count as incomplete_hour_count,
       source_nan_count,source_absent_count,missing_published_slot_count,
       is_full_day_in_release,is_complete_weather_day,
       case when is_complete_weather_day then complete_hour_mean else null::numeric end as temperature_c,
       false as is_imputed
from eligibility
