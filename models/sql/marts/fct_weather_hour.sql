select release_id, station_id, parameter_id, hour_start_utc,
       hour_start_utc + interval '1 hour' as hour_end_utc,
       temperature_c, expected_sample_count, published_slot_count, finite_sample_count,
       source_nan_count, source_absent_count, missing_published_slot_count,
       (finite_sample_count = 6 and published_slot_count = 6) as is_complete,
       false as is_imputed
from {{ ref('int_weather_hour') }}
