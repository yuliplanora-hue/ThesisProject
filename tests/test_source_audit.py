"""Synthetic source-contract tests; no private data, database or network needed."""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from ingestion.audit import audit_helen
from ingestion.fmi import acquire_sample, download, inspect_response, request_parameters, utc_time


def weather_xml(points=None, station="100971", parameter="t2m"):
    points = points if points is not None else [("2025-01-01T00:00:00Z", "-1.0"),
                                               ("2025-01-01T01:00:00Z", "2.0")]
    measurements = "".join(f"<w:MeasurementTVP><w:time>{t}</w:time><w:value>{v}</w:value></w:MeasurementTVP>"
                           for t, v in points)
    return f'''<f:FeatureCollection xmlns:f="http://www.opengis.net/wfs/2.0"
       xmlns:t="http://xml.fmi.fi/namespace/om/atmosphericfeatures/1.1"
       xmlns:g="http://www.opengis.net/gml/3.2" xmlns:o="http://www.opengis.net/om/2.0"
       xmlns:w="http://www.opengis.net/waterml/2.0" xmlns:x="http://www.w3.org/1999/xlink">
       <f:member><o:Observation><o:observedProperty x:href="https://opendata.fmi.fi/meta?param={parameter}"/>
       <t:Location><g:identifier codeSpace="http://xml.fmi.fi/namespace/stationcode/fmisid">{station}</g:identifier>
       <g:name codeSpace="http://xml.fmi.fi/namespace/locationcode/name">Synthetic station</g:name></t:Location>
       <g:Point><g:pos>60.0 25.0</g:pos></g:Point><w:MeasurementTimeseries>{measurements}</w:MeasurementTimeseries>
       </o:Observation></f:member></f:FeatureCollection>'''.encode()


class HelenAuditTests(unittest.TestCase):
    def audit(self, rows, header="datetime_utc;dh_MWh"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.csv"
            path.write_text(header + "\n" + rows, encoding="utf-8-sig")
            return audit_helen(path)

    def test_day_first_decimal_precision_and_no_semantics_inferred(self):
        result = self.audit("02.01.2025 00:00;10,1234567890123456789\n02.01.2025 01:00;20,5\n")
        self.assertEqual(result["minimum_timestamp_as_written"], "2025-01-02T00:00:00")
        self.assertEqual(result["minimum_measurement_as_written"], "10.1234567890123456789")
        self.assertEqual(result["written_clock_coverage"]["missing_keys"], 0)
        self.assertFalse(result["analytical_use_approved"])

    def test_each_bad_row_accounted_and_reasons_can_overlap(self):
        result = self.audit("31.02.2025 00:00;bad\n02.01.2025 00:00;NaN\n02.01.2025 01:00;10,0\n")
        self.assertEqual((result["rows"], result["parsable_rows"], result["rejected_rows"]), (3, 1, 2))
        self.assertEqual(result["rejection_counts"], {"invalid_timestamp": 1, "invalid_measurement": 2})

    def test_unsupported_numeric_formats_rejected(self):
        for value in ("1.2", "1e3", "Infinity", " 10,0"):
            with self.subTest(value=value):
                self.assertEqual(self.audit(f"02.01.2025 00:00;{value}\n")["rejected_rows"], 1)

    def test_unknown_or_duplicate_columns_fail(self):
        for header in ("datetime_utc;dh_MWh;extra", "datetime_utc;datetime_utc"):
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "schema mismatch"):
                self.audit("", header)

    def test_extra_record_field_is_rejected(self):
        result = self.audit("02.01.2025 00:00;10,0;unexpected\n")
        self.assertEqual(result["rejection_counts"], {"wrong_field_count": 1})

    def test_missing_and_conflicting_keys_are_not_hidden(self):
        result = self.audit("02.01.2025 00:00;10,0\n02.01.2025 00:00;11,0\n02.01.2025 02:00;12,0\n")
        self.assertEqual(result["duplicate_timestamp_rows"], 1)
        self.assertEqual(result["conflicting_timestamp_keys"], 1)
        self.assertEqual(result["written_clock_coverage"]["missing_keys"], 1)

    def test_off_hour_blocks_hourly_completeness_claim(self):
        result = self.audit("02.01.2025 00:30;10,0\n")
        self.assertEqual(result["off_hour_rows"], 1)
        self.assertIsNone(result["written_clock_coverage"])

    def test_empty_input_has_no_invented_coverage(self):
        result = self.audit("")
        self.assertEqual(result["rows"], 0)
        self.assertIsNone(result["written_clock_coverage"])

    def test_leap_day_and_reverse_order(self):
        result = self.audit("01.03.2024 00:00;10,0\n29.02.2024 23:00;9,0\n")
        self.assertEqual(result["descending_timestamp_steps"], 1)
        self.assertEqual(result["written_clock_coverage"]["missing_keys"], 0)


