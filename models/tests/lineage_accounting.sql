with delta as (
    (select release_id, observed_at_utc, station_id, parameter_id, snapshot_id, source_point_index, source_quality
     from {{ ref('stg_weather_point') }}
     except all
     select release_id, observed_at_utc, station_id, parameter_id, snapshot_id, source_point_index, source_quality
     from {{ ref('weather_hour_lineage') }})
    union all
    (select release_id, observed_at_utc, station_id, parameter_id, snapshot_id, source_point_index, source_quality
     from {{ ref('weather_hour_lineage') }}
     except all
     select release_id, observed_at_utc, station_id, parameter_id, snapshot_id, source_point_index, source_quality
     from {{ ref('stg_weather_point') }})
)
select * from delta
