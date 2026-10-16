"""Role-name safety and opt-in connection role handling; database ACLs have integration checks."""

import os
import unittest
from unittest.mock import Mock, patch

from ingestion.database import connect
from ingestion.permissions import provision_roles, role_name


class PermissionTests(unittest.TestCase):
    def test_unsafe_reserved_and_overlong_names_rejected(self):
        for name in (None, "", "public", "pg_read_all_data", "energy;drop", "ENERGY", "x"*64):
            with self.subTest(name=name), self.assertRaises(ValueError):
                role_name(name)
        self.assertEqual(role_name("energy_reporter"), "energy_reporter")

    def test_loader_and_reporter_cannot_share_one_role(self):
        connection = Mock()
        with self.assertRaises(ValueError):
            provision_roles(connection, "energy_same", "energy_same")
        connection.execute.assert_not_called()

    def test_failed_role_switch_closes_connection_and_preserves_error(self):
        connection = Mock()
        connection.execute.side_effect = ValueError("role switch denied")
        with patch.dict(os.environ, {"ENERGY_DB_ROLE": "energy_reporter"}):
            with patch("ingestion.database.connection_settings", return_value={}), patch("ingestion.database.psycopg.connect", return_value=connection):
                with self.assertRaisesRegex(ValueError, "role switch denied"):
                    connect()
        connection.close.assert_called_once()

    def test_connection_switch_is_explicit_and_optional(self):
        connection = Mock()
        with patch.dict(os.environ, {"ENERGY_DB_ROLE": ""}):
            with patch("ingestion.database.connection_settings", return_value={}), patch("ingestion.database.psycopg.connect", return_value=connection):
                self.assertIs(connect(), connection)
        connection.execute.assert_not_called()
