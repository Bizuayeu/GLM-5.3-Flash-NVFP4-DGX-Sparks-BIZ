#!/bin/bash
# Inside the container, on each host before the first start of an engine version: build (or find already built)
# every CUDA extension the GLM NVFP4 path loads, before any weight is read. TORCH_EXTENSIONS_DIR (/work/ext, on the
# host) keeps them across containers. A start that builds them lowered rank 0's free memory to 6-7 GiB, against
# about 9 GiB once built (2026-10-02), with the memory guard at 5 GiB.
set -eu
python3 - <<'PY'
import importlib
import time

MODULES = [
    ("tensorfold.cuda.experts", "_ext"),
    ("tensorfold.cuda.kernels.qmm", "_ext"),
    ("tensorfold.cuda.kernels.prefill_attention", "_ext"),
    ("tensorfold.cuda.nvfp4.checkpoint", "_ext"),
    ("tensorfold.cuda.nvfp4.linear", "_ext"),
    ("tensorfold.cuda.nvfp4.linear", "_prompt_ext"),
    ("tensorfold.families.glm5_next.cuda.kda", "_ext"),
]
for module, build in MODULES:
    start = time.time()
    getattr(importlib.import_module(module), build)()
    print(f"{module}.{build}: {time.time() - start:.1f} s", flush=True)
print("built")
PY
