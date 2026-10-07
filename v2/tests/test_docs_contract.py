"""The facts the 2.x pages repeat from the scripts, the Dockerfile and the lock.

The scripts and the Dockerfile own the values; README, SETUP, validation and CHANGELOG
quote them in both languages. Each test reads the owner and looks for its value in
every quote, so a changed default fails here until the pages say it too.
"""

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from glm53_tf import config

LINE = Path(__file__).resolve().parents[1]
HOST = LINE.parent / "host"
PAIRS = ("", ".ja")


def read(name):
    return (LINE / name).read_text(encoding="utf-8")


def owned(pattern, name):
    """The value a script or Dockerfile sets, by the one pattern that matches it."""
    match = re.search(pattern, read(name))
    if match is None:
        raise AssertionError(f"{pattern!r} matches nothing in {name}")
    return match[1]


def section(text, heading):
    """A level-2 section of a Markdown page, from its heading to the next one."""
    start = text.index(f"\n## {heading}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def row(text, key):
    """The table row that names ``key`` in backticks."""
    rows = [line for line in text.splitlines() if line.startswith("|") and key in line]
    if len(rows) != 1:
        raise AssertionError(f"{len(rows)} table rows name {key}")
    return rows[0]


def row_starting(text, prefix):
    """The one line of a page that starts with ``prefix``."""
    lines = [line for line in text.splitlines() if line.startswith(prefix)]
    if len(lines) != 1:
        raise AssertionError(f"{len(lines)} lines start with {prefix!r}")
    return lines[0]


def readme(suffix):
    return read(f"README{suffix}.md")


SERVING = {"": "Serving Defaults", ".ja": "配信の既定"}


class ServingDefaultsTests(unittest.TestCase):
    """README's serving-defaults table quotes serve.sh."""

    def serving(self, suffix):
        return section(readme(suffix), SERVING[suffix])

    def test_the_window_by_tp(self):
        tp2 = int(owned(r"\n\s*2\) context=(\d+)", "scripts/serve.sh"))
        tp3 = owned(r"\n\s*3\) context=(\d+)", "scripts/serve.sh")
        for suffix in PAIRS:
            window = row(self.serving(suffix), "`--context`")
            self.assertIn(f"{tp2:,}", window, suffix)
            self.assertIn(f"| {tp3}", window, suffix)

    def test_the_reply_limit_drafter_and_kv(self):
        limit = int(owned(r"--max-tokens (\d+)", "scripts/serve.sh"))
        drafter = owned(r"--drafter (\w+)", "scripts/serve.sh")
        kv = owned(r"export TF_GLM_KV=(\w+)", "scripts/serve.sh")
        for suffix in PAIRS:
            serving = self.serving(suffix)
            self.assertIn(f"{limit:,}", row(serving, "`--max-tokens`"), suffix)
            self.assertIn(f"`--drafter {drafter}`", serving, suffix)
            self.assertIn(f"`TF_GLM_KV={kv}`", serving, suffix)

    def test_the_heat_wait(self):
        high = owned(r"TF_GLM_HEAT_HIGH-(\d+)", "scripts/serve.sh")
        low = owned(r"TF_GLM_HEAT_LOW-(\d+)", "scripts/serve.sh")
        for suffix in PAIRS:
            pause = row(self.serving(suffix), "`TF_GLM_HEAT_HIGH")
            self.assertIn(f"{high} °C", pause, suffix)
            self.assertIn(f"{low} °C", pause, suffix)
            setting = row(readme(suffix), "| `TF_GLM_HEAT_HIGH`")
            self.assertIn(f"`{high}`", setting, suffix)
            self.assertIn(f"`{low}`", setting, suffix)

    def test_the_heat_ceiling(self):
        ceiling = owned(r"TF_GLM_HEAT_CEILING-(\d+)", "scripts/serve.sh")
        for suffix in PAIRS:
            self.assertIn(f"{ceiling} °C", row(self.serving(suffix), "`TF_GLM_HEAT_HIGH"), suffix)
            self.assertIn(f"`{ceiling}`", row(readme(suffix), "| `TF_GLM_HEAT_CEILING`"), suffix)

    def test_the_heat_wait_starts_below_the_thermal_watch(self):
        # The engine pauses before the watch would stop it, and looks one chunk ahead to stay under it.
        high = float(owned(r"TF_GLM_HEAT_HIGH-(\d+)", "scripts/serve.sh"))
        ceiling = float(owned(r"TF_GLM_HEAT_CEILING-(\d+)", "scripts/serve.sh"))
        stop = float(owned(r"\nTHRESHOLD_C = ([\d.]+)", HOST / "thermal-watch"))
        self.assertLess(high, ceiling)
        self.assertLess(ceiling, stop)


class ConfigurationTableTests(unittest.TestCase):
    """README's configuration table quotes the scripts' defaults."""

    def assert_row(self, key, values):
        for suffix in PAIRS:
            line = row(section(readme(suffix), CONFIGURATION[suffix]), key)
            for value in values:
                self.assertIn(f"`{value}`", line, (suffix, key))

    def test_rank_zero_endpoint(self):
        self.assert_row(
            "`MODEL_NAME`",
            [
                owned(r"MODEL_NAME:-([^}]+)", "scripts/serve.sh"),
                owned(r"HOST:-([^}]+)", "scripts/serve.sh"),
                owned(r"PORT:-([^}]+)", "scripts/serve.sh"),
            ],
        )

    def test_cluster_file_defaults(self):
        self.assert_row(
            "`SSH`",
            [
                owned(r"SSH=\$\{SSH:-([^}]+)\}", "scripts/cluster.sh"),
                owned(r"CONTAINER=\$\{CONTAINER:-([^}]+)\}", "scripts/cluster.sh"),
                owned(r"WORK=\$\{WORK:-'([^']+)'\}", "scripts/cluster.sh"),
            ],
        )

    def test_container_defaults(self):
        home = lambda path: path.replace("$HOME", "~")  # noqa: E731
        self.assert_row(
            "`HF_HUB`",
            [
                home(owned(r"work=\$\{2:-([^}]+)\}", "scripts/create_container.sh")),
                owned(
                    r'--name "\$\{CONTAINER:-([^}]+)\}"', "scripts/create_container.sh"
                ),
                home(
                    owned(r"hub=\$\{HF_HUB:-([^}]+)\}", "scripts/create_container.sh")
                ),
            ],
        )


CONFIGURATION = {"": "Configuration", ".ja": "設定"}


class PortTests(unittest.TestCase):
    """The tool-argument gate and the checks reach the port serve.sh gives rank 0."""

    def test_the_gate_command_in_setup_is_the_gate_default(self):
        port = owned(
            r'"--port", type=int, default=(\d+)', "glm53_tf/tool_gate/proxy.py"
        )
        upstream = owned(
            r'"--upstream", default="([^"]+)"', "glm53_tf/tool_gate/proxy.py"
        )
        serving = owned(r"PORT:-([^}]+)", "scripts/serve.sh")
        self.assertEqual(upstream, f"http://127.0.0.1:{serving}")
        for suffix in PAIRS:
            setup = read(f"SETUP{suffix}.md")
            self.assertIn(f"tool-gate --port {port} --upstream {upstream}", setup)

    def test_the_checks_target_rank_zero(self):
        port = owned(r"PORT:-([^}]+)", "scripts/serve.sh")
        name = owned(r"MODEL_NAME:-([^}]+)", "scripts/serve.sh")
        for tool in ("decode_check", "bench", "long_input"):
            path = f"glm53_tf/{tool}.py"
            base = owned(r'BASE = os\.environ\.get\("BASE", "([^"]+)"\)', path)
            model = owned(r'MODEL = os\.environ\.get\("MODEL", "([^"]+)"\)', path)
            self.assertEqual(base, f"http://127.0.0.1:{port}", tool)
            self.assertEqual(model, name, tool)


class ImageTests(unittest.TestCase):
    """The pages name the engine commit and the base image the Dockerfile builds."""

    def test_the_engine_commit(self):
        ref = owned(r"ARG TENSORFOLD_REF=([0-9a-f]{40})", "docker/Dockerfile")
        for suffix in PAIRS:
            self.assertIn(ref, read(f"CHANGELOG{suffix}.md"), suffix)
            self.assertIn(f"`{ref[:7]}`", readme(suffix), suffix)

    def test_the_base_image_is_pinned_by_digest(self):
        base = owned(r"ARG BASE_IMAGE=(\S+)", "docker/Dockerfile")
        self.assertRegex(base, r"@sha256:[0-9a-f]{64}$")
        for suffix in PAIRS:
            self.assertIn(f"`{base}`", read(f"SETUP{suffix}.md"), suffix)

    def test_the_commands_build_and_run_the_dockerfiles_tag(self):
        # The Dockerfile's usage line owns the tag; each page's commands repeat it.
        tag = owned(r"-t (glm53-tf:\S+) \.", "docker/Dockerfile")
        for suffix in PAIRS:
            for name in ("README", "SETUP", "docs/operations"):
                commands = re.findall(
                    r"(?:-t|inspect .*|create_container\.sh) (glm53-tf:\S+)",
                    read(f"{name}{suffix}.md"),
                )
                with self.subTest(page=name + suffix):
                    self.assertTrue(commands)
                    self.assertEqual(set(commands), {tag})

    def test_the_readme_names_the_image_it_builds(self):
        # The image's version is the release accepted last: the Status bullet names it
        # and the release measurements have its entry.
        version = owned(r"-t glm53-tf:(\S+) \.", "docker/Dockerfile")
        for suffix, status, measured in (
            ("", "- **Status.**", "Measured on the Release"),
            (".ja", "- **状態。**", "リリースでの測定値"),
        ):
            text = readme(suffix)
            with self.subTest(suffix=suffix):
                self.assertIn(version, row_starting(text, status))
                self.assertIn(f"**{version}**", section(text, measured))


class MemoryGuardTests(unittest.TestCase):
    """The pages quote the memory guard's floor."""

    def test_the_floor(self):
        floor = owned(r'"\$available" -lt (\d+) \]', "scripts/hostwatch.sh")
        for suffix in PAIRS:
            for name in ("README", "docs/operations"):
                with self.subTest(page=name + suffix):
                    self.assertIn(f"{floor} GiB", read(f"{name}{suffix}.md"))


class LockTests(unittest.TestCase):
    """The pages that write the pinned revision out write the locked one."""

    def test_pages_name_the_locked_revision(self):
        for suffix in PAIRS:
            self.assertTrue(f"`{config.MODEL}`" in readme(suffix), suffix)
            for name in ("README", "docs/validation"):
                text = read(f"{name}{suffix}.md")
                self.assertTrue(config.REVISION in text, name + suffix)


class SiteFileTests(unittest.TestCase):
    """The pages put a file with the site's values where Git ignores it (state/)."""

    def test_the_cluster_file_goes_under_state(self):
        for name in ("README", "SETUP"):
            for suffix in PAIRS:
                text = read(f"{name}{suffix}.md")
                paths = re.findall(r"cluster\.sh (\S+) (?:start|stop|status)", text)
                paths += re.findall(r"cp v2/examples/cluster\.tp\d\.env (\S+)", text)
                self.assertTrue(paths, name + suffix)
                for path in paths:
                    self.assertTrue(path.startswith("state/"), (name + suffix, path))
        ignored = (LINE.parent / ".gitignore").read_text(encoding="utf-8").split()
        self.assertIn("/state", ignored)


def assignments(path):
    """The KEY=value lines of a sourced file; a value may itself start with '='."""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"([A-Z_][A-Z0-9_]*)=(\S*)", line)
        if match:
            values[match[1]] = match[2]
    return values


