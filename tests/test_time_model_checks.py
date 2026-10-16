import unittest
from datetime import datetime, timezone

from tools.time_model_checks import expected_calendar


class CalendarReferenceTests(unittest.TestCase):
    def test_spring_skips_three_and_has_23_elapsed_hours(self):
        hours,days=expected_calendar(datetime(2025,3,29,22,tzinfo=timezone.utc),datetime(2025,3,30,21,tzinfo=timezone.utc))
        self.assertEqual(len(hours),23)
        self.assertNotIn(3,[r[2] for r in hours.values()])
        self.assertEqual(next(iter(days.values()))[-3:],(23,23,True))

    def test_fall_repeated_three_has_distinct_offset_and_fold(self):
        hours,days=expected_calendar(datetime(2025,10,25,21,tzinfo=timezone.utc),datetime(2025,10,26,22,tzinfo=timezone.utc))
        repeated=[r for r in hours.values() if r[2]==3]
        self.assertEqual([(r[3],r[4]) for r in repeated],[(180,0),(120,1)])
        self.assertEqual(next(iter(days.values()))[-3:],(25,25,True))

    def test_partial_fall_start_preserves_second_fold(self):
        hours,days=expected_calendar(datetime(2025,10,26,1,tzinfo=timezone.utc),datetime(2025,10,26,3,tzinfo=timezone.utc))
        self.assertEqual(next(iter(hours.values()))[-1],1)
        self.assertEqual(next(iter(days.values()))[-3:],(25,2,False))

    def test_leap_day_and_iso_week_year(self):
        _,days=expected_calendar(datetime(2024,2,28,22,tzinfo=timezone.utc),datetime(2024,2,29,22,tzinfo=timezone.utc))
        self.assertEqual(next(iter(days.values()))[2:9],(2024,2,29,2024,9,4,False))
        _,days=expected_calendar(datetime(2024,12,29,22,tzinfo=timezone.utc),datetime(2024,12,30,22,tzinfo=timezone.utc))
        self.assertEqual(next(iter(days.values()))[5:8],(2025,1,1))

    def test_invalid_windows_fail_before_generating_spine(self):
        with self.assertRaises(ValueError):expected_calendar(datetime(2025,1,1),datetime(2025,1,2))
        with self.assertRaises(ValueError):expected_calendar(datetime(2025,1,1,tzinfo=timezone.utc),datetime(2025,1,1,tzinfo=timezone.utc))
        with self.assertRaises(ValueError):expected_calendar(datetime(2025,1,1,0,1,tzinfo=timezone.utc),datetime(2025,1,2,tzinfo=timezone.utc))
