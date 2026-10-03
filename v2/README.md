# NVFP4 BIZ 2.x (TensorFold)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, without retraining or requantizing it, on DGX Spark or compatible GB10 systems. The name states that intent and does not depend on the engine. The 2.x line serves it with [TensorFold](https://github.com/ashhart/TensorFold) (Apache-2.0) in place of vLLM, on two hosts at TP=2 or three hosts at TP=3. It is being prepared for 2.0.0 and has no release yet; until then the [1.x line](../v1/README.md) is the released one.

## What it is

- **Weights**: `nvidia/GLM-5.3-Flash-NVFP4` at revision `423acf37583782c51c142d145aef733d72943d93`, the same as 1.x. The routed experts and the dense MLP run as W4A16 from the checkpoint's NVFP4 blocks; attention, the shared experts and the head stay BF16. One exception, inside the engine: the MTP layer's routed experts are BF16 in the checkpoint and are quantized to NVFP4 for drafting only. Every drafted token is verified by the full model, so replies are unchanged.
- **Engine**: the BIZ release of TensorFold, published as the branch `release/2.0.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): TensorFold v0.6.4 with the GLM NVFP4 loader, FP8 latent KV, the TP=3 split, prefill work that leaves the bits unchanged, and upstream pull request #301 (a stopped request ends on every rank within a round). The image pins one commit of it ([`TENSORFOLD_REF`](docker/Dockerfile)).
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

## Measured so far

The figures below were taken on 2026-10-02 and 10-03 on the reference hosts (MSI EdgeXpert, GPU clock capped at 2,200 MHz) with **development builds** of the engine before the release branch (TensorFold v0.6.1 to v0.6.3 with the BIZ work). The release engine (v0.6.4 and #301) is accepted again item by item before 2.0.0 ([validation](docs/validation.md)); these are the values it is compared with.

| Measurement | TP=2 | TP=3 | 1.x |
|---|---|---|---|
| Decode check count / prose / code (tok/s) | 41.16 / 26.82 / 34.87 | 52.90 / 38.29 / 48.66 | TP=2 defaults 32.59 / 21.12 / 28.21; TP=3 AXL 49.59 / 28.32 / 38.33 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,217.2 (two rails, `gather`) | 1,673.1 and 1,667.9 (two launches, `split`) | TP=2 defaults 1,233.4 |
| Decode after a short fixed prompt, 512 tokens (tok/s) | 35.61 | 53.03 and 52.93 | TP=2 defaults 27.18 |
| Window with `--context 0` (tokens) | 567,255 | 1,048,576 | 262,144 (TP=2) |
| Passphrase at 199,652 tokens | not measured on the current prefill | correct, 145.6 s | TP=3 AXL 150.5 s |
| Three passphrases at 499,622 tokens | — | 3 of 3, 454.1 s | — |
| Three passphrases at 1,036,859 tokens | — | 3 of 3, first token after 1,364 s (before the `split` exchange and the indexer work) | TP=3 AXL 1,058 s |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5313 / 2.9001 / 1.3101 / 0.6237 | TP=2 defaults (1.26.0) 2.5412 / 2.9079 / 1.3145 / 0.6285 |
| tool-eval-bench through the tool-argument gate | 91/100, Safety Gate passed | 91/100, Safety Gate passed | TP=3 AXL 90/100 |

- TP=2 and TP=3 do not give bit-identical outputs to each other or to 1.x: the ranks split the sums differently. Each repeats itself: within a launch, across launches and with one or two rails, the decode check gave one completion per task ([reference hashes](docs/validation.md#decode-check)).
- The TP=2 prefill and decode rows come from the build before the last TP=2 development build, with two rails and the `gather` exchange (`split` was not the default yet); the last build gave 1,168.6 tok/s prefill on one rail, and its decode check is the row above. The NLL set is the one in [`v1/config/nll_set.json`](../v1/config/nll_set.json), four domains of about 6,000 tokens each.
- tool-eval-bench: the same 69 scenarios and invocation as 1.x's. Without the gate TP=2 scored 89/100 with TC-43 failing the Safety Gate, the same three failures as 1.x's distributed defaults.

## Limits

- **One sequence at a time.** The engine's CUDA path decodes one GLM request at a time; the others wait their turn.
- **Text and tool calls only.** The engine refuses image input for GLM on CUDA (`GLM-5.3-Flash image input is currently MLX-only`).
- **TP=3 refuses DFlash2 and EXL3.** Both split only over two ranks. This line uses neither: `serve.sh` passes `--drafter none` and the checkpoint is NVFP4.
- **FP8 KV is lossy** against BF16 KV, as in 1.x; drafted replies still equal serial ones. On four short texts the two caches gave NLL within 0.011 of each other (2026-10-02).
- **Two or three hosts with ConnectX-7 links**, as in 1.x. Other world sizes, other hardware and concurrent requests are outside what was measured.

## Licensing

[LICENSE](../LICENSE) (Apache-2.0), [NOTICE](../NOTICE) and [third-party notices](../THIRD_PARTY_NOTICES.md) at the repository root. The engine's own notices travel with its source in the image (`/opt/tensorfold`).
