# Validation scope and evidence

[日本語](validation.ja.md)

What the 1.x evidence shows and does not show, how a candidate is compared with an unchanged control, the open items, and the scope in which routine use is accepted. Checks with pages of their own:

## Related checks

- [Repeatability](repeatability.md): requantization checks on the fixture, the expert token order, indexer top-k ties and launch states.
- [Output correctness gates](correctness-gates.md): the prefix-cache correctness gate and multibyte output.
- [Component validation](component-validation.md#reproduce-the-single-gpu-fixture): reproducing the single-GPU fixture, CPU and component checks, the kpool tail ring repro.

## Evidence, not production qualification

These observations used a GB10 GPU, vLLM source commit `385dce36bcee42309924a5ece951a96db3dce7f2`, and NVIDIA model revision `423acf37583782c51c142d145aef733d72943d93`. Private raw runs are not distributed; this is their reviewed summary.

| Test | Observed result | Limit |
|---|---|---|
| Reference attention with real packed FP8 cache | Candidate widths 63/64/65/2048/2051/2176 checked; padding/empty rows handled; deliberate tail removal detected | Component check, not whole-model correctness |
| Four-layer checkpoint | All 3,591 selected tensors byte-verified; original widths and 288 experts retained | Not a language-quality benchmark |
| Marlin W4A16, one GPU | Load, generation, A→B→A replay, two-request batch token comparison and forced-prefill tests passed | Limited inputs, no production reliability claim |
| Marlin, 8,705-token input | Crossed the measured 8,704-token attention manager block; forced-prefill next token matched; selected logprob difference 0.0031653 | Not every boundary or full context capacity |
| Batch-invariant mode | Rejected by SM120 sparse MLA; Triton MLA lacks sparse support | Not usable for this pinned stack |

The probability tolerance was a provisional two-BF16-epsilon bound at the reference logprob magnitude. Exact replay, token agreement and tolerance-based comparisons are distinct checks. A truncated model can amplify numerical differences.

The packaged CLI and reorganized Docker build were also checked on GB10: the real-cache component test and the Marlin four-layer test at context 16,384 passed, including the 8,705-token boundary input. Both test containers exited successfully without OOM. This verifies the new package/worker import path, not cross-run bitwise equivalence or full-model TP=2.

Marlin changes the arithmetic: its [linear kernel](https://github.com/vllm-project/vllm/blob/385dce36bcee42309924a5ece951a96db3dce7f2/vllm/model_executor/kernels/linear/nvfp4/marlin.py) is W4A16, and its [MoE selector](https://github.com/vllm-project/vllm/blob/385dce36bcee42309924a5ece951a96db3dce7f2/vllm/model_executor/layers/fused_moe/oracle/nvfp4.py) selects W4A16 for MARLIN independently of the generic `use_a16` flag. Do not infer precision from that flag alone.

**NVIDIA's model card does not describe this serving.** The [pinned model card](https://huggingface.co/nvidia/GLM-5.3-Flash-NVFP4) reports a BF16-versus-NVFP4 accuracy table for its checkpoint. Those figures were measured on NVIDIA GB200 through vLLM and SGLang, sampled at temperature 1.0, under the card's post-training quantization recipe (`nvfp4_experts_dense_mlp-kv_fp8_cast`, the W4A4 path); they describe that path on that hardware. This stack runs the same weights through Marlin W4A16 on GB10, with its own prefill, decode and speculative paths, so the card's table is neither reproduced nor claimed here. The numbers that describe this serving are the teacher-forced NLL rows and the long-input checks in [benchmarks](benchmarks.md), the [FreedomBench](freedombench.md) result and the harness cases in [harnesses](harnesses.md), each with the image and profile it was measured on.

vLLM [does not guarantee default reproducibility](https://github.com/vllm-project/vllm/blob/385dce36bcee42309924a5ece951a96db3dce7f2/docs/usage/reproducibility.md). This does not prove that our adapter is correct either; the checks above are evidence, not a proof.

## Comparing a candidate with an unchanged control

Before judging a difference, measure the unchanged arm at least twice and preserve every repetition, its median and range. Include separate launches when the candidate requires a restart. A difference inside the observed control variation is **inconclusive at this resolution**, not proof of equality; a few repetitions do not establish the absence of a slow tail.

- Identify the executed artifacts: model/tokenizer revisions, image ID, source and loaded overlays, effective settings and target-kernel dispatch. A comparison without evidence that its intended implementation ran is invalid. Keep launch identity, sampling/thinking settings, input/output lengths, concurrency, warmup and APC history with the results.
- Separate cold prefill from APC hits. For a cold length ladder, place a unique nonce early in each request so shorter inputs are not prefixes of later ones, and measure lengths with the tokenizer or returned usage. Shared system/tool prefixes may still hit: inspect cached-token counts and server logs, and mark missing evidence as unknown.
- Compare completion hashes for speed measurements that assume identical output. Different completions are different conditions; keep their performance and quality outcomes, including failures, rather than pooling them into an identical-output claim.
- When weights, quantization or speculative depth change, use several prompts per task type and separate tuning from evaluation inputs. Start with at least three per type as a provisional design, then justify the sample count from unchanged-arm variation across prompts. Report acceptance length and estimated steps/s (decode tok/s divided by acceptance length) with tok/s; changing the completion can change draft acceptance without making the underlying arithmetic faster. Compare steps/s only between arms at the same depth: a deeper draft verifies more positions per step. The route-g and depth sweeps on 1.6.0 used one prompt per type; the 1.7.0 sweeps used ten inputs with tuning and evaluation sets ([depth three for both](speculative-decoding.md#depth-three-for-both-checkpoints-2026-09-21)).
- Expect a draft-side change to change the completions. On this stack the drafted candidates enter the verification batch, and a BF16 tie in the target's logits then resolves differently, so the same depth with a different draft (another top-k sharing, a gate, a requantized `lm_head`) produced different text on most inputs while the unchanged arms repeated theirs. Judge such a change by acceptance and teacher-forced NLL, and treat equal text as a bonus, not a requirement.
- Match sent/completed requests and output tokens to server-counter deltas over the same measurement window. Exclude windows with background requests or unexplained mismatches from controlled comparisons, retaining their values and exclusion reasons. If old records lack counters, state which isolation checks were possible. Mia’s independent TP2 report on PR #139 illustrates this distinction; its adaptive policy, graph coverage and scratch-size changes were measured together.
- Keep acceptance-rate denominators explicit: proposed drafts, verified candidates and accepted draft tokens (excluding the bonus) differ. Shortening a verification prefix can raise the rate without improving prediction at a fixed depth (Mia PR #235). Do not transfer DFlash2 results to standard MTP or greedy results to sampling.

`server agreement --reference` accepts one saved result, not two control records. Its `self_agreement` describes within-run repeats. For an unchanged-before / candidate / unchanged-after comparison, preserve all three records and inspect the control pair with the existing `agreement.compare_records` function; do not treat within-run stability as evidence of stability across launches. No second-reference CLI option is provided.

## Evaluations and open items

[FreedomBench](freedombench.md) (the pinned English suite, the reviewed Japanese translation and the framing and evidence-placement extension), [HLE](hle.md) (two 100-question subsets on both profiles, not comparable with published HLE values) and the [harness acceptance matrix](harnesses.md) (per-case status and the accepted route) own their results; the basic API smoke below feeds the matrix's API group and closes no client case. The [NCCL diagnostic](nccl-validation.md) covers transport and synthetic data correctness on two and three ranks, not the full model. Do not turn a fixture, API smoke or collective result into evidence for a scope the acceptance in [SETUP step 6](../SETUP.md#6-qualify-the-full-model) does not declare.

Open, each with its owner:

- FB-05's LPA part (approximation exercised, A/B/A) is not run while LPA stays off ([FreedomBench](freedombench.md)).
- Images of 7,922 to 8,000 tokens are refused ([image input](vision.md#limits-and-open-items)).
- In long context the published option answered with the record before the one asked; the cause is not isolated ([prefix-cache gate](correctness-gates.md#prefix-cache-correctness-gate)).
- On the model API the tool-eval-bench Safety Gate is not passed; through the optional [tool-argument gate](harnesses.md#tool-argument-gate) it is.
- Sustained mixed load and batching combinations are unvalidated, and at TP=3 cancellation, tool calls and failure recovery were not run ([SETUP step 6](../SETUP.md#6-qualify-the-full-model)).
- MTP depths, decode graphs, prefix caching and APC/LPA combinations have scoped evidence only ([speculative decoding](speculative-decoding.md), [optimization catalog](optimization-catalog.md), [prefix caching](benchmarks.md#independent-full-model-prefix-caching-p19), [P22 contract](apc-lpa-design.md)).

## Full-model scope

**Status.** Routine use is **accepted** for both profiles on two hosts at TP=2 and on three hosts at TP=3, each with the settings in [server configuration](server-configuration.md) and within the [concurrency scope](#concurrency-scope). [SETUP step 6](../SETUP.md#6-qualify-the-full-model) is the record of that acceptance, its dates and extents, and of where each item's evidence is; if this page or the README ever differs from it, step 6 holds. Outside that scope (other hardware, more sequences than step 6 states, video input, unsupported request settings) nothing is qualified. The subsection after the concurrency scope records how the evidence was gathered; the other checks are listed under [related checks](#related-checks).

### Concurrency scope

| Topology and profile | Active sequences | Status |
|---|---|---|
| Two hosts at TP=2, distributed defaults | One (`max_num_seqs = 1`); further requests queue, the declared behaviour | Accepted ([SETUP step 6](../SETUP.md#6-qualify-the-full-model)). More than one is **not supported on two hosts**: 3 GiB of KV per rank is sized for one 256K sequence, and on the pinned weights concurrency needs more ranks (TP=3 below), not a larger budget on two |
| Two hosts at TP=2, published option ([example profile](../examples/server.axl.example.toml)) | Two, from 6 GiB of KV per rank; the repacked weights load 4.4 GiB less per rank | Accepted ([SETUP step 6](../SETUP.md#6-qualify-the-full-model)); evidence below |
| Three hosts at TP=3, both profiles ([example profile](../examples/server.tp3.example.toml)) | Set by `max_model_len`, `max_num_seqs` and the KV per rank; the template serves one 262,144-token sequence ([capacity](benchmarks.md#measurements-on-1240)) | Accepted ([SETUP step 6](../SETUP.md#6-qualify-the-full-model)) on three GB10 hosts in a switchless QSFP ring (NVIDIA's [three-Spark ring guide](https://build.nvidia.com/spark/connect-three-sparks)). Not measured: more than three long requests at once, the distributed defaults beyond 262,144 |

**Evidence for the two-sequence profile.** On one launch on 2026-09-23, two ~200K passphrase requests sent together were both answered correctly without preemption, two tool-call requests together both returned the right call, and an image and a prose request together both answered ([measurements on 1.10.2](benchmarks.md#measurements-on-1102), with the times, decode speeds and memory). Three launches that day (numerical states 2, 1 and 2) each passed the routine after a switch — weight digest equal on both ranks to the first launch's, decode check, request traces, and on the third the kernel hashes — the sparkDash and tool-eval runs of [1.10.4](benchmarks.md#measurements-on-1104) ran on the second, and the three switches completed without recovery. [SETUP step 6](../SETUP.md#6-qualify-the-full-model) lists the items. Not measured: two requests at the 262,144-token boundary together. Cancellation is harness case [H-06](harnesses.md#acceptance-matrix-and-status), and a new launch is checked, not assumed, as on the defaults.

**Evidence for TP=3.** On 2026-09-29 and 10-01 launches of both profiles on three hosts passed the decode check (one completion per task within a launch, and a second launch of the distributed defaults on the same runtime cache repeating the first bit for bit), teacher-forced NLL, a ~200K passphrase, [image input](vision.md#three-hosts-at-tp3) and the [Japanese/Korean check](correctness-gates.md#multibyte-output); the weight digest per rank was taken on the distributed defaults. Teacher-forced NLL against TP=2 is accepted by comparing the two records position by position, not by a fixed margin on the mean: argmax agreement of at least 0.93 and a mean move of the actual token's log-probability within 1.5 times that between TP=2 launches of the same weights that differ only in numerical state. Both profiles meet it. The decode-check hashes of a TP=3 launch are valid only with each host's runtime cache ([launch safety](launch-safety.md#three-nodes)). Figures in [measurements on 1.24.0](benchmarks.md#measurements-on-1240).

**Repeatability with two sequences.** A request alone repeats bit for bit. A request that shares steps with another can get a different completion, because the pinned backend has no batch-invariant mode ([evidence table](#evidence-not-production-qualification)) and what shares a call changes a request's result: the NVFP4 Marlin MoE splits along K by the number of expert blocks, a step shared with a prefill runs the prefill-sized kernels, and at MTP depth 3 a partner makes decode steps eight rows, more than the six that the attention keeps off FA2, so they go through FA2 instead of the reference computation ([server configuration](server-configuration.md#attention-cache-and-checkpoint)). The attention is not the main cause: forced onto the reference computation for every call, it left most two-sequence differences in place, and the lead suspects are the MoE and the prefill-sized kernels of a step shared with a prefill ([reachability in serving](benchmarks.md#reachability-in-serving-2026-09-26)). This holds on both weights, and a pair still repeats when it is sent in the same order ([measurements on 1.14.0](benchmarks.md#measurements-on-1140)). This is declared behaviour, not an accepted defect. **For completions that repeat under any load, serve `max_num_seqs = 1`**: requests sent together then queue and each gets its lone completion; the throughput two sequences gain when requests overlap is in [measurements on 1.14.0](benchmarks.md#measurements-on-1140).

### Loading, API and benchmark checks

The reference image loaded all 45 language layers on two GB10 hosts with Marlin W4A16, eager execution, one active sequence, context 16,384 and 1 GiB KV per rank. The serial TP=2 four-layer fixture passed all existing state checks. With two active fixture sequences, one greedy path diverged at a near tie; that raw diagnostic remains failed and is separate from task-level acceptance.

The full model passed basic served-ID, English/Japanese final-answer, OpenAI SSE, harmless automatic tool/argument/return, and Anthropic Messages/count_tokens smoke checks. Chat acceptance with low reasoning effort also passed these final-answer/tool criteria. Reasoning text differed on replay; it remains a diagnostic rather than a requirement for identical free-form wording. The unsupported thinking-off request caused parser/content mixing and is not an accepted configuration; see [harness settings](harnesses.md).

[Official vLLM synthetic benchmarks](benchmarks.md) completed all planned measured requests. MTP passed the same benchmark and API cases at k=1 and k=3 before it entered the template, with a separate metadata view that keeps the original checkpoint and excludes its BF16 MTP layer from global NVFP4; depths one to five and the choice of three are in [speculative decoding](speculative-decoding.md). None of these checks establishes application quality on its own; routine use within the declared scope rests on the acceptance recorded in [SETUP step 6](../SETUP.md#6-qualify-the-full-model).

The 1.25.0 image adds the samplers' vocabulary bound (vLLM #50843), which leaves a row of finite logits untouched. On 2026-10-02 both profiles gave the decode-check completions of 1.24.0 on it bit for bit, and the published option's `server agreement` matched its reference record exactly (argmax agreement 1.0, no log-probability movement).
