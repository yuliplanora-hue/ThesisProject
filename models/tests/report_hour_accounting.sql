with differences as (
    (select release_id,station_id,parameter_id,hour_start_utc,temperature_c,is_complete,
            source_nan_count,source_absent_count,missing_published_slot_count from {{ ref('fct_weather_hour') }}
     except all
     select release_id,station_id,parameter_id,hour_start_utc,temperature_c,is_complete,
            source_nan_count,source_absent_count,missing_published_slot_count from {{ ref('weather_report_hour') }})
    union all
    (select release_id,station_id,parameter_id,hour_start_utc,temperature_c,is_complete,
            source_nan_count,source_absent_count,missing_published_slot_count from {{ ref('weather_report_hour') }}
     except all
     select release_id,station_id,parameter_id,hour_start_utc,temperature_c,is_complete,
            source_nan_count,source_absent_count,missing_published_slot_count from {{ ref('fct_weather_hour') }})
)
select * from differences
