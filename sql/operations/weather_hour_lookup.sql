SELECT hour_start_utc, temperature_c, finite_sample_count, source_nan_count, source_absent_count
FROM dbt_weather.int_weather_hour
WHERE release_id = %(release_id)s AND station_id = %(station_id)s AND parameter_id = %(parameter_id)s
  AND hour_start_utc >= %(start)s AND hour_start_utc < %(end)s
ORDER BY hour_start_utc
