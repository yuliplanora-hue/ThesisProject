"""Offline provenance validation and command error handling on manufactured files."""

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from ingestion.cli import main
from ingestion.fmi import ENDPOINT, inspect_response, request_parameters
from ingestion.provenance import inspect_manifest, load_configuration
from test_source_audit import weather_xml


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name).resolve()
        self.addCleanup(self.directory.cleanup)
        self.raw = self.root / "data/raw/fmi-feasibility"
        self.raw.mkdir(parents=True)
        self.manifests = self.root / "experiments/source-audit"
        self.manifests.mkdir(parents=True)
        payload = weather_xml()
        self.digest = hashlib.sha256(payload).hexdigest()
        self.snapshot = self.raw / (self.digest + ".xml")
        self.snapshot.write_bytes(payload)
        parameters = request_parameters("2025-01-01T00:00:00Z", "2025-01-01T02:00:00Z", station="100971")
        self.manifest = {"source": "FMI", "status": "inspected", "parameters": parameters,
                         "response_sha256": self.digest, "response_bytes": len(payload),
                         "snapshot_file": self.snapshot.name,
                         "retrieval": {"request_url": ENDPOINT + "?" + urlencode(parameters),
                                       "http_status": 200, "attempts": 1, "retrieved_at_utc": "2026-10-14T12:00:00Z"},
                         "inspection": inspect_response(payload, parameters["starttime"], parameters["endtime"], "100971")}
        self.path = self.manifests / "fixture.json"
        self.settings = {"source": "FMI", "source_id": "FMI_WEATHER", "raw_directory": self.raw}

    def inspect(self):
        self.path.write_text(json.dumps(self.manifest), encoding="utf-8")
        return inspect_manifest(self.root, self.path, self.settings)

    def test_retained_evidence_is_reinspected_and_provenance_extracted(self):
        record = self.inspect()
        self.assertEqual(record["content_sha256"], self.digest)
        self.assertEqual(record["raw_locator"], "data/raw/fmi-feasibility/" + self.snapshot.name)
        self.assertEqual(record["request_parameters"]["fmisid"], "100971")
        self.assertEqual(record["retrieved_at_utc"].isoformat(), "2026-10-14T12:00:00+00:00")
        self.assertNotIn("inspection", record)

    def test_raw_corruption_and_changed_size_are_rejected(self):
        original = self.snapshot.read_bytes()
        self.snapshot.write_bytes(original.replace(b"-1.0", b"-9.0"))
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.inspect()
        self.snapshot.write_bytes(original + b"x")
        with self.assertRaisesRegex(ValueError, "byte count"):
            self.inspect()

    def test_untrusted_inspection_and_failed_status_are_rejected(self):
        self.manifest["inspection"]["point_rows_in_scope"] = 99
        with self.assertRaisesRegex(ValueError, "inspection differs"):
            self.inspect()
        self.manifest["status"] = "inspection_failed"
        with self.assertRaisesRegex(ValueError, "Only inspected"):
            self.inspect()

    def test_url_credentials_and_query_mismatch_are_rejected(self):
        original = self.manifest["retrieval"]["request_url"]
        for url in (original.replace("opendata.fmi.fi", "user:secret@opendata.fmi.fi"),
                    original + "&token=secret", original.replace("fmisid=100971", "fmisid=100968")):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.manifest["retrieval"]["request_url"] = url
                self.inspect()

    def test_paths_outside_evidence_scope_are_rejected(self):
        self.manifest["snapshot_file"] = "../../.env"
        with self.assertRaisesRegex(ValueError, "filename"):
            self.inspect()
        with self.assertRaisesRegex(ValueError, "outside the project"):
            inspect_manifest(self.root, self.root.parent / "external.json", self.settings)
        with self.assertRaisesRegex(ValueError, "under experiments/source-audit"):
            inspect_manifest(self.root, self.root / ".env", self.settings)

    def test_contract_change_changes_configuration_identity(self):
        config = self.root / "config"
        config.mkdir()
        contract = config / "weather.json"
        contract.write_text('{"version":"one"}', encoding="utf-8")
        foundation = config / "foundation.json"
        foundation.write_text(json.dumps({"version": "0.1", "sources": {"FMI": {
            "source_id": "FMI_WEATHER", "raw_directory": "data/raw/fmi-feasibility", "contract": "config/weather.json"}}}), encoding="utf-8")
        first = load_configuration(self.root, "FMI", foundation)
        contract.write_text('{"version":"two"}', encoding="utf-8")
        second = load_configuration(self.root, "FMI", foundation)
        self.assertNotEqual(first["configuration_sha256"], second["configuration_sha256"])

    def test_command_failure_has_nonzero_status_and_no_sensitive_exception_text(self):
        stderr = io.StringIO()
        with patch("ingestion.cli.connect", side_effect=ValueError("password=SECRET_PRIVATE_VALUE")), patch("sys.stderr", stderr):
            result = main(["database", "migrate"])
        self.assertEqual(result, 2)
        self.assertNotIn("SECRET_PRIVATE_VALUE", stderr.getvalue())
        self.assertIn("ValueError", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
