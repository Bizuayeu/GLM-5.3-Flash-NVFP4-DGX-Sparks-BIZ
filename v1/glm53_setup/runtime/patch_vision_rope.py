"""Source-pinned patch: the vision rope table spans a slim image's grid.

vLLM 385dce36 builds GLM-5.3-Flash's vision rope with ``max_position=8192``, while the pinned
processor's ``smart_resize`` bounds an image by its token budget only, with no cap on the aspect
ratio. A slim image within the 8,000-token ceiling can have a grid side past 8,192 (upstream's
example: 200000 x 20 px is accepted at 7,143 tokens with ``image_grid_thw = [1, 2, 14286]``), and
``cos[pos_ids]`` reads past the table: a device-side assert that takes the engine down. The table is
sized from ``text_config.max_position_embeddings`` instead (1,048,576 rows for the checkpoint, about
64 MiB in bf16 a GPU); for every grid that fit the old table the tower's output is bit-identical.
The same change stages the two host-to-device copies of ``rot_pos_emb`` and the eager ``forward``
through pinned memory (``async_tensor_h2d``), which only matters under ``VLLM_GPU_SYNC_CHECK=error``
(this setup does not set it) and is carried so that the file matches upstream. Upstream:
vllm-project/vllm pull request #59126 (gaby, merged 2026-10-02 as ``0979892992``), Apache-2.0 as
vLLM; this is its change to ``vllm/models/glm5next/common/multimodal.py`` placed in the pinned
tree's ``models/glm5next/nvidia/multimodal.py``. The file is the one ``patch_image_budget`` already
rewrote, so its hash is that of the budget patch's output and this patch applies only after it.
"""

# cc-defer: carries an upstream fix that the pinned vLLM predates (v0.31.0 does not have it
# either); drop it (and the Dockerfile RUN) when the vLLM pin moves past 0979892992.

from . import pinned_patch
from .pinned_patch import replace_once

TARGET = "models/glm5next/nvidia/multimodal.py"
# As patch_image_budget leaves it (its SOURCE_SHA256 is the pinned file).
SOURCE_SHA256 = "f19440dce58d372d8869305865e29ade02a988a53a69e9320a2f68f944080788"
MISMATCH = "Glm5Next multimodal source hash mismatch (apply patch_image_budget first)"
RECORD = "glm53-vision-rope-patch.json"
HEADER = (
    "# Modified by GLM setup: the vision rope table spans a slim image's grid\n"
    "# (vllm-project/vllm #59126). Original vLLM Apache-2.0 notices below remain applicable.\n"
)
IMPORT_ANCHOR = "from vllm.multimodal.parse import ImageSize, MultiModalDataItems\n"
IMPORT = "from vllm.utils.torch_utils import async_tensor_h2d\n"
EDITS = (
    (
        "            max_position=8192,\n",
        "            max_position=text_config.max_position_embeddings,\n",
    ),
    (
        "        pos_ids = pos_ids.to(cos.device, non_blocking=True)\n",
        "        pos_ids = async_tensor_h2d(pos_ids, device=cos.device)\n",
    ),
    (
        "            cu_seqlens = cu_seqlens.to(self.device, non_blocking=True)\n",
        "            cu_seqlens = async_tensor_h2d(cu_seqlens, device=self.device)\n",
    ),
)


def patch_text(text):
    if "max_position=text_config.max_position_embeddings" in text:
        raise ValueError("Vision rope patch already applied")
    patched = replace_once(text, IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT)
    for old, new in EDITS:
        patched = replace_once(patched, old, new)
    patched = HEADER + patched
    compile(patched, TARGET, "exec")
    return patched


def prepare(package):
    return pinned_patch.prepare(package, TARGET, SOURCE_SHA256, MISMATCH, patch_text)


def main(argv=None):
    pinned_patch.main(
        argv,
        doc=__doc__,
        target=TARGET,
        sha256=SOURCE_SHA256,
        prepare=prepare,
        record=RECORD,
    )


if __name__ == "__main__":
    main()
