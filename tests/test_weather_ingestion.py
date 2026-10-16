"""Known source-resolution weather semantics and bounded timeout behavior."""

import json
import socket
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from ingestion.fmi import download, request_parameters
from ingestion.provenance import load_configuration
from ingestion.weather import typed_points, weather_settings
from test_source_audit import weather_xml


class WeatherPointTests(unittest.TestCase):
    def setUp(self):
        self.parameters = request_parameters("2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z", station="100971", timestep=10)

    def parse(self, points, **kwargs):
        return typed_points(weather_xml(points, **kwargs), self.parameters, ["100971"])

    def test_decimal_precision_original_text_and_observation_time_are_retained(self):
        value = "-1.1234567890123456789"
        result = self.parse([("2025-01-01T00:00:00Z", value)])
        row = result["rows"][0]
        self.assertEqual(row[2].isoformat(), "2025-01-01T00:00:00+00:00")
        self.assertEqual(row[3], Decimal(value))
        self.assertEqual((row[4], row[5], row[6]), (value, 1, "observed"))

    def test_nan_and_absent_keys_have_separate_accounting(self):
        result = self.parse([("2025-01-01T00:00:00Z", "-1"), ("2025-01-01T00:20:00Z", "NaN")])
        coverage = result["inspection"]["coverage_by_station"]["100971"]
        self.assertEqual((coverage["expected_samples"],coverage["valid_samples"],coverage["missing_value_samples"],coverage["absent_samples"]), (6,1,1,4))
        self.assertEqual(result["rows"][1][3:], (None,"NaN",2,"source_nan"))

    def test_endpoint_exclusion_keeps_original_point_locator(self):
        result = self.parse([("2025-01-01T01:00:00Z", "2"), ("2025-01-01T00:00:00Z", "-1")])
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0][5], 2)
        self.assertEqual(result["inspection"]["out_of_scope_points"], 1)

    def test_duplicates_off_grid_and_wrong_station_fail(self):
        variants = [([("2025-01-01T00:00:00Z", "1")]*2, {}),
                    ([("2025-01-01T00:05:00Z", "1")], {}),
                    ([("2025-01-01T00:00:00Z", "1")], {"station":"100968"})]
        for points, kwargs in variants:
            with self.subTest(points=points,kwargs=kwargs), self.assertRaises(ValueError):
                self.parse(points,**kwargs)

    def test_non_utc_source_time_and_infinite_values_fail(self):
        for timestamp,value in [("2025-01-01T00:00:00+03:00","1"), ("2025-01-01T00:00:00Z","Infinity")]:
            with self.subTest(timestamp=timestamp,value=value), self.assertRaises(ValueError):
                self.parse([(timestamp,value)])

    def test_hourly_request_cannot_silently_replace_ten_minute_contract(self):
        parameters = {**self.parameters,"timestep":"60"}
        with self.assertRaisesRegex(ValueError,"ten-minute contract"):
            typed_points(weather_xml(),parameters,["100971"])

    def test_contract_requires_compatible_source_semantics(self):
        root = Path.cwd().resolve()
        foundation = load_configuration(root,"FMI",Path("config/foundation.json"))
        settings = weather_settings(root,foundation)
        self.assertFalse(settings["weather_contract"]["paired_heating_acceptance"])
        foundation["contract"]["unit"] = "K"
        with self.assertRaisesRegex(ValueError,"baseline semantics"):
            weather_settings(root,foundation)

    def test_timeout_retries_stop_at_three_attempts(self):
        with patch("ingestion.fmi.urllib.request.urlopen",side_effect=socket.timeout) as opener, patch("ingestion.fmi.time.sleep") as sleep:
            with self.assertRaisesRegex(ValueError,"3 attempt"):
                download(self.parameters)
        self.assertEqual(opener.call_count,3)
        self.assertTrue(all(call.kwargs["timeout"] == 20 for call in opener.call_args_list))
        self.assertEqual([call.args[0] for call in sleep.call_args_list],[1,2])
