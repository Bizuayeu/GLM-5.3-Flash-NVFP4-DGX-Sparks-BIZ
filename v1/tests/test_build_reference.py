import contextlib
import io
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_setup import build_reference
from glm53_setup.config import CHECKOUT, ROOT

LOCK = {
    "platform": "linux/arm64",
    "image": "nvcr.io/example/base@sha256:" + "0" * 64,
    "reference_candidate": {"tag": "glm53-reference:test"},
}


class BuildCommandTests(unittest.TestCase):
    def test_the_build_is_pinned_to_the_lock_and_rooted_at_the_checkout(self):
        command = build_reference.build_command(LOCK)
        self.assertEqual(command[:2], ["docker", "build"])
        self.assertEqual(command[command.index("--platform") + 1], "linux/arm64")
        self.assertEqual(
            command[command.index("--build-arg") + 1], "BASE_IMAGE=" + LOCK["image"]
        )
        self.assertEqual(command[command.index("-t") + 1], "glm53-reference:test")
        self.assertEqual(
            command[command.index("-f") + 1], str(ROOT / "docker/Dockerfile.reference")
        )
        self.assertEqual(command[-1], str(CHECKOUT))

    def test_every_copy_source_is_in_the_build_context(self):
        # The context is the checkout root: the licences live beside v1/.
        dockerfile = (ROOT / "docker/Dockerfile.reference").read_text(encoding="utf-8")
        sources = [
            source
            for line in dockerfile.splitlines()
            if line.startswith("COPY ")
            for source in line.split()[1:-1]
        ]
        self.assertIn("LICENSE", sources)
        for source in sources:
            with self.subTest(source=source):
                self.assertTrue((CHECKOUT / source).exists())

    def test_plan_prints_the_command_and_builds_nothing(self):
        out = io.StringIO()
        with (
            patch.object(build_reference, "load_lock", return_value=LOCK),
            patch.object(build_reference.subprocess, "run") as run,
            contextlib.redirect_stdout(out),
        ):
            build_reference.main(["--plan"])
        run.assert_not_called()
        self.assertEqual(
            json.loads(out.getvalue()), build_reference.build_command(LOCK)
        )


def inspect_output(layers):
    """`docker image inspect` stdout for an image with this many layers."""
    diff_ids = ["sha256:" + f"{i:064x}" for i in range(layers)]
    return json.dumps([{"Id": "sha256:" + "f" * 64, "RootFS": {"Layers": diff_ids}}])


class LayerBudgetTests(unittest.TestCase):
    def test_counts_the_layers_and_the_headroom_to_the_overlay2_limit(self):
        for layers, headroom, warning in (
            (48, 77, False),
            (123, 2, False),
            (124, 1, True),
            (126, -1, True),
        ):
            with self.subTest(layers=layers):
                self.assertEqual(
                    build_reference.layer_budget(json.loads(inspect_output(layers))),
                    {
                        "layers": layers,
                        "limit": 125,
                        "headroom": headroom,
                        "warning": warning,
                    },
                )

    def test_record_dir_keeps_the_layer_count_and_warns_near_the_limit(self):
        for layers, warned in ((48, False), (124, True)):
            with (
                self.subTest(layers=layers),
                tempfile.TemporaryDirectory() as tmp,
                patch.object(build_reference, "load_lock", return_value=LOCK),
                patch.object(
                    build_reference.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess([], 0),
                        subprocess.CompletedProcess([], 0, inspect_output(layers)),
                    ],
                ),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()) as err,
            ):
                build_reference.main(["--record-dir", tmp])
                record = json.loads(
                    (Path(tmp) / "image-layers.json").read_text(encoding="utf-8")
                )
                self.assertEqual(record["layers"], layers)
                self.assertEqual(record["warning"], warned)
                self.assertEqual("125" in err.getvalue(), warned)


if __name__ == "__main__":
    unittest.main()


def ignore_patterns():
    lines = (CHECKOUT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def pattern(text):
    """A .dockerignore pattern as a regular expression over slash-separated paths."""
    out, i = "", 0
    while i < len(text):
        if text.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif text.startswith("**", i):
            out, i = out + ".*", i + 2
        else:
            out += {"*": "[^/]*", "?": "[^/]"}.get(text[i], re.escape(text[i]))
            i += 1
    return re.compile(out)


def admitted(path, patterns):
    """Docker's rule: the last pattern matching the path or a parent of it decides."""
    parts = path.split("/")
    keep = True
    for line in patterns:
        negated = line.startswith("!")
        regex = pattern(line.removeprefix("!").strip("/"))
        if any(regex.fullmatch("/".join(parts[:n])) for n in range(1, len(parts) + 1)):
            keep = negated
    return keep


class BuildContextTests(unittest.TestCase):
    def test_the_ignore_rule_reads_parents_and_last_matches(self):
        patterns = ["*", "!v2/scripts/", "**/__pycache__"]
        self.assertTrue(admitted("v2/scripts/serve.sh", patterns))
        self.assertFalse(admitted("v2/README.md", patterns))
        self.assertFalse(admitted("v2/scripts/__pycache__/x.pyc", patterns))

    def test_every_image_copies_only_what_the_context_admits(self):
        # Both lines build from the checkout root through its one .dockerignore.
        patterns = ignore_patterns()
        for dockerfile in ("v1/docker/Dockerfile.reference", "v2/docker/Dockerfile"):
            text = (CHECKOUT / dockerfile).read_text(encoding="utf-8")
            self.assertTrue(admitted(dockerfile, patterns), dockerfile)
            for line in text.splitlines():
                if not line.startswith("COPY "):
                    continue
                for source in line.split()[1:-1]:
                    path = CHECKOUT / source
                    files = [path] if path.is_file() else sorted(path.rglob("*"))
                    self.assertTrue(path.exists(), source)
                    for f in files:
                        if f.is_file() and "__pycache__" not in f.parts:
                            name = f.relative_to(CHECKOUT).as_posix()
                            with self.subTest(dockerfile=dockerfile, file=name):
                                self.assertTrue(admitted(name, patterns))