class ExampleFileTests(unittest.TestCase):
    """The reference hosts' files agree with each other and with the cluster files."""

    def test_every_rank_of_a_tp_meets_at_one_master_with_the_same_keys(self):
        for tp in (2, 3):
            ranks = [
                assignments(LINE / f"examples/tp{tp}-rank{r}.env") for r in range(tp)
            ]
            self.assertTrue(all(rank.get("MASTER") for rank in ranks), tp)
            self.assertEqual(len({rank["MASTER"] for rank in ranks}), 1, tp)
            self.assertEqual(len({frozenset(rank) for rank in ranks}), 1, tp)

    def test_a_cluster_file_names_one_host_per_rank(self):
        for tp in (2, 3):
            cluster = assignments(LINE / f"examples/cluster.tp{tp}.env")
            self.assertEqual(cluster["TP"], str(tp))
            hosts = re.search(
                r'^HOSTS="([^"]+)"', read(f"examples/cluster.tp{tp}.env"), re.M
            )[1]
            self.assertEqual(len(hosts.split()), tp)


# On Windows `bash` can resolve to WSL's launcher, which cannot read Windows paths; Linux CI runs this.
@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "needs bash on POSIX")
class ScriptSyntaxTests(unittest.TestCase):
    def test_every_shell_script_parses(self):
        scripts = sorted((LINE / "scripts").glob("*.sh")) + [HOST / "install.sh"]
        for script in scripts:
            result = subprocess.run(
                ["bash", "-n", script.as_posix()],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, (script.name, result.stderr))


if __name__ == "__main__":
    unittest.main()
