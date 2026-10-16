with selected as (select * from {{ ref('stg_weather_release') }})
select 'selection_must_contain_one_release' as failure where (select count(*) from selected) <> 1
union all
select 'release_bounds_or_parameter_invalid' from selected
where start_utc is null or end_utc_exclusive is null
   or end_utc_exclusive <= start_utc or parameter_id is distinct from 't2m'
   or extract(epoch from start_utc) % 3600 <> 0 or extract(epoch from end_utc_exclusive) % 3600 <> 0
   or end_utc_exclusive - start_utc > interval '732 days'
