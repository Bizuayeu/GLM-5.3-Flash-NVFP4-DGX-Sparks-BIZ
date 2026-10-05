import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_setup.runtime import patch_vision_rope as rope

# The lines of vLLM 385dce36 models/glm5next/nvidia/multimodal.py around the four sites,
# as patch_image_budget leaves them.
SOURCE = '''# Modified by GLM setup: the image encoder cache is sized to the processor's token ceiling.
"""GLM-5.3-Flash vision tower and multimodal processor."""

from vllm.models.common.ops import fused_q_kv_rmsnorm
from vllm.multimodal.parse import ImageSize, MultiModalDataItems
from vllm.v1.attention.backends.registry import AttentionBackendEnum


class Glm5NextVisionTransformer(nn.Module):
    def __init__(self, text_config, vision_config):
        head_dim = self.hidden_size // self.num_heads
        self.rotary_pos_emb = get_rope(
            head_size=head_dim,
            max_position=8192,
            is_neox_style=True,
            rope_parameters={"partial_rotary_factor": 0.5},
        )

    def rot_pos_emb(self, grid_thw):
        cos, sin = self.rotary_pos_emb.get_cos_sin(max_grid_size)

        pos_ids = pos_ids.to(cos.device, non_blocking=True)
        cos_combined = cos[pos_ids].flatten(1)

    def forward(self, x, grid_thw):
        if True:
            cu_seqlens = torch.cat([cu_seqlens.new_zeros(1), cu_seqlens])
            cu_seqlens = cu_seqlens.to(self.device, non_blocking=True)
            max_seqlen = self.compute_attn_mask_seqlen(cu_seqlens)
'''

# vllm-project/vllm #59126 as merged (0979892992): its four changed lines.
UPSTREAM_LINES = (
    "from vllm.multimodal.parse import ImageSize, MultiModalDataItems\n"
    "from vllm.utils.torch_utils import async_tensor_h2d\n",
    "            max_position=text_config.max_position_embeddings,\n",
    "        pos_ids = async_tensor_h2d(pos_ids, device=cos.device)\n",
    "            cu_seqlens = async_tensor_h2d(cu_seqlens, device=self.device)\n",
)


class PatchTests(unittest.TestCase):
    def test_the_changes_are_the_upstream_pull_request_lines(self):
        patched = rope.patch_text(SOURCE)
        for line in UPSTREAM_LINES:
            self.assertIn(line, patched)
        self.assertNotIn("max_position=8192", patched)
        self.assertNotIn("non_blocking=True", patched)
        self.assertTrue(patched.startswith("# Modified by GLM setup: the vision rope"))

    def test_nothing_else_changes(self):
        patched = rope.patch_text(SOURCE)
        self.assertEqual(len(patched.splitlines()), len(SOURCE.splitlines()) + 3)

    def test_refuses_drifted_or_already_patched_source(self):
        with self.assertRaises(ValueError):
            rope.patch_text(SOURCE.replace("max_position=8192", "max_position=16384"))
        with self.assertRaises(ValueError):
            rope.patch_text(
                SOURCE.replace("pos_ids.to(cos.device, ", "pos_ids.to(cos.device,  ")
            )
        with self.assertRaises(ValueError):
            rope.patch_text(rope.patch_text(SOURCE))


class PrepareTests(unittest.TestCase):
    def package(self, directory, text=SOURCE):
        package = Path(directory) / "vllm"
        target = package / rope.TARGET
        target.parent.mkdir(parents=True)
        target.write_bytes(text.encode("utf-8"))
        return package

    def test_the_pin_is_the_budget_patch_output(self):
        # sha256 of patch_image_budget.patch_text(`git show 385dce36:vllm/models/glm5next/nvidia/multimodal.py`).
        self.assertEqual(rope.TARGET, "models/glm5next/nvidia/multimodal.py")
        self.assertEqual(
            rope.SOURCE_SHA256,
            "f19440dce58d372d8869305865e29ade02a988a53a69e9320a2f68f944080788",
        )

    def test_the_command_writes_the_file_and_the_image_record(self):
        with tempfile.TemporaryDirectory() as directory:
            package = self.package(directory)
            digest = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
            with patch.object(rope, "SOURCE_SHA256", digest):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rope.main(["--package", str(package)])
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    rope.prepare(package)
            self.assertIn(
                "max_position=text_config.max_position_embeddings",
                (package / rope.TARGET).read_text(encoding="utf-8"),
            )
            record = json.loads((package.parent / rope.RECORD).read_text())
            self.assertEqual(record["source_sha256"], digest)

    def test_a_file_the_budget_patch_has_not_touched_is_refused_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            package = self.package(directory)
            with self.assertRaisesRegex(ValueError, "apply patch_image_budget first"):
                rope.main(["--package", str(package)])
            self.assertEqual(
                (package / rope.TARGET).read_bytes(), SOURCE.encode("utf-8")
            )


if __name__ == "__main__":
    unittest.main()
