import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from glm53_tf import download

LINE = Path(__file__).resolve().parents[1]


class BackgroundTests(unittest.TestCase):
    def test_the_background_job_runs_this_lines_package_from_v2(self):
        with tempfile.TemporaryDirectory() as tmp:
            posix = SimpleNamespace(name="posix", environ=os.environ)
            with (
                patch.object(download, "STATE", Path(tmp)),
                patch.object(download, "os", posix),
                patch.object(download.subprocess, "Popen") as popen,
                redirect_stdout(io.StringIO()),
            ):
                popen.return_value.pid = 1
                download.main(["--background"])
            self.assertTrue((Path(tmp) / "download.log").is_file())
        command = popen.call_args.args[0]
        self.assertEqual(command[1:], ["-m", "glm53_tf", "download"])
        self.assertEqual(popen.call_args.kwargs["cwd"], LINE)


if __name__ == "__main__":
    unittest.main()
