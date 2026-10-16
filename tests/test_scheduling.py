"""Bounded execution, fail-stop and secret-safe scheduler controls without PostgreSQL."""

import hashlib
import json
import subprocess
import tempfile
import unittest
import io
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from ingestion.scheduling import execute_release, run_schedule, validate_limits
from test_publication import plan


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "plan.json"
        self.path.write_text(json.dumps(plan()), encoding="utf-8")
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.release_id = str(uuid4())
        self.connection = Mock()
        self.locked = True
        self.head = (self.release_id, self.digest)

        def execute(query, parameters=None):
            value = (self.locked,) if "pg_try_advisory_lock" in query else self.head
            return Mock(fetchone=lambda: value)
        self.connection.execute.side_effect = execute
        self.child = Mock(return_value={"status": "succeeded", "run_id": str(uuid4()),
                                       "release_id": self.release_id, "replayed_release": True})

    def run_schedule(self, **kwargs):
        return run_schedule(self.root, self.path, connection_factory=lambda: nullcontext(self.connection),
                            execute=self.child, **kwargs)

    def test_limits_reject_unbounded_boolean_and_impossible_intervals(self):
        for values in ((0, 0, 1, 1), (25, 0, 1, 1), (True, 0, 1, 1),
                       (2, 10, 1, 10), (1, 0, 901, 3600), (1, 0, 1, 3601)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                validate_limits(*values)

    def test_two_ticks_keep_release_and_write_final_report(self):
        result = self.run_schedule(runs=2, interval_seconds=0)
        self.assertEqual((result["status"], self.child.call_count), ("succeeded", 2))
        saved = json.loads(next((self.root / "experiments/source-audit/schedule-runs").glob("*.json")).read_text())
        self.assertEqual(result, saved)
        self.assertEqual({tick["release_id"] for tick in saved["ticks"]}, {self.release_id})

    def test_first_failure_stops_future_ticks(self):
        self.child.return_value = {"status": "failed", "error_code": "CHILD_TIMEOUT"}
        result = self.run_schedule(runs=3, interval_seconds=0)
        self.assertEqual((result["error_code"], self.child.call_count), ("CHILD_TIMEOUT", 1))

    def test_concurrent_schedule_never_starts_child(self):
        self.locked = False
        self.assertEqual(self.run_schedule()["error_code"], "SCHEDULE_ALREADY_RUNNING")
        self.child.assert_not_called()

    def test_different_or_missing_accepted_plan_never_starts_child(self):
        for head in (None, (self.release_id, "0" * 64)):
            self.head = head
            self.assertEqual(self.run_schedule()["error_code"], "SCHEDULE_FAILED")
        self.child.assert_not_called()

    def test_plan_edit_between_ticks_stops_execution(self):
        def mutate(*args):
            self.path.write_text("{}", encoding="utf-8")
            return {"status": "succeeded", "release_id": self.release_id}
        self.child.side_effect = mutate
        self.assertEqual(self.run_schedule(runs=2, interval_seconds=0)["error_code"], "PLAN_CHANGED")
        self.assertEqual(self.child.call_count, 1)

    def test_elapsed_budget_never_starts_child(self):
        clock = iter([0, 901])
        result = self.run_schedule(monotonic=lambda: next(clock))
        self.assertEqual(result["error_code"], "SCHEDULE_DEADLINE")
        self.child.assert_not_called()

    def test_interrupt_is_recorded_and_lock_is_released(self):
        self.child.side_effect = KeyboardInterrupt
        result = self.run_schedule()
        self.assertEqual(result["error_code"], "SCHEDULE_INTERRUPTED")
        self.assertTrue(any("pg_advisory_unlock" in call.args[0]
                            for call in self.connection.execute.call_args_list))

    def test_child_timeout_and_nonzero_exit_hide_raw_output(self):
        with patch("ingestion.scheduling.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)):
            self.assertEqual(execute_release(self.root, self.path, self.digest, self.release_id, 1)["error_code"], "CHILD_TIMEOUT")
        with patch("ingestion.scheduling.subprocess.run", return_value=Mock(returncode=2, stderr="secret-password")):
            result = execute_release(self.root, self.path, self.digest, self.release_id, 1)
            self.assertNotIn("secret", json.dumps(result))
            self.assertEqual(result["error_code"], "CHILD_FAILED")

    def test_child_result_requires_reviewed_hash_and_unchanged_release(self):
        payload = {"status": "succeeded", "run_id": str(uuid4()), "release_id": self.release_id,
                   "counts": {"replayed_release": True}, "plan_sha256": self.digest}
        with patch("ingestion.scheduling.subprocess.run") as child:
            child.return_value = Mock(returncode=0, stdout=json.dumps(payload))
            self.assertEqual(execute_release(self.root, self.path, self.digest, self.release_id, 1)["status"], "succeeded")
            self.assertFalse(child.call_args.kwargs.get("shell", False))
            payload["plan_sha256"] = "0" * 64
            child.return_value.stdout = json.dumps(payload)
            self.assertEqual(execute_release(self.root, self.path, self.digest, self.release_id, 1)["error_code"], "CHILD_RESULT_INVALID")

    def test_child_plan_hash_guard_runs_before_database_connection(self):
        from ingestion.cli import main
        with patch("ingestion.cli.Path.cwd", return_value=self.root), patch("ingestion.cli.connect") as connect:
            with patch("sys.stderr", new_callable=io.StringIO):
                status = main(["release", "publish", "--plan", str(self.path),
                               "--expected-plan-sha256", "0" * 64])
        self.assertEqual(status, 2)
        connect.assert_not_called()
