"""Known revision precedence, absence accounting and release-plan controls."""

import unittest
from decimal import Decimal
from datetime import timedelta, timezone

from ingestion.fmi import utc_time
from ingestion.publication import content_hash, merge_layers, validate_plan


def plan():
    return {"version":"0.1","scope":"FMI source-resolution weather points only","stream_id":"synthetic-weather",
            "station_id":"100971","parameter_id":"t2m","unit":"degC","timestep_minutes":10,
            "policy":"explicit_layers_no_implicit_deletion","start_utc":"2025-01-01T00:00:00Z",
            "end_utc_exclusive":"2025-01-01T01:00:00Z","publication_reason":"Manufactured test",
            "layers":[{"name":"base","mode":"base","reason":"Frozen synthetic source","snapshots":["a"*64]}]}


class PublicationTests(unittest.TestCase):
    def test_conflicting_same_layer_values_fail(self):
        t=utc_time("2025-01-01T00:00:00Z")
        with self.assertRaisesRegex(ValueError,"Conflicting"):
            merge_layers([[(t,Decimal(1),"observed","a",1),(t,Decimal(2),"observed","b",1)]],plan()["start_utc"],plan()["end_utc_exclusive"])

    def test_equal_overlaps_deduplicate_with_deterministic_first_lineage(self):
        t=utc_time("2025-01-01T00:00:00Z")
        points,_=merge_layers([[(t,Decimal("1.0"),"observed","a",1),(t,Decimal("1.00"),"observed","b",2)]],plan()["start_utc"],plan()["end_utc_exclusive"])
        self.assertEqual(points[0],(t,Decimal("1.0"),"observed","a",1))
        self.assertEqual(len(points),6)

    def test_declared_correction_overrides_only_present_keys(self):
        a,b=utc_time("2025-01-01T00:00:00Z"),utc_time("2025-01-01T00:10:00Z")
        points,overlay=merge_layers([[(a,Decimal(1),"observed","base",1),(b,None,"source_nan","base",2)],[(a,Decimal(2),"observed","fix",1)]],plan()["start_utc"],plan()["end_utc_exclusive"])
        self.assertEqual(points[0][1],Decimal(2))
        self.assertEqual(points[1][2],"source_nan")
        self.assertEqual(overlay,{a})

    def test_backfill_preserves_prior_keys_and_distinguishes_absent_from_nan(self):
        a,b=utc_time("2025-01-01T00:00:00Z"),utc_time("2025-01-01T00:10:00Z")
        points,_=merge_layers([[(a,None,"source_nan","base",1)],[(b,Decimal(3),"observed","fill",1)]],plan()["start_utc"],plan()["end_utc_exclusive"])
        self.assertEqual([p[2] for p in points],["source_nan","observed",*(["source_absent"]*4)])
        self.assertEqual(points[2][3:],(None,None))

    def test_content_hash_compares_values_not_source_locator_or_decimal_scale(self):
        t=utc_time("2025-01-01T00:00:00Z")
        a=[(t,Decimal("1.00"),"observed","a",1)]
        b=[(t,Decimal("1"),"observed","b",9)]
        self.assertEqual(content_hash(a),content_hash(b))
        self.assertNotEqual(content_hash(a),content_hash([(t,None,"source_nan","a",1)]))

    def test_equal_instants_hash_identically_in_different_session_timezones(self):
        t=utc_time("2025-01-01T00:00:00Z")
        local=t.astimezone(timezone(timedelta(hours=2)))
        self.assertEqual(content_hash([(t,Decimal(1),"observed","a",1)]),content_hash([(local,Decimal(1),"observed","a",1)]))

    def test_precedence_reason_and_layer_mode_are_required(self):
        p=plan()
        p["layers"].append({"name":"fix","mode":"correction","reason":"","snapshots":["b"*64]})
        with self.assertRaisesRegex(ValueError,"precedence reason"):
            validate_plan(p)
        p["layers"][1]["reason"]="Declared synthetic correction"
        p["layers"][1]["mode"]="newest_download"
        with self.assertRaisesRegex(ValueError,"precedence"):
            validate_plan(p)

    def test_duplicate_snapshot_and_unbounded_window_fail(self):
        p=plan()
        p["layers"][0]["snapshots"]*=2
        with self.assertRaisesRegex(ValueError,"unique"):
            validate_plan(p)
        p=plan()
        p["end_utc_exclusive"]="2030-01-01T00:00:00Z"
        with self.assertRaises(ValueError):
            validate_plan(p)

    def test_off_grid_key_is_not_silently_published(self):
        t=utc_time("2025-01-01T00:05:00Z")
        with self.assertRaisesRegex(ValueError,"off grid"):
            merge_layers([[(t,Decimal(1),"observed","a",1)]],plan()["start_utc"],plan()["end_utc_exclusive"])
