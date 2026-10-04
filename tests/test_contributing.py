"""CONTRIBUTING tells contributors to run what CI runs, in both languages."""

import posixpath
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def commands(text):
    """The command lines of a page's sh blocks, without comments."""
    blocks = re.findall(r"```sh\n(.*?)```", text, re.S)
    lines = (line.strip() for block in blocks for line in block.splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def ci_runs():
    workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    return re.findall(r"^\s*- run: (.+)$", workflow, re.M)


class ContributingTests(unittest.TestCase):
    def test_every_check_ci_runs_is_in_contributing(self):
        runs = [run for run in ci_runs() if not run.startswith("python -m pip")]
        for name in ("CONTRIBUTING.md", "CONTRIBUTING.ja.md"):
            listed = commands((REPO / name).read_text(encoding="utf-8"))
            with self.subTest(page=name):
                self.assertEqual(sorted(set(runs)), sorted(set(listed)))

    def test_every_lock_ci_installs_exists_and_is_in_contributing(self):
        # CI's pip steps run in v1/ (the jobs' working directory); the paths are
        # compared from the checkout root, as CONTRIBUTING writes them.
        locks = {
            posixpath.normpath(posixpath.join("v1", path))
            for run in ci_runs()
            if run.startswith("python -m pip install")
            for path in re.findall(r"-r (\S+)", run)
        }
        self.assertTrue(locks)
        for lock in sorted(locks):
            self.assertTrue((REPO / lock).is_file(), lock)
            for name in ("CONTRIBUTING.md", "CONTRIBUTING.ja.md"):
                with self.subTest(lock=lock, page=name):
                    self.assertIn(lock, (REPO / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
