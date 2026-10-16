"""Independent ZoneInfo/Decimal oracle for the candidate SQL calendar and reports."""

from collections import Counter, defaultdict
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo


def expected_calendar(start, end):
    """UTC spine plus full Helsinki civil-day bounds, including partial edge days."""
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError('An increasing aware time window is required')
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if any(t.minute or t.second or t.microsecond for t in (start, end)):
        raise ValueError('Whole UTC hour boundaries are required')
    helsinki = ZoneInfo('Europe/Helsinki')
    hours = {}
    days = {}
    cursor = start
    while cursor < end:
        local = cursor.astimezone(helsinki)
        date = local.date()
        hours[cursor] = (local.replace(tzinfo=None), date, local.hour,
                         int(local.utcoffset().total_seconds() // 60), local.fold)
        if date not in days:
            a = datetime.combine(date, time(), helsinki).astimezone(timezone.utc)
            b = datetime.combine(date + timedelta(days=1), time(), helsinki).astimezone(timezone.utc)
            iso = date.isocalendar()
            days[date] = (a, b, date.year, date.month, date.day, iso.year, iso.week,
                          iso.weekday, iso.weekday >= 6, int((b-a).total_seconds() // 3600),
                          int((min(b,end)-max(a,start)).total_seconds() // 3600), start <= a and end >= b)
        cursor += timedelta(hours=1)
    return hours, days


def verify_time_models(connection, start, end):
    hours, days = expected_calendar(start,end)
    actual_hours = dict((r[0],r[1:]) for r in connection.execute('''SELECT hour_start_utc,
        local_hour_start,local_date,local_hour,utc_offset_minutes,local_fold
        FROM dbt_weather.dim_hour''').fetchall())
    assert actual_hours == hours, 'SQL UTC/Helsinki labels differ from ZoneInfo'
    actual_days = dict((r[0],r[1:]) for r in connection.execute('''SELECT local_date,
        day_start_utc,day_end_utc,calendar_year,calendar_month,day_of_month,iso_year,iso_week,
        iso_weekday,is_weekend,expected_day_hour_count,release_hour_count,is_full_day_in_release
        FROM dbt_weather.dim_date''').fetchall())
    assert actual_days == days, 'SQL calendar/coverage differs from independent civil-day bounds'
    facts = connection.execute('''SELECT hour_start_utc,temperature_c,is_complete,
        source_nan_count,source_absent_count,missing_published_slot_count FROM dbt_weather.fct_weather_hour''').fetchall()
    reports = connection.execute('''SELECT hour_start_utc,temperature_c,is_complete,
        source_nan_count,source_absent_count,missing_published_slot_count FROM dbt_weather.weather_report_hour''').fetchall()
    assert sorted(facts) == sorted(reports) and len(facts) == len(hours), 'Reporting join lost or multiplied facts'
    grouped = defaultdict(list)
    for r in facts:
        grouped[hours[r[0]][1]].append(r)
    daily = connection.execute('''SELECT local_date,expected_day_hour_count,release_hour_count,
        present_hour_count,complete_hour_count,out_of_window_hour_count,missing_model_hour_count,
        incomplete_hour_count,source_nan_count,source_absent_count,missing_published_slot_count,
        is_full_day_in_release,is_complete_weather_day,temperature_c,is_imputed
        FROM dbt_weather.weather_report_day''').fetchall()
    assert len(daily) == len(days) and {r[0] for r in daily} == set(days)
    complete_days = 0
    for row in daily:
        date = row[0]; values = grouped[date]; calendar = days[date]
        expected, covered, full = calendar[-3:]
        complete = sum(r[2] for r in values)
        eligible = full and len(values) == expected and complete == expected
        counts = (expected,covered,len(values),complete,expected-covered,covered-len(values),
                  len(values)-complete,*[sum(r[i] for r in values) for i in (3,4,5)],full,eligible)
        assert row[1:13] == counts, 'Daily counts/eligibility differ from independent hour groups'
        mean = sum(r[1] for r in values)/Decimal(expected) if eligible else None
        assert (row[13] is None) == (mean is None) and row[14] is False
        if mean is not None:
            assert abs(row[13]-mean) <= Decimal('1e-12'), 'Daily mean differs'
        complete_days += eligible
    return {'hour_labels':len(hours),'local_dates':len(days),'complete_weather_days':complete_days,
            'day_lengths':dict(sorted(Counter(r[-3] for r in days.values()).items())),
            'partial_days':sum(not r[-1] for r in days.values()),
            'repeated_second_hours':sum(r[-1] for r in hours.values())}
