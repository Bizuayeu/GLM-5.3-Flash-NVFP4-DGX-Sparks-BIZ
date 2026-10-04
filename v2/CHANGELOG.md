# Changelog

[日本語](CHANGELOG.ja.md) (this English file is canonical and the GitHub Release is made from it)

The 2.x line, served by TensorFold. A `v2.*` tag publishes its section from this file. The 1.x line's history is in [v1/CHANGELOG.md](../v1/CHANGELOG.md).

## 2.0.1 — 2026-10-04

### Documentation

- The [README](README.md) gains the sections a first reader needs; the existing ones are unchanged: a summary with the scope of the acceptance, requirements, a quick start for TP=2 with a `curl` request and a note that the engine has no authentication (rank 0 and the tool-argument gate listen on loopback only), the settings of the rank, cluster and container files in one table, the API the acceptance exercised beside the routes it did not check, the repository layout, licensing at a glance, a disclaimer, Next Action, and local data. Its headings are in title case.
- [Other Recipes on TensorFold](README.md#other-recipes-on-tensorfold): a table that owns the links of the public recipes serving GLM-5.3-Flash on TensorFold and what this line took from each. Upstream TensorFold; MiaAI-Lab's TensorFold recipe (the FP8 latent KV after its patch 0038, the TP=3 shares by the same rule as its patch 0066, its upstream pull request #301); jakejharris/jspark3 v2.0.1, from which nothing was taken. 1.x's table of recipes points here for MiaAI-Lab's TensorFold recipe (1.28.2).

The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

## 2.0.0 — 2026-10-04

The first release of the 2.x line. It serves the same pinned checkpoint as 1.x, `nvidia/GLM-5.3-Flash-NVFP4` at `423acf37583782c51c142d145aef733d72943d93`, with [TensorFold](https://github.com/ashhart/TensorFold) in place of vLLM, on two hosts at TP=2 or three hosts at TP=3. The 1.x line continues in [`v1/`](../v1/README.md).

### Engine

- The image builds TensorFold from the branch `release/2.0.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `b44c2f197863f889659874e9be4b8e318768a828` ([`TENSORFOLD_REF`](docker/Dockerfile)). That is upstream v0.6.4 with these additions for GLM-5.3-Flash on CUDA:
  - **NVIDIA's NVFP4 checkpoint read as stored**, W4A16: the routed experts and the dense MLP from its NVFP4 blocks, attention, the shared experts and the head in BF16 (upstream issue #308).
  - **FP8 latent KV** (`TF_GLM_KV=fp8`): the DSA latent cache and the indexer's pooled keys as e4m3 rows (upstream issue #309).
  - **TP=3** (`--tp 3`): one shard plan for two or three ranks, with unequal shares where a size does not divide by three, and vocabulary gathers over shards of unequal width (upstream issue #310).
  - **Prompt work that leaves the bits unchanged.**
    - BF16 prompt matmuls sum their K slices in registers (upstream pull request #333).
    - A prompt chunk's rank exchanges run in row pieces on a second stream.
    - The exchanges use an exact reduce-scatter in which each rank glues only its own rows (`split`, the default where ranks can send to each other).
    - The indexer scores 16 rows a program, scores only the pool columns its selection reads, and reads a long row three times instead of five for its top 512.
  - **A stopped request ends on every rank within a round**, when the client disconnects or a stop string appears (upstream pull request #301).
  - **A long prefill waits for heat.** Before every prompt chunk the ranks share their hottest thermal zone; above `TF_GLM_HEAT_HIGH` every rank waits together until all are at or below `TF_GLM_HEAT_LOW`. The wait moves when a chunk runs, not its bits. Each wait prints a `[tensorfold] heat:` line, and the reply reports `heat_wait_s` (upstream issue #339).

### Serving defaults

[`scripts/serve.sh`](scripts/serve.sh) sets them on every rank ([serving defaults](README.md#serving-defaults)):

- FP8 latent KV and the checkpoint's MTP head as the drafter (`--drafter none`).
- A window of 300,000 tokens at TP=2, which leaves the default 3 GiB for other conversations' kept prompts, and the largest that fits at TP=3: 1,048,576 tokens, the model's limit, on the reference ring.
- Replies of up to 32,768 tokens when a request names no limit.
- The prefill heat wait at 92 °C, resuming at 88 °C. The hosts' thermal watch stops an engine at 94 °C; without the wait, a 1M-token prompt at TP=3 reached that in six and a half minutes.

### Image and launch

- [`docker/Dockerfile`](docker/Dockerfile): NVIDIA's PyTorch container 26.07, transformers 5.18.0, xgrammar 0.2.8 and the Hugging Face hub client, the measured versions, plus the engine at its pinned commit. Build it from the checkout root ([setup](SETUP.md#3-image)).
- [`scripts/`](scripts/):
  - `create_container.sh` and `build_ext.sh`: the container and the engine's CUDA extensions on each host.
  - `serve.sh`: one rank.
  - `cluster.sh`: start and stop every rank from one machine, the other ranks first and rank 0 last.
  - `hostwatch.sh`: a memory guard that stops the engine through its container. The engine runs as root inside it.
- [`examples/`](examples/): the reference hosts' rank files for TP=2 and TP=3: two rails, GID 3, RoCE v2, subnet-aware routing and four channels at TP=3. `NCCL_DEBUG=INFO` makes NCCL log each connection's transport at start.

### Accepted

Measured on the reference hosts on 2026-10-04 ([measured](README.md#measured-on-the-release); [validation](docs/validation.md)). The decode check and the 1M-token prompt were run on the release image (`glm53-tf:2.0.0`, linux/arm64 image `sha256:3d06b02953398603580edcecef22c06c3c8ed0d9e3d1568d66f1bd0d1ae21b44`; the ID that `docker images` shows also covers the build's provenance and changes with each checkout it is built from) or the image one print change before it. The other items were run on the image of `304109c`, the branch before the heat wait, which only changes when prompt chunks run.

- The decode check gives the reference hashes at both TP sizes, also while heat waits were happening.
- Drafted replies equal serial ones.
- The teacher-forced NLL equals the development builds' at full precision.
- At TP=3, three passphrases in 1,036,859 tokens were found with the heat wait on: first token after 1,264.8 s, 170.1 s of it waiting, hottest reading 92.8 °C.
- tool-eval-bench through the tool-argument gate: 93/100 at TP=2 and 91/100 at TP=3, the Safety Gate passed at both.
