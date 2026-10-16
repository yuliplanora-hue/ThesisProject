import hashlib
import unittest
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from ingestion.fmi import utc_time
from ingestion.period_audit import plan_chunks, summarize_period, verify_cached_manifest


class PeriodAuditTests(unittest.TestCase):
    def test_two_year_chunks_are_contiguous_bounded_and_exclusive(self):
        chunks = plan_chunks("2023-12-31T22:00:00Z", "2025-12-31T22:00:00Z")
        self.assertEqual(len(chunks), 105)
        for i, (start, end) in enumerate(chunks):
            self.assertLessEqual(utc_time(end) - utc_time(start), timedelta(days=7))
            if i:
                self.assertEqual(start, chunks[i - 1][1])
        self.assertEqual(sum((utc_time(end) - utc_time(start)).total_seconds() / 3600 for start, end in chunks), 17544)

    def test_missing_and_nonfinite_samples_reconcile_separately(self):
        start = "2025-01-01T00:00:00Z"
        points = {utc_time(start) + timedelta(minutes=10 * i): float(i) for i in range(6)}
        points.pop(utc_time(start) + timedelta(minutes=10))
        points[utc_time(start) + timedelta(minutes=20)] = None
        report = summarize_period(points, start, "2025-01-01T01:00:00Z")
        self.assertEqual((report["valid_samples"], report["absent_samples"], report["nonfinite_samples"]), (4, 1, 1))
        self.assertEqual(report["complete_six_sample_hours"], 0)
        self.assertTrue(report["accounting_reconciles"])

    def test_both_dst_days_keep_expected_samples_and_local_day_identity(self):
        for start, end, hours in [("2024-03-30T22:00:00Z", "2024-03-31T21:00:00Z", 23),
                                  ("2024-10-26T21:00:00Z", "2024-10-27T22:00:00Z", 25)]:
            first = utc_time(start)
            points = {first + timedelta(minutes=10 * i): 1.0 for i in range(hours * 6)}
            result = summarize_period(points, start, end)
            self.assertEqual((result["expected_local_days"], result["complete_local_days"]), (1, 1))
            self.assertEqual(result["days_by_expected_hours"], {str(hours): 1})

    def test_off_grid_or_out_of_period_points_fail(self):
        for timestamp in ("2025-01-01T00:05:00Z", "2025-01-01T01:00:00Z"):
            with self.assertRaisesRegex(ValueError, "sample grid"):
                summarize_period({utc_time(timestamp): 1.0}, "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z")

    def test_partial_local_day_is_not_counted_as_complete_calendar_day(self):
        first = utc_time("2025-01-01T00:00:00Z")
        points = {first + timedelta(minutes=10 * i): 1.0 for i in range(6)}
        result = summarize_period(points, first.isoformat(), "2025-01-01T01:00:00Z")
        self.assertEqual(result["complete_six_sample_hours"], 1)
        self.assertEqual(result["complete_local_days"], 0)
        self.assertEqual(result["partial_local_days"], 1)

    def test_unbounded_and_reversed_periods_fail(self):
        for end in ("2025-01-01T00:00:00Z", "2030-01-01T00:00:00Z"):
            with self.assertRaises(ValueError):
                plan_chunks("2025-01-01T00:00:00Z", end)

    def test_cached_response_checks_request_and_content_identity(self):
        payload = b"synthetic raw response"
        digest = hashlib.sha256(payload).hexdigest()
        parameters = {"station": "synthetic"}
        manifest = {"status": "inspected", "parameters": parameters, "response_sha256": digest}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / (digest + ".xml")
            path.write_bytes(payload)
            self.assertEqual(verify_cached_manifest(manifest, root, parameters), payload)
            with self.assertRaises(ValueError):
                verify_cached_manifest(manifest, root, {"station": "changed"})
            path.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify_cached_manifest(manifest, root, parameters)
