select release_id, stream_id, station_id, parameter_id, start_utc, end_utc_exclusive,
       content_sha256, plan_sha256
from {{ source('accepted_weather', 'weather_release') }}
where release_id = {{ selected_weather_release() }}
