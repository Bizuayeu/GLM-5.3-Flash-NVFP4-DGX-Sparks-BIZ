# NVFP4 BIZ 2.x (TensorFold)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, without retraining or requantizing it, on DGX Spark or compatible GB10 systems. The name states that intent and does not depend on the engine. The 2.x line serves it with [TensorFold](https://github.com/ashhart/TensorFold) (Apache-2.0) in place of vLLM, on two hosts at TP=2 or three hosts at TP=3. 2.0.0 is its first release; the [1.x line](../v1/README.md) continues beside it.

## What it is

- **Weights**: `nvidia/GLM-5.3-Flash-NVFP4` at revision `423acf37583782c51c142d145aef733d72943d93`, the same as 1.x. The routed experts and the dense MLP run as W4A16 from the checkpoint's NVFP4 blocks; attention, the shared experts and the head stay BF16. One exception, inside the engine: the MTP layer's routed experts are BF16 in the checkpoint and are quantized to NVFP4 for drafting only. Every drafted token is verified by the full model, so replies are unchanged.
- **Engine**: the BIZ release of TensorFold, published as the branch `release/2.0.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): TensorFold v0.6.4 with the GLM NVFP4 loader, FP8 latent KV, the TP=3 split, prefill work that leaves the bits unchanged, upstream pull request #301 (a stopped request ends on every rank within a round), and a prefill that waits for heat between chunks. The image pins one commit of it ([`TENSORFOLD_REF`](docker/Dockerfile)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile), NVIDIA's PyTorch container 26.07 plus the measured package versions (transformers 5.18.0, xgrammar 0.2.8 for structured output, the Hugging Face hub client) and the engine.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order.

## Serving defaults

[`scripts/serve.sh`](scripts/serve.sh) holds them, the same on every rank:

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| KV cache | FP8 latent and pooled index keys (`TF_GLM_KV=fp8`) | same |
| Drafts | the checkpoint's MTP head (`--drafter none`: no DFlash2) | same |
| Window (`--context`) | 300,000 tokens | 0 = the largest that fits: 1,048,576 (the model's limit) on the reference ring |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| NCCL | two rails per link, from each rank's file | two rails, four channels, subnet-aware routing |
| Prefill exchange between ranks | the engine's default, `split` | same |
| Prefill pause for heat | between chunks, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_GLM_HEAT_HIGH`/`TF_GLM_HEAT_LOW`) | same |
| Kept prompts of other conversations | the engine's defaults: 8 entries, 3 GiB | same |

**Why 300,000 at TP=2.** With `--context 0` the pair took a window of 567,255 tokens and left nothing for other conversations' kept prompts, which matter for chat and agents that resend a long history. By the engine's own memory geometry, 300,000 tokens free about 3.3 GiB per rank against 567,255, enough for the default 3 GiB of kept prompts. 1.x serves 262,144; this window is not matched to it. Pass another `--context` to `serve.sh` to choose differently (the last flag wins); the most the pair holds is about 567K.

## Differences from 1.x

