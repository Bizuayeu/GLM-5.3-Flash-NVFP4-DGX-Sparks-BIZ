"""A rank's recorded container that Docker no longer has (removed after it exited) counts as stopped.

Missing is decided from a successful ``docker ps -a`` inventory, never from a failed inspect: an inventory that
fails still raises.
"""

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from glm53_setup import cluster, server

GONE = "glm53-startup-r0-gone"


@contextlib.contextmanager
def recorded(root, names, rank=0):
    """Rank ``rank`` recorded as ``GONE`` under ``root``; Docker lists ``names``."""
    (root / "state").mkdir()
    server.write_json(
        root / f"state/startup-rank{rank}.json",
        {"name": GONE, "fingerprint": "f", "record": str(root)},
    )
    calls = []

    def run(*args):
        calls.append(args)
        if args[:3] == ("docker", "ps", "-a"):
            return "\n".join(names) + "\n"
        if args[:2] == ("docker", "inspect"):
            raise subprocess.CalledProcessError(1, args)
        return ""

    with (
        patch.object(server, "STATE", root / "state"),
        patch.object(cluster, "RECORDS", root / "records"),
        patch.object(server.host, "run", side_effect=run),
    ):
        yield calls


class MissingRecordedContainerTests(unittest.TestCase):
    def test_inspect_recorded_is_none_for_a_name_docker_does_not_list(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            recorded(Path(tmp), ["other"]) as calls,
        ):
            self.assertIsNone(server.inspect_recorded(GONE))
            self.assertIn(("docker", "ps", "-a", "--format", "{{.Names}}"), calls)

    def test_a_listed_name_whose_inspect_fails_still_raises(self):
        with tempfile.TemporaryDirectory() as tmp, recorded(Path(tmp), [GONE]):
            with self.assertRaises(subprocess.CalledProcessError):
                server.inspect_recorded(GONE)

    def test_inspect_recorded_inspects_a_listed_name(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            recorded(Path(tmp), [GONE]),
            patch.object(
                server, "inspect_owned", return_value={"State": {"Running": True}}
            ) as owned,
        ):
            self.assertEqual(
                server.inspect_recorded(GONE, "f"), {"State": {"Running": True}}
            )
            owned.assert_called_once_with(GONE, "f")

    def test_a_failed_inventory_still_raises(self):
        def broken(*args):
            raise subprocess.CalledProcessError(1, args)

        with patch.object(server.host, "run", side_effect=broken):
            with self.assertRaises(subprocess.CalledProcessError):
                server.inspect_recorded(GONE)

    def test_current_reports_nothing_for_a_removed_container(self):
        with tempfile.TemporaryDirectory() as tmp, recorded(Path(tmp), ["other"]):
            self.assertIsNone(cluster.rpc("current", 0, None))

    def test_a_new_rank_may_start_after_its_previous_container_was_removed(self):
        with tempfile.TemporaryDirectory() as tmp, recorded(Path(tmp), []):
            self.assertFalse(server.rank_running(0))

    def test_stop_of_a_removed_container_succeeds_without_docker_stop(self):
        out = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as tmp,
            recorded(Path(tmp), []) as calls,
            patch.object(server.os, "name", "posix"),
            contextlib.redirect_stdout(out),
        ):
            server.act_stop(None, SimpleNamespace(rank=0), None)
            self.assertFalse([c for c in calls if c[:2] == ("docker", "stop")])
        self.assertIn(GONE, out.getvalue())

    def test_status_of_a_removed_container_says_so(self):
        out = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as tmp,
            recorded(Path(tmp), []),
            patch.object(server.settings, "fingerprint", return_value="f"),
            contextlib.redirect_stdout(out),
        ):
            server.act_status(None, SimpleNamespace(rank=0), {})
        report = json.loads(out.getvalue())
        self.assertEqual((report["name"], report["state"]), (GONE, None))

    def test_the_running_head_refuses_a_removed_container_in_words(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            recorded(Path(tmp), []),
            patch.object(server.settings, "fingerprint", return_value="f"),
        ):
            with self.assertRaisesRegex(ValueError, "needs the head"):
                server.running_head({}, require="needs the head")
            with self.assertRaisesRegex(ValueError, GONE):
                server.running_head({})


if __name__ == "__main__":
    unittest.main()
