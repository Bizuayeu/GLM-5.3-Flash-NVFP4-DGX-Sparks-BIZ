"""CONTRIBUTING tells contributors to run what CI runs, in both languages."""

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


if __name__ == "__main__":
    unittest.main()
