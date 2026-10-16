select release_id, hour_start_utc from {{ ref('fct_weather_hour') }}
where expected_sample_count <> 6 or published_slot_count <> 6 or missing_published_slot_count <> 0
   or finite_sample_count + source_nan_count + source_absent_count <> 6
   or finite_sample_count not between 0 and 6
   or is_imputed
   or (is_complete and (temperature_c is null or finite_sample_count <> 6))
   or (not is_complete and temperature_c is not null)
