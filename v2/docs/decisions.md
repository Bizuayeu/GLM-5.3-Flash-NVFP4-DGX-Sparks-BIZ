# Decisions (2.x)

[日本語](decisions.ja.md) · [2.x overview](../README.md) · [Validation](validation.md) · [Benchmark method](benchmarks.md)

What was tried for the 2.x line, what was adopted or rejected, when, with the measured effect and what would reopen it: the 2.x counterpart of 1.x's [optimization catalog](../../v1/docs/optimization-catalog.md). The effects were measured on the reference hosts under the GPU clock cap, on the development build where each decision was taken, at TP=2 on the pair unless the row says TP=3; prefill is the median of three 38,960-token prompts ([benchmark method](benchmarks.md)). The release's own figures are in [measured on the release](../README.md#measured-on-the-release) and the reference values in [validation](validation.md). "—" means nothing recorded would reopen the decision.

## Engine

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| Serve with TensorFold in place of vLLM | 2026-10-02 | Exactness is the engine's contract (drafted equals serial, resumed equals fresh, the result does not depend on the chunking), where 1.x buys repeatability by turning vLLM's switches on ([differences from 1.x](../README.md#differences-from-1x)) | — |
| Start from upstream TensorFold and port only what GLM needs, not build on MiaAI-Lab's TensorFold recipe | 2026-10-02 | Its FP8 latent KV (patch 0038) sat on about 37 earlier patches; a dry run onto upstream 0.6.1 failed nearly every hunk, so it was rewritten on upstream (about 600 lines) | — |
| Follow upstream releases, upstream's side winning a conflict | 2026-10-03 | v0.6.2, v0.6.3, then v0.6.4, where the TP=3 exchanges were rebuilt on upstream's communicator interface (#219). The stop on every rank is upstream pull request #301 taken as it is, rather than written anew | Upstream merges #320 or #301, or takes this line's issues and #333 ([Next Action](../README.md#next-action)) |

## Precision and memory

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| FP8 latent KV (`TF_GLM_KV=fp8`) with a power-of-two scale per row | 2026-10-02 | The KV of a token takes 12,912 bytes a rank across the 12 layers with a latent cache (11 DSA layers and the MTP layer), against 19,200 with BF16 KV (−33%); the TP=2 window with BF16 KV was 344,820 tokens against about 490K with FP8 on that build. Drafted replies still equal serial ones; lossy against BF16 KV ([limits](../README.md#limits)). The checkpoint declares FP8 KV but stores no KV scale (vLLM uses 1.0), hence the per-row scale. The indexer ring of the same patch (keys and gates in a ring) was not ported: it changes the BF16 default's layout | More window per rank is needed; the ring is the next step |
| Routed experts and the dense MLP as W4A16; `--precision checkpoint` refused | 2026-10-02 | Upstream's grouped NVFP4 expert kernel takes BF16 rows only, with no input-scale path; in the pinned checkpoint the activation scales would change only dense layers 0-2 | — |
| The MTP layer's routed experts quantized to NVFP4 for drafting only | 2026-10-02 | BF16 in the checkpoint (13.5 GiB): 6.75 GiB a rank at TP=2 down to 1.90 GiB. The full model verifies every drafted token, so replies are unchanged | — |
| The KDA conv taps kept fp32, as stored | 2026-10-02 | An earlier build rounded them to BF16 for the kernels; the kernels now read fp32, as 1.x's vLLM keeps them. MLX and EXL3 checkpoints, whose taps are BF16, give the same tokens and caches as before (12 of 12) | — |
| TP=3 shares cut at unit boundaries, the remainder to the lower ranks | 2026-10-03 | Heads 22/21/21, MoE width 704/704/640, vocabulary 51,648/51,648/51,584: no zero rows, the weights untouched. At two ranks the cut equals the halves byte for byte on every tensor. Weight estimates 63.04/62.87/57.70 GiB on ranks 0/1/2 | — |
| The published AXL weights not supported | 2026-10-04 | Capacity does not need them: on the pinned weights TP=2 holds more window than 1.x. At TP=3 they would act only on the part of a prefill that does not grow with length, at most 12 ms a chunk, about 1% of that part (2026-10-03) | More than one sequence at a time is taken up: 1.x measured AXL at two sequences |

## Window, limits and scope

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| TP=2 window 300,000 tokens, not the 567,255 of `--context 0` | 2026-10-04 | Leaves the default 3 GiB for other conversations' kept prompts ([why 300,000](../README.md#serving-defaults)) | A deployment passes another `--context` |
| TP=3 window: the largest that fits (`--context 0`) | used from 2026-10-03, the shipped default from 2026-10-04 | 1,048,576 tokens, the model's limit, on the reference ring | — |
| Replies of up to 32,768 tokens when a request names no limit | 2026-10-03 | — | — |
| Prefill chunk of 4,096 rows | rejected 2026-10-02 | 1,076.1 tok/s against 1,169.9 with 2,048 rows on the same build, and a window of about 405K instead of about 490K; the bits were the same | — |
| One sequence at a time | 2026-10-02 | The engine's CUDA path decodes one GLM request at a time | Upstream merges #243 |
| No image input in 2.0.0 | 2026-10-04 | The engine refuses images for GLM on CUDA | Read upstream pull request #194 first ([Next Action](../README.md#next-action)) |

## Drafts

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| The checkpoint's MTP head drafts (`--drafter none`), not DFlash2 | 2026-10-04 | Named explicitly: the engine's `--drafter auto` would take DFlash2 at TP=2 when its weights are in the cache and refuse it at TP=3 (it splits only over two ranks). DFlash2's weights' terms are also why 1.x does not use it | — |

## Fabric

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| Two rails per link | 2026-10-02 (TP=2), 2026-10-03 (TP=3) | TP=2 prefill +4% on the same build (two rails give [validation's](validation.md#prefill-and-decode-speed) TP=2 reference); TP=3 1,225.1 → 1,384.7 tok/s (+13%); decode unchanged and the decode-check hashes the same at both | — |
| TP=3: four NCCL channels, NCCL's own IB transport (`NCCL_NET_PLUGIN=none`), subnet-aware routing | 2026-10-03 | The second rail took an 8 MiB piece from 1,530 to about 900 µs, with 2, 4, 8 or 64 channels alike; four channels shortened a 32 MiB chunk (9,236 → 5,072 µs on one rail, 3,622 → 3,346 on two). Decode-sized exchanges (23-51 µs) moved within noise. `NCCL_CROSS_NIC` and the image's default network plugin changed nothing | — |

## Prefill

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| A prompt kernel for the NVFP4 routed experts (`b0fa0a5`) | 2026-10-02 | Expert time 18.55 → 9.2 s a prompt, prefill 769.3 → 913.7 tok/s (+19%). Its prompt bits differ from the decode kernel's (a pair's bits depend only on its row and expert, so chunking still does not change them), so the decode-check hashes changed once here; the reference hashes postdate it. A faster form summing the whole K inside the tensor cores (2.64× against 2.5-2.6×) was rejected for five times the down projection's error | — |
| BF16 prompt matmuls sum their K slices in registers (#333); DSA prompt kernels on more programs | 2026-10-02 | 943.7 → 1,068.2 tok/s, same bits | — |
| A prompt chunk's exchanges in four row pieces on a second stream | 2026-10-02 | 1,068.2 → 1,150.7 tok/s; two and eight pieces gave 1,119.6 and 1,116.6 | — |
| The KDA prompt step kernel with eight warps a block | 2026-10-02 | 1,150.7 → 1,169.9 tok/s, same bits | — |
| BF16 split-K partials reserved for short windows only | 2026-10-02 | The window at `--context 0` grew from about 490K to 567,255 tokens; prefill unchanged | — |
| The prefill exchange `split` as the default (`TF_GLM_PREFILL_REDUCE`) | 2026-10-03 | TP=3, in one window of launches: against the earlier `gather` (1,394-1,398 tok/s), `scatter` +6.8% and `split` +19.6%; every decode-check hash and the NLL set unchanged. Taken where the ranks can send to each other; elsewhere `gather`. At TP=2 it first ran in the release, with the hashes unchanged; its share of TP=2's gain was not measured alone | — |
| The indexer's prompt work: 16 rows a program, only the pool columns selection reads, a long row read three times instead of five | 2026-10-03 | On one GPU with a real DSA layer, a chunk's token selection at 1M tokens 209.5 → 165.5 ms (−21%), same bits; with the exchange work above, the 200K and 500K runs fit a shorter 1M prefill ([long inputs](validation.md#long-inputs)). Tried and slower: the histogram fused into scoring, three 11-bit passes, a persistent grid, blocks of 2,048 | — |
| Prefill ideas that change bits | rejected 2026-10-02 and 03 | Scoring 32 heads of a row block as one GEMM with the head sum moved after it (estimated at about 240 s off a 1M prefill if it scored twice as fast), scoring on FP8 tensor cores, a chunked KDA (its recurrence is 2.06 s of a 38,960-token prompt, a gain of a few percent at most), MiaAI-Lab's single-pass sparse attention. Each changes, or may change, the bits behind the reference hashes and NLL | — |

## Heat

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| A prefill waits between chunks at 92 °C until 88 °C, every rank together | 2026-10-04 | Without it, a 1M-token prompt at TP=3 reached the thermal watch's 94 °C after six and a half minutes; with it the prompt completed ([heat](../README.md#measured-on-the-release)). The per-chunk exchange of the hottest reading cost about 0.2% of a 38,960-token prefill. 92 °C sits 2 °C under the stop (near the top a host rose 0.5-1 °C a minute; a chunk takes seconds); 88 °C sits under the 88.8-89.6 °C a 1M prefill held before the faster prefill work, and `serve.sh` keeps it provisional | Upstream answers issue #339; the bands are the rank file's to change |
| How the wait is made | 2026-10-04 | One word gathered on its own before each chunk, not added to the existing exchange, whose result the host does not read; the ACPI zones only, as the thermal watch and the cooling gate read (the GPU ran about 9 °C cooler in every record); no limit on a wait, so a hot room holds the request and the thermal watch stays the last guard; off unless both bands are set, so upstream's default does not change | — |

## Engine commits not named elsewhere

The release branch is upstream v0.6.4 plus the commits that the [changelog](../CHANGELOG.md) groups. These are the ones it does not name, tests and recipe text aside:

- `539cf8d`: `/v1/completions` takes token-id prompts and returns vLLM-shaped `prompt_logprobs` for GLM, which the NLL check (`score-nll`) needs; a request without it is unchanged, and one with it never resumes a kept prompt.
- `b0fa0a5`: the NVFP4 routed experts' prompt kernel (above).
- `a7d7c2b`, `065a58e`: the KDA conv taps in fp32 (above).
- `8b8e6e8`: DSA's prompt absorb and expand over row blocks, and the indexer's pool scores four rows a program (after MiaAI-Lab's patch 0009).
- `7a84888`: the KDA prompt step kernel with eight warps (above).
- `d6fe08e`: the BF16 split-K partials only for short windows (above).
- `b58dc42`: the startup estimate counts the draft head's rows as packed, so every rank of three loads exactly its estimate.
- `68cfebc`: `send_recv` as an optional capability of upstream's communicator interface, which `split` uses.
- `ac478a5`: a rank can load only chosen layers, for the tests against the real checkpoint.

## Measures from 1.x not yet evaluated on 2.x

Open items: 1.x measured them; 2.x has no result either way.

- **CPU pinning of each rank to performance cores.** 1.x pins each rank's container to the performance cores ([CPU placement](../../v1/docs/benchmarks.md#cpu-placement-on-the-reference-pair-2026-09-26)); `create_container.sh` sets no CPU set.
- **MTP draft depth.** 1.x compared fixed depths one to five and keeps three ([depths one to five](../../v1/docs/speculative-decoding.md#depths-one-to-five-2026-09-19-and-20)); 2.x's draft depth was not compared.
- **NCCL channel count at TP=2.** The TP=2 rank files leave the count to NCCL, which on its own opened 64 channels on this pair under 1.x, where 8 returned about 3 GiB a rank with prefill within 1% ([channel count](../../docs/nccl-validation.md#channel-count)); TP=3 sets four.
- **MTU.** 1.x measured 9000 against 1500 and stayed at 1500 ([channel count](../../docs/nccl-validation.md#channel-count)); 2.x did not vary it.
- **LPA.** 1.x's late-prefill approximation is experimental and a batch opt-in there ([LPA](../../v1/docs/lpa.md)); it changes a long prefill's result by design. 2.x has no counterpart, and its reference hashes and NLL are those of the exact prefill.
