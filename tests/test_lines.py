"""What the serving lines must agree on, checked where both are visible."""

import hashlib
import json
import tomllib
import unittest
from pathlib import Path

from tools.release_notes import notes, section

REPO = Path(__file__).resolve().parents[1]
LINES = sorted(p.parent for p in REPO.glob("v[0-9]*/pyproject.toml"))


def version(line):
    text = (line / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)["project"]["version"]


class LineTests(unittest.TestCase):
    def test_both_lines_are_found(self):
        self.assertEqual([line.name for line in LINES], ["v1", "v2"])

    def test_each_lines_version_has_notes_in_both_languages(self):
        # A v* tag publishes the English section; the Japanese changelog is its pair.
        for line in LINES:
            with self.subTest(line=line.name):
                v = version(line)
                self.assertTrue(notes(REPO, v, match_project=True).strip())
                japanese = (line / "CHANGELOG.ja.md").read_text(encoding="utf-8")
                self.assertTrue(section(japanese, v).strip())


class SharedCheckpointTests(unittest.TestCase):
    """Both lines serve one pinned checkpoint; each keeps its own copy of what it reads."""

    def test_the_lines_pin_the_same_model_and_revision(self):
        v1 = json.loads((REPO / "v1/config/runtime.lock.json").read_text("utf-8"))
        v2 = json.loads((REPO / "v2/config/model.lock.json").read_text("utf-8"))
        self.assertEqual((v1["model"], v1["revision"]), (v2["model"], v2["revision"]))

    def test_the_copies_both_lines_read_are_byte_identical(self):
        # The NLL set makes the lines' figures comparable; the lock installs one client.
        for name in ("config/nll_set.json", "requirements/huggingface.lock.txt"):
            with self.subTest(name=name):
                digests = {
                    hashlib.sha256((line / name).read_bytes()).hexdigest()
                    for line in LINES
                }
                self.assertEqual(len(digests), 1)


class CopiedModuleTests(unittest.TestCase):
    """2.x carries its own copies of 1.x modules (each line stands alone). These are
    unchanged but for the package name; one that has to differ leaves this list."""

    # download.py and verify_download.py left it in 2.4.0: 2.x also fetches AXL.
    SAME = (
        "io.py",
        "tool_gate/__init__.py",
        "tool_gate/check.py",
        "tool_gate/repair.py",
    )

    def test_the_copies_differ_only_in_the_package_name(self):
        for name in self.SAME:
            with self.subTest(name=name):
                v1 = (REPO / "v1/glm53_setup" / name).read_text(encoding="utf-8")
                v2 = (REPO / "v2/glm53_tf" / name).read_text(encoding="utf-8")
                self.assertEqual(v1.replace("glm53_setup", "glm53_tf"), v2)


if __name__ == "__main__":
    unittest.main()
