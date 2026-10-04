import ast
import contextlib
import hashlib
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from glm53_setup.runtime import patch_image_budget as budget

# The lines of vLLM 385dce36 models/glm5next/nvidia/multimodal.py around the two sites.
SOURCE = '''# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""GLM-5.3-Flash vision tower and multimodal processor."""

from collections.abc import Mapping
from functools import cached_property, partial

from vllm.multimodal.parse import ImageSize, MultiModalDataItems


class Glm5NextProcessingInfo(Glm4vProcessingInfo):
    def _get_image_max_pixels(self) -> int:
        mm_kwargs = self.ctx.get_merged_mm_kwargs({})
        if (override := mm_kwargs.get("max_pixels")) is not None:
            return int(override)
        return self._processor_pixel_budget(self.get_hf_processor().image_processor)[1]

    def _get_video_max_pixels(self) -> int:
        mm_kwargs = self.ctx.get_merged_mm_kwargs({})
        if (override := mm_kwargs.get("max_pixels")) is not None:
            return int(override)
        return self._processor_pixel_budget(self.get_hf_processor().video_processor)[1]

    def _get_vision_info(
        self,
        *,
        image_width: int,
    ):
        pass
'''

# vllm-project/vllm #59565 as merged (5688a4dd4a), the method it adds to the processing info.
UPSTREAM_METHOD = """    def get_image_size_with_most_features(self) -> ImageSize:
        # The inherited square probe strands budget whenever the token
        # ceiling is not a perfect square: with max_image_tokens=8000 the
        # square refits to 2492x2492 (89x89 = 7921 tokens) while a
        # 2240x2800 canvas reaches 80x100 = 8000, so the encoder cache came
        # up short of the processor's own maximum and refused valid images
        # (#59539). Factor the ceiling exactly instead of probing a square.
        vision_config = self.get_hf_config().vision_config
        factor = (
            vision_config.patch_size
            * vision_config.spatial_merge_size
            * self.get_hf_processor().image_processor.patch_expand_factor
        )
        pixels_per_token = vision_config.temporal_patch_size * factor * factor
        max_tokens = max(1, self._get_image_max_pixels() // pixels_per_token)
        short_side = math.isqrt(max_tokens)
        while max_tokens % short_side:
            short_side -= 1
        return ImageSize(
            width=(max_tokens // short_side) * factor,
            height=short_side * factor,
        )
"""


def probe(max_pixels):
    """Run the patched method on the checkpoint's vision geometry (14 px patches, 2x2 merge)."""
    tree = ast.parse(budget.patch_text(SOURCE))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    method = next(
        n
        for n in cls.body
        if getattr(n, "name", "") == "get_image_size_with_most_features"
    )
    method.returns = None
    space = {"math": math, "ImageSize": lambda width, height: (width, height)}
    exec(compile(ast.Module([method], []), "probe", "exec"), space)
    info = SimpleNamespace(
        get_hf_config=lambda: SimpleNamespace(
            vision_config=SimpleNamespace(
                patch_size=14, spatial_merge_size=2, temporal_patch_size=2
            )
        ),
        get_hf_processor=lambda: SimpleNamespace(
            image_processor=SimpleNamespace(patch_expand_factor=1)
        ),
        _get_image_max_pixels=lambda: max_pixels,
    )
    return space["get_image_size_with_most_features"](info)


class PatchTests(unittest.TestCase):
    def test_the_method_is_the_upstream_pull_request_lines(self):
        patched = budget.patch_text(SOURCE)
        self.assertIn(UPSTREAM_METHOD + "\n    def _get_vision_info(\n", patched)
        self.assertIn(
            '"""\n\nimport math\nfrom collections.abc import Mapping\n', patched
        )
        self.assertTrue(patched.startswith("# Modified by GLM setup"))

    def test_the_probe_reaches_the_token_ceiling(self):
        # 1,568 pixels a token: 8,000 tokens factor exactly as 80 x 100, not the square 89 x 89.
        self.assertEqual(probe(1568 * 8000), (100 * 28, 80 * 28))
        self.assertEqual(probe(1568 * 100), (10 * 28, 10 * 28))
        width, height = probe(1568 * 7921)
        self.assertEqual((width // 28) * (height // 28), 7921)

    def test_refuses_drifted_or_already_patched_source(self):
        with self.assertRaises(ValueError):
            budget.patch_text(
                SOURCE.replace("video_processor)[1]", "video_processor)[0]")
            )
        with self.assertRaises(ValueError):
            budget.patch_text(budget.patch_text(SOURCE))


class PrepareTests(unittest.TestCase):
    def package(self, directory, text=SOURCE):
        package = Path(directory) / "vllm"
        target = package / budget.TARGET
        target.parent.mkdir(parents=True)
        target.write_bytes(text.encode("utf-8"))
        return package

    def test_the_pin_is_the_pinned_vllm_file(self):
        # sha256 of `git show 385dce36:vllm/models/glm5next/nvidia/multimodal.py`.
        self.assertEqual(budget.TARGET, "models/glm5next/nvidia/multimodal.py")
        self.assertEqual(
            budget.SOURCE_SHA256,
            "896d9f133f97d338182f4880e2e7d3ac3b8def25ef7eaf82182f0ea01a3d72d7",
        )

    def test_the_command_writes_the_file_and_the_image_record(self):
        with tempfile.TemporaryDirectory() as directory:
            package = self.package(directory)
            digest = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
            with patch.object(budget, "SOURCE_SHA256", digest):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    budget.main(["--package", str(package)])
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    budget.prepare(package)
            self.assertIn(
                "def get_image_size_with_most_features",
                (package / budget.TARGET).read_text(encoding="utf-8"),
            )
            record = json.loads((package.parent / budget.RECORD).read_text())
            self.assertEqual(record["source_sha256"], digest)

    def test_a_drifted_file_is_refused_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            package = self.package(directory)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                budget.main(["--package", str(package)])
            self.assertEqual(
                (package / budget.TARGET).read_bytes(), SOURCE.encode("utf-8")
            )


if __name__ == "__main__":
    unittest.main()
