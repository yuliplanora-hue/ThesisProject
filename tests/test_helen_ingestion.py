"""Helen source-value intake controls, independent of physical interpretation."""

import unittest
from datetime import timedelta
from decimal import Decimal

from ingestion.helen import parse_records


class HelenIntakeTests(unittest.TestCase):
    def parse(self, rows):
        return parse_records(("datetime_utc;dh_MWh\n"+rows).encode("utf-8"))

    def test_decimal_and_raw_lineage_are_exact(self):
        record=self.parse("01.01.2025 10:00;123,45600\n")[0]
        self.assertEqual(record["measurement"],Decimal("123.45600"))
        self.assertEqual(record["fields"],["01.01.2025 10:00","123,45600"])
        self.assertEqual((record["index"],record["line_end"],record["status"]),(1,2,"valid"))
        self.assertEqual(record["label"]-record["start"],timedelta(hours=1))
        self.assertEqual(record["label"].utcoffset(),timedelta(0))

    def test_every_invalid_record_is_accounted_for(self):
        rows=self.parse("bad;NaN\n01.01.2025 01:30;1,5\n01.01.2025 02:00;2;extra\n\n")
        self.assertEqual(len(rows),4)
        self.assertTrue(all(r["status"]=="quarantined" for r in rows))
        self.assertEqual(rows[0]["reasons"],["invalid_timestamp","invalid_measurement"])
        self.assertIn("off_hour",rows[1]["reasons"])
        self.assertIn("wrong_field_count",rows[2]["reasons"])

    def test_all_duplicate_labels_are_quarantined_even_if_equal(self):
        for value in ("1","2"):
            rows=self.parse(f"01.01.2025 00:00;1\n01.01.2025 00:00;{value}\n")
            self.assertEqual([r["reasons"] for r in rows],[["duplicate_label"],["duplicate_label"]])

    def test_negative_measurement_is_not_silently_deleted_or_converted(self):
        record=self.parse("01.01.2025 00:00;-1,25\n")[0]
        self.assertEqual((record["status"],record["measurement"]),("valid",Decimal("-1.25")))
        self.assertEqual(record["warnings"],["negative_source_value"])

    def test_dst_transition_utc_labels_keep_distinct_intervals(self):
        for date in ("30.03.2025","26.10.2025"):
            rows=self.parse(f"{date} 00:00;1\n{date} 01:00;2\n{date} 02:00;3\n")
            self.assertTrue(all(r["status"]=="valid" for r in rows))
            self.assertEqual(rows[2]["label"]-rows[0]["label"],timedelta(hours=2))

    def test_schema_numeric_lexemes_and_record_bound_are_strict(self):
        with self.assertRaises(ValueError): parse_records(b"time,value\n")
        with self.assertRaises(ValueError): parse_records(b"datetime_utc;dh_MWh\n01.01.2025 00:00;1\n",maximum_records=0)
        for value in ("1.2","1e3","NaN","inf"," 1","1 "):
            self.assertIn("invalid_measurement",self.parse(f"01.01.2025 00:00;{value}\n")[0]["reasons"])

    def test_bom_and_quoted_csv_fields_preserve_values(self):
        rows=parse_records(b'\xef\xbb\xbfdatetime_utc;dh_MWh\r\n"01.01.2025 00:00";"1,50"\r\n')
        self.assertEqual(rows[0]["measurement"],Decimal("1.50"))
