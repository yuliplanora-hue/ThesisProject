"""Independent hand controls for future SQL/DAX checks; no publisher data or API."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.check_wp1_fixtures import DEFAULT_DIRECTORY, verify_suite


class ReferenceFixtureTests(unittest.TestCase):
    def test_all_manual_metric_answers(self):
        result = verify_suite()
        self.assertEqual((result["cases"], result["comparisons"]), (11, 55))

    def test_modified_input_is_rejected_by_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "fixtures"
            shutil.copytree(DEFAULT_DIRECTORY, directory)
            with (directory / "heat.csv").open("a", encoding="utf-8") as stream:
                stream.write("changed fixture\n")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_suite(directory)

    def test_wrong_manual_answer_is_rejected_after_valid_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "fixtures"
            shutil.copytree(DEFAULT_DIRECTORY, directory)
            cases_path = directory / "cases.json"
            fixture = json.loads(cases_path.read_text(encoding="utf-8"))
            fixture["cases"][0]["expected"]["M1"]["energy_mwh"] = "529"
            cases_path.write_text(json.dumps(fixture), encoding="utf-8")
            manifest_path = directory / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["cases.json"] = hashlib.sha256(cases_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numeric mismatch"):
                verify_suite(directory)
