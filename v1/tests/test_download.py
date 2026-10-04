"""download() of the pinned checkpoint: its status file and its lock."""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from glm53_setup import download


def fake_hub(snapshot, sha, sizes):
    """A huggingface_hub whose model lists ``sizes`` and downloads into ``snapshot``."""
    siblings = [SimpleNamespace(rfilename=n, size=s) for n, s in sizes.items()]
    api = SimpleNamespace(
        model_info=lambda *a, **k: SimpleNamespace(sha=sha, siblings=siblings)
    )
    return SimpleNamespace(
        HfApi=lambda: api, snapshot_download=lambda *a, **k: str(snapshot)
    )


INDEX = json.dumps({"weight_map": {"a": "model-1.safetensors"}})


class DownloadTests(unittest.TestCase):
    """download() records why it stopped, so the status file is the job's verdict."""

    def run_download(self, sha=None, files=None, sizes=None):
        with tempfile.TemporaryDirectory() as tmp:
            state, snapshot = Path(tmp) / "state", Path(tmp) / "snapshot"
            snapshot.mkdir()
            files = (
                {"model.safetensors.index.json": INDEX, "model-1.safetensors": "w"}
                if files is None
                else files
            )
            for name, text in files.items():
                (snapshot / name).write_text(text, encoding="utf-8")
            if sizes is None:
                sizes = {n: len(t.encode("utf-8")) for n, t in files.items()}
            hub = fake_hub(snapshot, sha or download.REVISION, sizes)
            with (
                patch.dict(sys.modules, {"huggingface_hub": hub}),
                patch.dict(os.environ),
                patch.object(download, "STATE", state),
                redirect_stdout(io.StringIO()),
            ):
                try:
                    download.download()
                    code = None
                except SystemExit as error:
                    code = error.code
            status = json.loads((state / download.STATUS_FILE).read_text("utf-8"))
        return code, status

    def test_a_complete_snapshot_is_recorded_with_its_shards(self):
        code, status = self.run_download()
        self.assertIsNone(code)
        self.assertEqual(status["status"], "complete")
        self.assertEqual((status["file_count"], status["weight_shards"]), (2, 1))

    def test_another_revision_fails_the_job(self):
        code, status = self.run_download(sha="0" * 40)
        self.assertEqual(code, 1)
        self.assertEqual(
            (status["status"], status["error_type"]), ("failed", "RuntimeError")
        )

    def test_a_file_of_the_wrong_size_fails_the_job(self):
        files = {"model.safetensors.index.json": INDEX, "model-1.safetensors": "w"}
        sizes = {"model.safetensors.index.json": len(INDEX), "model-1.safetensors": 2}
        code, status = self.run_download(files=files, sizes=sizes)
        self.assertEqual((code, status["status"]), (1, "failed"))

    def test_an_indexed_shard_that_is_missing_fails_the_job(self):
        files = {"model.safetensors.index.json": INDEX}
        code, status = self.run_download(files=files)
        self.assertEqual((code, status["status"]), (1, "failed"))


@unittest.skipUnless(importlib.util.find_spec("filelock"), "needs filelock")
class LockTests(unittest.TestCase):
    def test_a_second_download_in_the_same_workspace_is_refused(self):
        from filelock import FileLock

        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(download, "STATE", Path(tmp)),
                FileLock(Path(tmp) / "download.lock"),
                self.assertRaisesRegex(SystemExit, "already owns this workspace"),
            ):
                download.main([])


if __name__ == "__main__":
    unittest.main()
