"""Source-pinned patch: the image encoder cache is sized to the processor's token ceiling.

vLLM 385dce36 sizes the encoder cache from ``get_image_size_with_most_features``, which
GLM-5.3-Flash's processing info inherits as a square probe. With the checkpoint's ceiling of
8,000 image tokens the square refits to 89 x 89 = 7,921 tokens, so the boot log says
``Encoder cache will be initialized with a budget of 7921 tokens`` and an image the processor
turns into 7,922 to 8,000 tokens (a 4:3 phone photo, a 4K frame, an A4 scan at 300 dpi) is
refused with HTTP 400. The method below factors the ceiling exactly (80 x 100 = 8,000 for
the default budget). Upstream: vllm-project/vllm issue #59539, fixed by pull request #59565
(he-yufeng, merged 2026-10-02 as ``5688a4dd4a``), Apache-2.0 as vLLM; this is its change to
``vllm/models/glm5next/common/multimodal.py`` placed in the pinned tree's
``models/glm5next/nvidia/multimodal.py``, which holds the same class (its tests are not in
the image).
"""

# cc-defer: carries an upstream fix that the pinned vLLM predates; drop it (and the
# Dockerfile RUN) when the vLLM pin moves past 5688a4dd4a. patch_vision_rope's
# SOURCE_SHA256 is this patch's output: re-pin it then, or drop both together.

from . import pinned_patch
from .pinned_patch import replace_once

TARGET = "models/glm5next/nvidia/multimodal.py"
# As pinned (git show 385dce36:vllm/models/glm5next/nvidia/multimodal.py).
SOURCE_SHA256 = "896d9f133f97d338182f4880e2e7d3ac3b8def25ef7eaf82182f0ea01a3d72d7"
MISMATCH = "Glm5Next multimodal source hash mismatch"
RECORD = "glm53-image-budget-patch.json"
HEADER = (
    "# Modified by GLM setup: the image encoder cache sized to the token ceiling\n"
    "# (vllm-project/vllm #59565). Original vLLM Apache-2.0 notices below remain applicable.\n"
)

IMPORTS = '"""\n\nfrom collections.abc import Mapping\n'
MATH_IMPORT = '"""\n\nimport math\nfrom collections.abc import Mapping\n'
VIDEO_END = (
    "        return self._processor_pixel_budget(self.get_hf_processor().video_processor)[1]\n"
    "\n"
)
NEXT = "    def _get_vision_info(\n"
METHOD = """    def get_image_size_with_most_features(self) -> ImageSize:
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


def patch_text(text):
    if "def get_image_size_with_most_features" in text:
        raise ValueError("Image budget patch already applied")
    patched = replace_once(text, IMPORTS, MATH_IMPORT)
    patched = replace_once(patched, VIDEO_END + NEXT, VIDEO_END + METHOD + NEXT)
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
