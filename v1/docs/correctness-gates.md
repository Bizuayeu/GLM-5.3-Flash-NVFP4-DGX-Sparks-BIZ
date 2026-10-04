# Output correctness gates

[日本語](correctness-gates.ja.md)

Two checks of served output; the scope they belong to is in [validation](validation.md#full-model-scope).

## Prefix-cache correctness gate

On 2026-10-02 [`server prefix-gate`](server-configuration.md#commands) ran on the reference pair with the 1.25.0 image, both profiles at TP=2, each at both lengths. The distributed defaults passed both: six of six cold and warm, every warm request restoring 9,216 cached tokens of a 14,014-token prompt and 92,160 of 98,982. The published option was inconclusive (`cold_incorrect`) at both lengths: five of six cold and warm, the miss the same task with the same wrong answer in both phases. Each missed task was sent again alone under a fresh salt (one request, 0 cached tokens) to the pair then serving the option (1.24.0 checkout, image `99e6cf7a…`, the same request body) and returned the same wrong code, so the miss is not a cache defect; prefix caching stays on in serving.

**Off-by-one retrieval in long context, measured on the published option only.** Each wrong answer was the code of the record immediately before the one asked: asked for Record 03008 in the 98,982-token log, it answered `LPDHS`, the code of Record 03007; asked for Record 00374 in the 14,013-token log, `GYCUK`, that of Record 00373. The other record asked in the same task was right both times. The distributed defaults answered all six tasks right on the same logs and tasks at both lengths. The cause is not isolated: the option differs from the defaults in its W4A16 attention projections and `lm_head`, and also in other profile settings (two sequences, 6 GiB of KV, page dedup). The attention requantization is the most likely cause only as a hypothesis.

The gate sends its six requests in parallel under one salt, so in the cold phase only the first to arrive computes the prefix uncached and the others may read what it wrote; the single requests above are the uncached evidence.

## Multibyte output

ModelOpt NVFP4 checkpoints whose gate and up projections carry different global scales were reported to garble multibyte text ([vLLM #54150](https://github.com/vllm-project/vllm/issues/54150)). The pinned NVIDIA checkpoint is not affected: no full-model log shows the `w1_weight_scale_2 must match` warning, and in the four-layer fixture layer 3's gate and up scales match for all 288 experts. Another launcher for this model reads the garbling differently: tonyd2wild's checkpoint guard (commit `abb38bb`, 2026-09-24, no code adopted) refuses ModelOpt builds that quantize attention, naming those as the builds that corrupt. BIZ AXL quantizes the attention projections (W4A16, repacked here rather than by ModelOpt), so it has the form that guard refuses.

`server mojibake` on rank 0 monitors this. It asks for Japanese and Korean answers of at least 400 characters, three times each, at temperature 0 or sampled (`--temperature`, `--top-p`), and counts U+FFFD, lone surrogates and control characters other than line breaks and tabs in both the answer and the reasoning; a short, off-language, empty, malformed or failed answer is inconclusive, never a pass, and the full answers stay in `records/<stamp>-mojibake-r0/result.json`. No run has found such a character:

| Date | Profile | Sampling | Answers |
|---|---|---|---|
| 2026-09-17 | Distributed defaults, TP=2 (1.3.1) | Temperature 0 | Six: 852–1,024 characters, 93–95% in the target script, all finished with `stop`; the reasoning field was empty at that profile's low effort, so reasoning text was not exercised |
| 2026-09-21, 09-25 | Published option, TP=2 (on 09-25 the two-sequence profile) | Temperature 0 | Six each; on 09-25 1,154 Japanese and 1,309 Korean characters, 93–94% in the target script, all finished with `stop` |
| 2026-09-29, 10-01 | Distributed defaults, then the published option, TP=3 | Temperature 0 | Six each |
| 2026-10-02 | Both profiles, TP=2 (1.25.0) | Temperature 1.0, top_p 0.95, seeds 42 to 47 | Six each |

Answers at temperature 0 do not decide between the two readings above; the sampled answers did not find the garbling either.
