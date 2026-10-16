select f.*, d.local_hour_start, d.local_date, d.local_hour, d.utc_offset_minutes, d.local_fold,
       c.calendar_year, c.calendar_month, c.iso_year, c.iso_week, c.iso_weekday, c.is_weekend
from {{ ref('fct_weather_hour') }} f
left join {{ ref('dim_hour') }} d using (release_id,hour_start_utc)
left join {{ ref('dim_date') }} c using (release_id,local_date)