| | 1.x (vLLM) | 2.x (TensorFold) |
|---|---|---|
| Repeatable output | vLLM with the [repeatability switches](../v1/docs/server-configuration.md#repeatability-switches) on (one token order inside each expert, settled indexer top-k ties, Inductor configs chosen without timing) | the engine's contract: drafted replies equal serial ones, a resumed prompt equals a fresh one, and the result does not depend on the prompt chunking |
| KV and window | FP8, 262,144 tokens (3 GiB per rank) | FP8 latent and index keys, 300,000 tokens at TP=2 and 1,048,576 at TP=3 |
| Launch | `glm53_setup` reads one server TOML; `server preflight`, `cluster switch`, warmup ladder | the scripts here; no preflight or switch |
| Sequences in flight | one, or two with the published option's two-sequence profile | one |
| Image input | accepted | not accepted |
| Published AXL weights | optional | not supported |
| Tool calls | the model API, optionally behind the tool-argument gate | the same gate, run from `v1/` in front of the engine |
| Heat during a long prefill | outside the engine: the cooling gate between requests and the thermal watch | the engine waits between prompt chunks, every rank together, at 92 °C until 88 °C |

## Measured on the release

Taken on 2026-10-04 on the reference hosts (MSI EdgeXpert, GPU clock capped at 2,200 MHz). The engine was the branch at `b44c2f1` (the release), at `2d4fa9b` (one printed line before it) or at `304109c` (before the heat wait, which only changes when prompt chunks run); the notes say which. The [validation page](docs/validation.md) has the commands and reference values.

| Measurement | TP=2 | TP=3 | 1.x |
|---|---|---|---|
| Decode check count / prose / code (tok/s) | 41.04 / 26.73 / 34.85 | 52.47 / 37.99 / 48.47 | TP=2 defaults 32.59 / 21.12 / 28.21; TP=3 AXL 49.59 / 28.32 / 38.33 |
| MTP acceptance length, same tasks | 3.821 / 2.098 / 3.180 | 3.549 / 2.222 / 3.234 | — |
| Prefill of 38,960 tokens (tok/s, median of three, cooled before each) | 1,329.9 | 1,668.5 (1,671.4 with the heat wait off) | TP=2 defaults 1,233.4 |
| Decode after a short fixed prompt, 512 tokens (tok/s) | 35.31 | 52.93 | TP=2 defaults 27.18 |
| Window (tokens) | 300,000 (567,255 with `--context 0`) | 1,048,576 | 262,144 (TP=2) |
| Passphrase at 199,652 tokens | correct, first token after 163.7 s | correct, first token after 133.2 s | TP=3 AXL 150.5 s |
| Three passphrases at 1,036,859 tokens | — | 3 of 3, first token after 1,264.8 s, 170.1 s of it heat waits | TP=3 AXL 1,058 s |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5313 / 2.9001 / 1.3101 / 0.6237 | TP=2 defaults (1.26.0) 2.5412 / 2.9079 / 1.3145 / 0.6285 |
| tool-eval-bench through the tool-argument gate | 93/100, Safety Gate passed | 91/100, Safety Gate passed | TP=3 AXL 90/100 |
| A client disconnect or a stop string mid-reply | stops within a round, the next request starts at once | same | — |

- **Repeatability.** TP=2 and TP=3 do not give bit-identical outputs to each other or to 1.x, because the ranks split the sums differently. Each repeats itself: within a launch, across launches, with one or two rails, and with heat waits happening, the decode check gave one completion per task, the [reference hashes](docs/validation.md#decode-check). The NLL equals the development builds' at full precision.
- **Which engine.**
  - The decode check ran on `b44c2f1` at TP=2 and on `2d4fa9b` at TP=3.
  - The TP=3 prefill and the 1M-token prompt ran on `2d4fa9b`.
  - The other rows ran on `304109c`.
- **Heat.** During the 1M-token prompt the hottest host held at about 92 °C, waited about 80 times for a few seconds each, and peaked at 92.8 °C. Without the wait the same prompt reached 94 °C, where the thermal watch stops the engine, after six and a half minutes. Prefill also slows as a host heats: three 38,960-token prompts back to back fell from 1,670 to 1,540 tok/s, below the wait's threshold and with the clock unchanged. Cool the hosts between long requests.
- **tool-eval-bench** used the same 69 scenarios and invocation as 1.x's. Both TP sizes failed TC-61 only.

## Limits

- **One sequence at a time.** The engine's CUDA path decodes one GLM request at a time; the others wait their turn.
- **Text and tool calls only.** The engine refuses image input for GLM on CUDA (`GLM-5.3-Flash image input is currently MLX-only`).
- **TP=3 refuses DFlash2 and EXL3.** Both split only over two ranks. This line uses neither: `serve.sh` passes `--drafter none` and the checkpoint is NVFP4.
- **Streamed replies.** With drafts, one round can cross from thinking into the answer, so one delta can carry both `reasoning_content` and `content`. A client that reads only one field per delta loses text; non-streamed replies are whole.
- **FP8 KV is lossy** against BF16 KV, as in 1.x; drafted replies still equal serial ones. On four short texts the two caches gave NLL within 0.011 of each other (2026-10-02).
- **Two or three hosts with ConnectX-7 links**, as in 1.x. Other world sizes, other hardware and concurrent requests are outside what was measured.

## Licensing

[LICENSE](../LICENSE) (Apache-2.0), [NOTICE](../NOTICE) and [third-party notices](../THIRD_PARTY_NOTICES.md) at the repository root. The engine's own notices travel with its source in the image (`/opt/tensorfold`).
