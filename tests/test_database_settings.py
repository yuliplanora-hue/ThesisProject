import tempfile
import unittest
from pathlib import Path

from ingestion.database import connection_settings


class DatabaseSettingsTests(unittest.TestCase):
    def test_missing_or_placeholder_password_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            with self.assertRaises(ValueError):
                connection_settings(path, {})
            path.write_text("POSTGRES_PASSWORD=replace_with_a_local_password\n")
            with self.assertRaises(ValueError):
                connection_settings(path, {})

    def test_environment_overrides_local_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("POSTGRES_PASSWORD='synthetic_file_value'\n")
            self.assertEqual(connection_settings(path, {})["password"], "synthetic_file_value")
            settings = connection_settings(path, {"POSTGRES_PASSWORD": "synthetic_env_value", "ENERGY_DB_PORT": "5433"})
            self.assertEqual((settings["password"], settings["port"]), ("synthetic_env_value", 5433))

    def test_invalid_port_does_not_echo_input_or_password(self):
        for port in ("not_a_port", "0", "65536"):
            with self.subTest(port=port), self.assertRaisesRegex(ValueError, "valid port number") as context:
                connection_settings(environment={"POSTGRES_PASSWORD": "synthetic_secret", "ENERGY_DB_PORT": port})
            self.assertNotIn("synthetic_secret", str(context.exception))
            self.assertNotIn(port, str(context.exception))
