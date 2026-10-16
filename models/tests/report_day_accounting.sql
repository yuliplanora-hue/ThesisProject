with totals as (
    select (select count(*) from {{ ref('weather_report_hour') }}) as hours,
           (select sum(present_hour_count) from {{ ref('weather_report_day') }}) as day_hours,
           (select count(*) from {{ ref('dim_date') }}) as dates,
           (select count(*) from {{ ref('weather_report_day') }}) as day_rows
)
select 'totals' as failure from totals where hours is distinct from day_hours or dates<>day_rows
union all
select 'eligibility' from {{ ref('weather_report_day') }}
where missing_model_hour_count<>0 or missing_published_slot_count<>0
   or incomplete_hour_count<>present_hour_count-complete_hour_count
   or out_of_window_hour_count<>expected_day_hour_count-release_hour_count
   or is_complete_weather_day is distinct from
      (is_full_day_in_release and complete_hour_count=expected_day_hour_count and present_hour_count=expected_day_hour_count)
   or (temperature_c is not null) is distinct from is_complete_weather_day or is_imputed