class FMIResponseTests(unittest.TestCase):
    def inspect(self, payload, **kwargs):
        return inspect_response(payload, "2025-01-01T00:00:00Z", "2025-01-01T02:00:00Z", **kwargs)

    def test_inclusive_api_endpoint_excluded_from_project_scope(self):
        payload = weather_xml([(f"2025-01-01T0{h}:00:00Z", str(h)) for h in range(3)])
        result = self.inspect(payload, station="100971")
        self.assertEqual(result["point_rows_in_scope"], 2)
        self.assertEqual(result["out_of_scope_points"], 1)
        self.assertEqual(result["coverage_by_station"]["100971"]["valid_samples"], 2)

    def test_missing_temperature_is_not_zero_or_absent_timestamp(self):
        result = self.inspect(weather_xml([("2025-01-01T00:00:00Z", "NaN")]))
        self.assertEqual(result["coverage_by_station"]["100971"],
                         {"expected_samples": 2, "returned_distinct_samples": 1, "valid_samples": 0,
                          "absent_samples": 1, "missing_value_samples": 1})

    def test_duplicate_key_reported(self):
        result = self.inspect(weather_xml([("2025-01-01T00:00:00Z", "1"), ("2025-01-01T00:00:00Z", "2")]))
        self.assertEqual(result["duplicate_key_rows"], 1)

    def test_wrong_station_and_parameter_fail(self):
        with self.assertRaisesRegex(ValueError, "station"):
            self.inspect(weather_xml(station="999"), station="100971")
        with self.assertRaisesRegex(ValueError, "parameter"):
            self.inspect(weather_xml(parameter="wind"))

    def test_ambiguous_location_cannot_misassign_points(self):
        payload = weather_xml().replace(b"</t:Location>", b"</t:Location><t:Location/>")
        with self.assertRaisesRegex(ValueError, "ambiguous FMI location"):
            self.inspect(payload)

    def test_exception_empty_collection_and_malformed_xml_fail(self):
        for payload in (b"<ExceptionReport/>", b"<broken", b'<FeatureCollection xmlns="http://www.opengis.net/wfs/2.0"/>'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.inspect(payload)

    def test_xml_entity_declarations_fail(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.inspect(b'<!DOCTYPE x [<!ENTITY a "x">]><x/>')

    def test_off_grid_observation_fails(self):
        with self.assertRaisesRegex(ValueError, "time grid"):
            self.inspect(weather_xml([("2025-01-01T00:10:00Z", "1")]))

    def test_invalid_boundaries_selector_and_unbounded_queries_fail(self):
        with self.assertRaises(ValueError):
            utc_time("2025-01-01T00:00:00")
        for end in ("2025-01-01T00:00:00Z", "2025-02-01T00:00:00Z"):
            with self.assertRaises(ValueError):
                request_parameters("2025-01-01T00:00:00Z", end, station="100971")
        with self.assertRaises(ValueError):
            request_parameters("2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z", station="100971", place="helsinki")

    def test_hash_ignores_response_envelope_and_point_order(self):
        points = [("2025-01-01T00:00:00Z", "-1"), ("2025-01-01T01:00:00Z", "2")]
        self.assertEqual(self.inspect(weather_xml(points))["keyed_observation_sha256"],
                         self.inspect(weather_xml(list(reversed(points))))["keyed_observation_sha256"])


class FMIAcquisitionTests(unittest.TestCase):
    def test_retry_transient_failure_and_bounded_exhaustion(self):
        transient = urllib.error.HTTPError("https://opendata.fmi.fi/wfs", 503, "temporary", {}, None)
        class Response(io.BytesIO):
            status = 200
            headers = {"Content-Type": "text/xml"}
        with patch("ingestion.fmi.urllib.request.urlopen", side_effect=[transient, Response(b"ok")]) as opener, \
             patch("ingestion.fmi.time.sleep"):
            body, metadata = download({"request": "GetFeature"})
            self.assertEqual(body, b"ok")
            self.assertEqual(metadata["attempts"], 2)
            self.assertEqual(opener.call_count, 2)
        with patch("ingestion.fmi.urllib.request.urlopen", side_effect=transient) as opener, \
             patch("ingestion.fmi.time.sleep"), self.assertRaisesRegex(ValueError, "3 attempt"):
            download({"request": "GetFeature"})
        self.assertEqual(opener.call_count, 3)

    def test_nontransient_failure_not_retried(self):
        error = urllib.error.HTTPError("https://opendata.fmi.fi/wfs", 400, "bad query", {}, None)
        with patch("ingestion.fmi.urllib.request.urlopen", side_effect=error) as opener, \
             self.assertRaisesRegex(ValueError, "HTTP 400"):
            download({"request": "GetFeature"})
        self.assertEqual(opener.call_count, 1)

    def test_oversized_response_rejected_without_retry(self):
        class Response(io.BytesIO):
            status = 200
            headers = {}
        with patch("ingestion.fmi.urllib.request.urlopen", return_value=Response(b"x" * 2_000_001)) as opener, \
             self.assertRaisesRegex(ValueError, "size limit"):
            download({"request": "GetFeature"})
        self.assertEqual(opener.call_count, 1)

    def test_snapshots_reused_and_each_attempt_gets_manifest(self):
        params = request_parameters("2025-01-01T00:00:00Z", "2025-01-01T02:00:00Z", station="100971")
        with tempfile.TemporaryDirectory() as directory, \
             patch("ingestion.fmi.download", return_value=(weather_xml(), {"http_status": 200})):
            raw, manifests = Path(directory) / "raw", Path(directory) / "manifests"
            first, _ = acquire_sample(params, raw, manifests)
            second, _ = acquire_sample(params, raw, manifests)
            self.assertEqual(first["response_sha256"], second["response_sha256"])
            self.assertEqual(len(list(raw.glob("*.xml"))), 1)
            self.assertEqual(len(list(manifests.glob("*.json"))), 2)

    def test_failed_inspection_preserves_input_and_failure_record(self):
        params = request_parameters("2025-01-01T00:00:00Z", "2025-01-01T02:00:00Z", station="100971")
        with tempfile.TemporaryDirectory() as directory, \
             patch("ingestion.fmi.download", return_value=(b"<ExceptionReport/>", {"http_status": 200})):
            raw, manifests = Path(directory) / "raw", Path(directory) / "manifests"
            with self.assertRaises(ValueError):
                acquire_sample(params, raw, manifests)
            record = json.loads(next(manifests.glob("*.json")).read_text())
            self.assertEqual(record["status"], "inspection_failed")
            self.assertEqual(len(list(raw.glob("*.xml"))), 1)


if __name__ == "__main__":
    unittest.main()
