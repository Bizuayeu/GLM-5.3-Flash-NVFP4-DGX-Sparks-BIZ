# NVFP4 BIZ 2.x (TensorFold)

![NVFP4 BIZ v2 on TensorFold: repeatable inference on two or three nodes, a 300K-token window at TP=2 and 1M at TP=3](assets/banner.png)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, without retraining or requantizing it, on DGX Spark or compatible GB10 systems. The name states that intent and does not depend on the engine. The 2.x line serves it with [TensorFold](https://github.com/ashhart/TensorFold) (Apache-2.0) in place of vLLM, on two hosts at TP=2 or three hosts at TP=3. 2.0.0 is its first release; the [1.x line](../v1/README.md) continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

- **What it is.** Build steps, launch scripts and acceptance checks that serve the pinned checkpoint through a pinned TensorFold commit as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, or three at TP=3 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems.
- **Status.** 2.0.0 was accepted on the reference hosts on 2026-10-04 against the reference values of [validation](docs/validation.md), at both TP sizes ([measured on the release](#measured-on-the-release)). Each later image was accepted against the same reference values, at the TP sizes and with the checks its [changelog](CHANGELOG.md) section names; the current one, 2.1.4's, at TP=2 with image input on ([measured on the release](#measured-on-the-release)). That is the scope of the claim; other hosts are qualified by running the same checks.
- **Repeatable by contract.** Drafted replies equal serial ones, a resumed prompt equals a fresh one, and the result does not depend on how the prompt is chunked. These are the engine's contract, where 1.x buys repeatability with switches on vLLM ([differences from 1.x](#differences-from-1x)).
- **Precision.** W4A16 for the routed experts and the dense MLP, BF16 elsewhere, FP8 KV. NVIDIA's model card measured its checkpoint under another recipe on other hardware, so its accuracy table does not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine, MIT weights that the operator downloads, nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** More than one sequence at a time, image input beyond [the checks run](#measured-on-the-release), the published AXL weights, harness integration (ZCode, Claude Code), other world sizes and hardware, full application quality and production reliability ([limits](#limits)).

## What It Is

- **Weights**: `nvidia/GLM-5.3-Flash-NVFP4` at revision `423acf37583782c51c142d145aef733d72943d93`, the same as 1.x, derived from [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash). The routed experts and the dense MLP run as W4A16 from the checkpoint's NVFP4 blocks; attention, the shared experts and the head stay BF16. One exception, inside the engine: the MTP layer's routed experts are BF16 in the checkpoint and are quantized to NVFP4 for drafting only. Every drafted token is verified by the full model, so replies are unchanged.
- **Engine**: the BIZ release of TensorFold, published as the branch `release/2.1.4` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): TensorFold v0.6.5 with the GLM NVFP4 loader, FP8 latent KV, the TP=3 split, prefill work that leaves the bits unchanged, upstream pull request #301 (a stopped request ends on every rank within a round), a prefill that waits for heat between chunks, image input from upstream pull request #194, carried to three ranks, and upstream pull request #421 (a new conversation no longer copies and drops the kept prompts first). The image pins one commit of it ([`TENSORFOLD_REF`](docker/Dockerfile)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile), NVIDIA's PyTorch container 26.07 plus the measured package versions (transformers 5.18.0, xgrammar 0.2.8 for structured output, the Hugging Face hub client) and the engine.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order.

## Requirements

- **Hosts**: two or three DGX Spark or compatible GB10 systems (Linux ARM64, 128 GB unified memory each) with nothing else large on their GPUs. A 1.x server on the same hosts is stopped first.
- **Fabric**: ConnectX-7 links with RoCE v2, a direct cable for the pair or a switchless ring for three hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring)). Both rails of each port are used.
- **Host kernel**: as in 1.x; the default of current DGX OS updates can break multi-node RoCE ([host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce)).
- **GPU clock** capped on every host, as in 1.x ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)); [`host/`](../host/README.md) installs the cap and a telemetry logger. Every 2.x figure was measured under the cap.
- **Docker** with NVIDIA's GPU runtime and the RDMA devices (`create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets).
- **Disk**: the whole checkpoint on every host, as in 1.x ([what you deploy](../v1/README.md#what-you-deploy-and-supported-hardware)), plus the image.
- **A control machine** with SSH to every host, for `cluster.sh`.
- **Python 3.11+** on the hosts for this line's tools in [`glm53_tf/`](glm53_tf/) (download, verification, tool-argument gate, checks), run from `v2/` ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

## Quick Start

The steps, with what to check after each, are the [setup runbook](SETUP.md); this is their outline for TP=2. Use the same reviewed `v2.*` tag on every host.

```sh
# Once, from v2/ on one host in its virtual environment; then copy the cache to the others and verify each copy (SETUP §2)
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait

# Each host, from the checkout root (SETUP §3-§5); build once and `docker load` it elsewhere, then compare image IDs
docker build -f v2/docker/Dockerfile -t glm53-tf:2.1.4 .
v2/scripts/create_container.sh glm53-tf:2.1.4
cp v2/examples/tp2-rank0.env ~/glm53-tf/rank.env      # tp2-rank1 on the other host; then put this host's values
docker exec glm53-tf bash /opt/glm53-tf/build_ext.sh

# The control machine (SETUP §6, §9)
mkdir -p state && cp v2/examples/cluster.tp2.env state/cluster.env  # HOSTS in rank order, CHECKOUT
v2/scripts/cluster.sh state/cluster.env start first    # "first" labels the logs; READY after rank 0's serving line
v2/scripts/cluster.sh state/cluster.env stop
```

Rank 0 then answers on loopback:

```sh
curl -s http://127.0.0.1:8095/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "glm-tf",
  "messages": [{"role": "user", "content": "Write a Python fibonacci function."}]
}'
```

The model thinks before it answers: the reasoning comes back in `reasoning_content` and the answer in `content`, and a request that names no `max_tokens` gets 32,768 tokens for both; a smaller limit can end inside the thinking with an empty `content`. Accept a new launch with the [validation](docs/validation.md) checks, the decode check first, before routine use.

**Security.** `serve.sh` binds rank 0 to `127.0.0.1`, and the [tool-argument gate](SETUP.md#7-tool-argument-gate-optional) also listens on loopback only; reach them through an SSH tunnel (`ssh -L 8095:127.0.0.1:8095 <rank 0>`) or a proxy that adds authentication. To serve beyond loopback (`HOST=0.0.0.0` in the rank file), set an API key too: a line `TENSORFOLD_API_KEY=<key>` in rank 0's rank file (the example has it commented out) makes the engine refuse every request without `Authorization: Bearer <key>`, `/metrics` included, while `/health` stays open. This line's decode check, `score-nll`, `bench` and `long-input` send the key when `TENSORFOLD_API_KEY` is set where they run, and the tool-argument gate passes the header on. The key is a secret in a plain file: keep the rank file readable by its owner only (`chmod 600`). Without a key, `HOST=0.0.0.0` exposes the API unauthenticated.

## Serving Defaults

[`scripts/serve.sh`](scripts/serve.sh) holds them, the same on every rank:

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| KV cache | FP8 latent and pooled index keys (`TF_GLM_KV=fp8`) | same |
| Drafts | the checkpoint's MTP head (`--drafter none`: no DFlash2) | same |
| Window (`--context`) | 300,000 tokens | 0 = the largest that fits: 1,048,576 (the model's limit) on the reference ring |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| NCCL | two rails per link, four channels, the IB transport named, from each rank's file | two rails, four channels, the IB transport named, subnet-aware routing |
| Image input | on: `VISION=1` in every rank file adds `--vision`; rank 0 holds the image tower (1.05 GiB), and other conversations' kept prompts get 2.4 GiB of the 3 GiB | on; the kept prompts keep 3 GiB |
| Prefill exchange between ranks | the engine's default, `split` | same |
| Prefill pause for heat | between chunks, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_GLM_HEAT_HIGH`/`TF_GLM_HEAT_LOW`) | same |
| Kept prompts of other conversations | the engine's defaults: 8 entries, 3 GiB | same |

**Why 300,000 at TP=2.** With `--context 0` the pair took a window of 567,255 tokens and left nothing for other conversations' kept prompts, which matter for chat and agents that resend a long history. By the engine's own memory geometry, 300,000 tokens free about 3.3 GiB per rank against 567,255, enough for the default 3 GiB of kept prompts. 1.x serves 262,144; this window is not matched to it. Pass another `--context` to `serve.sh` to choose differently (the last flag wins); the most the pair holds is about 567K.

## Configuration

Three places set a deployment. Copy the two files from [`examples/`](examples/), put your own values and keep them out of Git.

| Where | Setting | Default | Meaning |
|---|---|---|---|
| Rank file (`/work/rank.env`, sourced by `serve.sh`) | `MASTER` | none, required | rank 0's address on the link, the same on every rank |
| | `NCCL_IB_HCA`, `NCCL_IB_GID_INDEX`, `NCCL_SOCKET_IFNAME` | the reference hosts' values | the RDMA devices on the links (both rails), the RoCE v2 GID index, the bootstrap interface |
| | `NCCL_NET`, `NCCL_IB_DISABLE`, `NCCL_IB_ROCE_VERSION_NUM`, `NCCL_IB_ADDR_FAMILY`, `NCCL_SOCKET_FAMILY`, `NCCL_MIN_NCHANNELS`, `NCCL_MAX_NCHANNELS` | NCCL's IB transport over RoCE v2 and IPv4, four channels | named so that NCCL does not fall back to sockets unseen; four channels gave TP=2 decode +1% and more room at start ([decisions](docs/decisions.md#fabric)); TP=3 adds subnet-aware routing and `NCCL_NET_PLUGIN=none`, NCCL's own IB transport ([`tp3-rank0.env`](examples/tp3-rank0.env)) |
| | `VISION` | `1` in the examples (`0` when unset) | image input (`serve.sh` adds `--vision`); `0` turns it off; the same on every rank |
| | `NCCL_DEBUG`, `NCCL_DEBUG_SUBSYS` | `INFO`, `INIT,NET` | NCCL logs each connection's transport once at start, which [SETUP §6](SETUP.md#6-start) reads |
| | `MODEL_NAME`, `HOST`, `PORT` | `glm-tf`, `127.0.0.1`, `8095` | rank 0's model id and listener |
| | `CHECKPOINT` | the pinned snapshot under `/hub` | the checkpoint directory inside the container |
| | `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW` | `92`, `88` (°C) | the prefill heat wait; the same on every rank, empty for none |
| | `TF_GLM_CACHE_GIB` | `3` (the engine's) | the most memory per rank for other conversations' kept prompts, out of what the window leaves; the same on every rank |
| | `TF_GLM_CACHE_ENTRIES` | `8` (the engine's) | kept prompts of other conversations; the decode check must be told another value ([decode check](docs/validation.md#decode-check)) |
| `serve.sh` arguments | after `TP RANK RANK_ENV` | none | passed to `tensorfold serve` after the defaults, so they win (`--context 500000`) |
| Cluster file (`cluster.sh`) | `TP`, `HOSTS`, `CHECKOUT` | none, required | the TP size, SSH names in rank order, this repository's root on every host (1.x's `--checkout` names its `v1/` instead) |
| | `SSH`, `CONTAINER`, `WORK` | `ssh -o ConnectTimeout=20`, `glm53-tf`, `$HOME/glm53-tf` | how to reach the hosts, the container, the host directory at `/work` |
| `create_container.sh` | `IMAGE [WORK_DIR]`, `CONTAINER`, `HF_HUB` | `~/glm53-tf`, `glm53-tf`, `~/.cache/huggingface/hub` | the image, the work directory (rank file, extensions, logs), the container name, the Hugging Face cache mounted read-only at `/hub` |

The rank file is sourced by `bash` with every variable exported, so any other `TF_GLM_*` or `NCCL_*` setting in it reaches the engine. Settings outside this table were not measured on this line.

## API

Rank 0 serves the engine's HTTP API. What the acceptance exercised:

- **`/v1/chat/completions`**, streamed and not, with tools and structured output (tool-eval-bench's TC-64 to TC-69, which need xgrammar in the image), through the [tool-argument gate](SETUP.md#7-tool-argument-gate-optional).
- **Thinking**: `chat_template_kwargs.reasoning_effort` and `clear_thinking`, as the checks send them. A streamed delta can carry both `reasoning_content` and `content` ([limits](#limits)).
- **`"draft": false`** in the request body decodes one token a round, the serial reference that drafted replies must equal.
- **The reply's `tensorfold` block**: `accepted` and `rounds` (MTP acceptance), `cached` (prompt tokens resumed from a kept prompt) and `heat_wait_s`.
- **`/health`** (the decode `rounds`, among others) and **`/metrics`**, which the decode check reads to tell the engines apart.
- **Stopping**: a client disconnect or a stop string ends the decode on every rank within a round.
- **Images** (`VISION=1`): `image_url` parts as data URLs, in user messages and in tool results; a video part is refused with 400.

The NLL check also uses **`/v1/models`** (the model it scores) and **`/v1/completions`** (teacher-forced, with `prompt_logprobs`). The engine also routes `/v1/responses`, Anthropic's `/v1/messages` and `/tokenize`; 2.0.0's acceptance did not check them.

## Differences from 1.x

| | 1.x (vLLM) | 2.x (TensorFold) |
|---|---|---|
| Repeatable output | vLLM with the [repeatability switches](../v1/docs/server-configuration.md#repeatability-switches) on | the engine's contract: drafted replies equal serial ones, a resumed prompt equals a fresh one, and the result does not depend on the prompt chunking |
| KV and window | FP8, 262,144 tokens (3 GiB per rank) | FP8 latent and index keys, 300,000 tokens at TP=2 and 1,048,576 at TP=3 |
| Launch | `glm53_setup` reads one server TOML; `server preflight`, `cluster switch`, warmup ladder | the scripts here; no preflight or switch |
| Sequences in flight | one, or two with the published option's two-sequence profile | one |
| Image input | accepted | accepted (`VISION=1` in the example rank files) |
| Published AXL weights | optional | not supported |
| Tool calls | the model API, optionally behind the tool-argument gate | the same gate, this line's copy run from `v2/`, in front of the engine |
| Heat during a long prefill | no wait in the engine; its measurements rested the hosts between requests with a cooling gate, the one [`host/`](../host/README.md#during-long-runs) now holds | the engine waits between prompt chunks, every rank together, at 92 °C until 88 °C |

Why each 2.x setting was chosen, and what was tried and not adopted, is in [decisions](docs/decisions.md).

## Measured on the Release

**2.1.4** (2026-10-06, engine `a265436`, image `glm53-tf:2.1.4`). A new conversation after a long one no longer copies and drops the kept prompts first (TensorFold pull request #421). At TP=2 with image input on, the decode check gave 2.1.1's token ids and texts and the image checks passed; after a conversation of 247,330 tokens over 11 turns, a new one kept `MemAvailable` at 11–12 GiB on rank 0 and 12–15 GiB on rank 1.

**2.1.1** (2026-10-05, engine `1a3fb17`, image `glm53-tf:2.1.1`). Each image of a request is its own call of the image tower. At TP=2 with image input on, the decode check gave 2.1.0's token ids, texts and acceptance lengths, and the image checks passed, with two images of one size read alike one at a time and together.

| 2.1.1, TP=2, image input on | |
|---|---|
| Decode check count / prose / code (tok/s) | 41.62 / 27.03 / 35.37 |
| Prefill of 38,960 tokens, three back to back without cooling (tok/s) | 1,327.0 / 1,326.8 / 1,322.8 |

**2.1.0** (2026-10-05, engine `9a1c7cc`, image `glm53-tf:2.1.0`). The engine moved onto upstream v0.6.5 and gained image input; TP=2 took four NCCL channels. At both TP sizes the decode check gave 2.0.0's token ids and acceptance lengths ([validation](docs/validation.md#decode-check) gives its texts' new hashes), with image input off and on; at TP=2 the NLL set equalled 2.0.0's at full precision. The rows below are 2.0.0's unless the table says otherwise; the other measurements were not repeated, since the prompt and decode paths give the same tokens.

| 2.1.0 | TP=2 | TP=3 |
|---|---|---|
| Decode check count / prose / code (tok/s) | 41.67 / 27.02 / 35.38 | 52.37 / 37.92 / 48.41 (image input on) |
| Prefill of 38,960 tokens (tok/s, the second and third of three; the first 1,221.5) | 1,331.1 / 1,329.9 | — |
| [Image checks](docs/validation.md#image-input) (`VISION=1`) | all passed | all passed |

**2.0.0.** Taken on 2026-10-04 on the reference hosts (MSI EdgeXpert, GPU clock capped at 2,200 MHz). The engine was the release (`b44c2f1`), the build one printed line before it, or a build before the heat wait, which only changes when prompt chunks run; the notes say which. The [validation page](docs/validation.md) has the commands and reference values. The 1.x column is from [1.x's benchmarks](../v1/docs/benchmarks.md), its NLL from [the NLL set on 1.26.0's defaults](../v1/docs/benchmarks.md#the-nll-set-on-1260s-distributed-defaults-2026-10-02).

| Measurement | TP=2 | TP=3 | 1.x |
|---|---|---|---|
| Decode check count / prose / code (tok/s) | 41.04 / 26.73 / 34.85 | 52.47 / 37.99 / 48.47 | TP=2 defaults 32.59 / 21.12 / 28.21; TP=3 AXL 51.00 / 30.10 / 39.48 |
| MTP acceptance length, same tasks | 3.821 / 2.098 / 3.180 | 3.549 / 2.222 / 3.234 | — |
| Prefill of 38,960 tokens (tok/s, median of three; TP=3 cooled before each, TP=2 back to back after one cooling) | 1,329.9 | 1,668.5 (1,671.4 with the heat wait off) | TP=2 defaults 1,233.4 (38,962 tokens) |
| Decode after a short fixed prompt, 512 tokens (tok/s) | 35.31 | 52.93 | TP=2 defaults 27.18 |
| Window (tokens) | 300,000 (567,255 with `--context 0`) | 1,048,576 | 262,144 (TP=2) |
| Passphrase at 199,652 tokens | correct, first token after 163.7 s | correct, first token after 133.2 s | TP=3 AXL 150.5 s |
| Three passphrases at 1,036,859 tokens | — | 3 of 3, first token after 1,264.8 s, 170.1 s of it heat waits | TP=3 AXL 1,058 s (1,038,423 tokens) |
| Teacher-forced NLL on the NLL set (`config/nll_set.json`), ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5313 / 2.9001 / 1.3101 / 0.6237 | TP=2 defaults (1.26.0) 2.5412 / 2.9079 / 1.3145 / 0.6285 |
| tool-eval-bench through the tool-argument gate | 93/100, Safety Gate passed | 91/100, Safety Gate passed | TP=2 AXL 90/100 |
| A client disconnect or a stop string mid-reply | stops within a round, the next request starts at once | same | — |

- **Repeatability.** TP=2 and TP=3 do not give bit-identical outputs to each other or to 1.x, because the ranks split the sums differently. Each repeats itself: within a launch, across launches, with one or two rails, and with heat waits happening, the decode check gave one completion per task, the [reference hashes](docs/validation.md#decode-check). The NLL equals the [reference values](docs/validation.md#teacher-forced-nll), taken on builds before the release, at full precision.
- **Which engine.**
  - The decode check ran on the release at TP=2 and on the build one printed line before it at TP=3.
  - The TP=3 prefill and the 1M-token prompt ran on the build one printed line before the release.
  - The other rows ran on the build before the heat wait.
- **Heat.** During the 1M-token prompt the hottest host held at about 92 °C, waited about 80 times for a few seconds each, and peaked at 92.8 °C. Without the wait the same prompt reached 94 °C after six and a half minutes, and the [thermal watch](../host/README.md#during-long-runs) stopped the engine. Prefill runs at one of two speeds about 7.5% apart, and heat does not explain which ([prefill and decode speed](docs/validation.md#prefill-and-decode-speed)). Cool the hosts between long requests.
- **tool-eval-bench** used the same 69 scenarios and invocation as 1.x's. Both TP sizes failed TC-61 only.

## Limits

- **One sequence at a time.** The engine's CUDA path decodes one GLM request at a time; the others wait their turn.
- **Images take memory at TP=2.** With image input on, the tower takes part of the memory for other conversations' kept prompts ([serving defaults](#serving-defaults)); `VISION=0` on every rank gives the 3 GiB back.
- **TP=3 refuses DFlash2 and EXL3.** Both split only over two ranks. This line uses neither: `serve.sh` passes `--drafter none` and the checkpoint is NVFP4.
- **Streamed replies.** With drafts, one round can cross from thinking into the answer, so one delta can carry both `reasoning_content` and `content`. A client that reads only one field per delta loses text; non-streamed replies are whole.
- **FP8 KV is lossy** against BF16 KV, as in 1.x; drafted replies still equal serial ones. On four short texts the two caches gave NLL within 0.011 of each other (2026-10-02).
- **Two or three hosts with ConnectX-7 links**, as in 1.x. Other world sizes, other hardware and concurrent requests are outside what was measured.

## Repository Layout

The 2.x files live in `v2/`. The image is built from the checkout root, where the licenses are; the Python tools run from `v2/` as `python -m glm53_tf <command>`. The host tools and the host and fabric pages every line shares are at the checkout root ([`host/`](../host/README.md), [`docs/`](../docs/README.md)).

```
v2/
  README.md         this page (each .md has a .ja.md beside it)
  SETUP.md          the deployment runbook
  CHANGELOG.md      the 2.x releases; a v2.* tag publishes its section
  glm53_tf/         the Python tools: download, verify-download, tool-gate,
                    decode-check, decode-divergence, score-nll, bench, long-input
  config/           model.lock.json (the pinned checkpoint), nll_set.json (the NLL set, a byte copy of 1.x's)
  requirements/     huggingface.lock.txt: the Hugging Face client for the download and its verification
  docker/           Dockerfile: the image, with the engine pinned by TENSORFOLD_REF
  scripts/          create_container.sh  the serving container on each host
                    build_ext.sh         the engine's CUDA extensions, once per image
                    serve.sh             one rank, with the serving defaults
                    cluster.sh           start, stop and status of every rank from a control machine
                    hostwatch.sh         the memory guard (stops the engine below 5 GiB MemAvailable)
  examples/         the reference hosts' rank files and cluster files, TP=2 and TP=3
  docs/             validation.md  the acceptance checks and reference values
                    benchmarks.md  how the release figures were taken
                    operations.md  failures and routine changes: a rank that stops, a new image, handing hosts to 1.x
                    decisions.md   what was tried for 2.x, adopted or rejected, and why
  tests/            CPU tests of glm53_tf/ and of the facts these pages quote
  pyproject.toml    the 2.x version
```

## Other Recipes on TensorFold

Public recipes that serve GLM-5.3-Flash on TensorFold. This table owns their links, their licenses as read on 2026-10-04 and what this line took from each; the recipes on other engines are in [1.x's table](../v1/README.md#other-glm-53-flash-recipes-for-dgx-spark-systems). Their measurements use other weights and settings and do not compare with the ones above.

| Recipe | License | What this line took from it |
|---|---|---|
| [ashhart/TensorFold](https://github.com/ashhart/TensorFold) | Apache-2.0 (MIT up to 0.5.0) | The engine. The release branch is upstream v0.6.5 plus its own commits, offered back as upstream issues #308, #309, #310 and #339 and pull request #333 |
| [MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold) | Apache-2.0 | The FP8 latent KV follows its patch 0038, rewritten on v0.6.x and credited in the engine's notices (upstream issue #309). The TP=3 shares use the same rule as its patch 0066 (cut at unit boundaries, the remainder to the lower ranks). Its upstream pull request #301 (a stopped request ends on every rank) is in the release as it is. It serves its own EXL3 checkpoint with DFlash2 drafts, up to eight requests at once and image and video input |
| [jakejharris/jspark3 v2.0.1](https://github.com/jakejharris/jspark3/releases/tag/v2.0.1) | Apache-2.0 (recipe); MIT (its engine, a fork of TensorFold 0.3.6.2) | Nothing. Three hosts at TP=3 on its own TensorFold fork with 4-bit MLX-format weights split across the hosts, DFlash2 drafts by default with `--drafter none` as its commercial path, a session cache on disk, measured with RigMark |

## Disclaimer

- **BIZ is an intent, not a promise** ([repository README](../README.md#biz)).
- **The acceptance is the reference hosts'.** A launch elsewhere, or on another image ID, is accepted by running [validation](docs/validation.md) there.
- **The engine is a fork until upstream takes its commits.** The issues and pull requests above are open upstream; the release branch carries them meanwhile.

## Next Action

Each item is a trigger and what this line then does.

- Upstream merges pull request [#320](https://github.com/ashhart/TensorFold/pull/320) (both ranks stop a GLM reply when its caller asks, in review for 0.6.6 as of 2026-10-04) or #301 → take upstream's stop in place of the release branch's #301, rebase onto that release, accept the image again and move `TENSORFOLD_REF` in a 2.x release.
- Upstream takes the work of issues #308, #309, #310, #339 or pull request #333 (none is on upstream's list for 0.6.6 as of 2026-10-04) → rebase the release branch onto that upstream release, drop what upstream now carries, accept the image again and move `TENSORFOLD_REF` in a 2.x release.
- Upstream releases 0.6.6 (under test as of 2026-10-04: unoffered `<tool_call>` markup leaking into the reply text, #285 with #256; `--loop-guard` against a token repeated without end, #210 and #262 for #204; the open-file limit raised at start, #294) → read it against the release branch and follow it in a 2.x release.
- Upstream pull request [#243](https://github.com/ashhart/TensorFold/pull/243) (`--parallel N` on two ranks) merges → take up more than one sequence at a time.
- Upstream merges pull request [#194](https://github.com/ashhart/TensorFold/pull/194) (GLM-5.3-Flash image input on CUDA over two ranks), which the release branch carries with three ranks added → take upstream's in its place and accept the image input again.
- The published AXL weights on 2.x: on hold after 2.0.0; 2.x serves the pinned weights only.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 2.x changes.
