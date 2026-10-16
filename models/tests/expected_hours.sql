select r.release_id
from {{ ref('stg_weather_release') }} r
left join {{ ref('fct_weather_hour') }} h using (release_id)
group by r.release_id, r.start_utc, r.end_utc_exclusive
having count(h.hour_start_utc) <> extract(epoch from (r.end_utc_exclusive-r.start_utc))/3600
    or min(h.hour_start_utc) <> r.start_utc
    or max(h.hour_end_utc) <> r.end_utc_exclusive
