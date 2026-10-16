select stream_id, release_id, station_id, parameter_id, observed_at_utc,
       temperature_c, source_quality, snapshot_id, source_point_index
from {{ source('accepted_weather', 'weather_point') }}
where release_id = {{ selected_weather_release() }}
