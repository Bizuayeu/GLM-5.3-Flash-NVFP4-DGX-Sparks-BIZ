# Validation (2.x)

[日本語](validation.ja.md) · [2.x overview](../README.md) · [Setup runbook](../SETUP.md)

What a 2.x launch is accepted on, in the order to run it, with the reference values. The reference values were measured on the reference hosts on 2026-10-02 and 10-03 with builds of the engine before the release, and 2.0.0 was accepted against them on 2026-10-04 ([measured on the release](../README.md#measured-on-the-release)). A check that differs is a finding to explain before routine use, not a value to replace.

Run the tools from `v2/` of the checkout on rank 0, in its virtual environment ([setup §2](../SETUP.md#2-checkout-and-checkpoint)), against the engine on loopback (`http://127.0.0.1:8095`, model `glm-tf` unless the rank file sets others). Let the hosts cool between long requests ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)) and keep the memory guard running.

## Decode check

Greedy 512 tokens after the fixed prompt of about 2,048 tokens (`PROMPT_TOKENS`; each row's `prompt_tokens` gives the exact count), three times for each task, as in 1.x ([after a switch](../../v1/docs/launch-safety.md#after-a-switch-the-decode-check)):

```sh
for k in count prose code; do
  BASE=http://127.0.0.1:8095 MODEL=glm-tf PROMPT_KIND=$k SAMPLES=3 \
  TOKENS_OUT=../records/<run>/tokens-$k.json python -m glm53_tf decode-check
done
```

Before each sample it sends `TF_GLM_CACHE_ENTRIES` (default 8, the engine's) short distinct requests, so every sample prefills the whole prompt (`cached` 0 in each row); if the server was started with another value, pass the same one. The summary gives the speed, the MTP acceptance length (1 + accepted / rounds, from each reply's `tensorfold` block) and `distinct_completions`. `TOKENS_OUT` keeps each sample's text and token ids; two launches whose hashes differ are compared at their first diverging token with `python -m glm53_tf decode-divergence A.json B.json`.

**Accepted when** each task gives one completion within the launch (`distinct_completions` 1) and its `completion_sha256` is the reference of its TP:

| Task | TP=2 `completion_sha256` | TP=2 `token_ids_sha256` | TP=3 `completion_sha256` | TP=3 `token_ids_sha256` |
|---|---|---|---|---|
| count | `aa5a33f7dfae78e6` | `77fcc6e0c2a8540c` | `67058e32104fa3d1` | `3e398a9c0dfc5cd9` |
| prose | `e33450686f6b5624` | `3ee287174a7b9ae3` | `8901c751b210f13c` | `0a3bb372ba424ae0` |
| code | `0ffecb8187fd7084` | `f579ca05b8be8490` | `43edfcefb4bafdb8` | `91f20cec01a74182` |

The token ids held across eight engine builds at TP=2 and ten launches at TP=3, with one or two rails, the three prefill exchanges, four NCCL channels at TP=2 and image input on (`VISION=1`). From 2.1.0 the check keeps both fields of a delta that carries the end of the reasoning and the start of the content; earlier versions kept one, so counting and code read shorter texts (2.0.x's hashes `93951874…`, `389d8fb9…` at TP=2 and `be0f5d34…`, `ac0a26c6…` at TP=3 are the same tokens). TP=2 and TP=3 differ from each other by design (the ranks split the sums differently). Acceptance length: 3.821 / 2.098 / 3.180 at TP=2 and 3.549 / 2.222 / 3.234 at TP=3. Each release's speeds are in [measured on the release](../README.md#measured-on-the-release).

## Image input

With image input on (`VISION=1` on every rank): one image, a 4:3 image of 7,966 prompt tokens, two images in order, a single colour and an image in a tool result, then a text question and a tool round trip. **Accepted when** each is answered correctly and a video part is refused with 400.

## Drafted equals serial

The same prompt with and without drafts (`"draft": false` in the request body decodes one token a round) must give the same text. Measured on prose, code and counting prompts, 256 tokens, at both TP=2 and TP=3. Compare whole texts: in a stream with drafts, one delta can carry both `reasoning_content` and `content`, and a reader that takes one field per delta finds a difference that is not there.

## Teacher-forced NLL

The NLL set of [`config/nll_set.json`](../config/nll_set.json), a byte copy of 1.x's: four domains (Japanese, English, code, math) of four texts each, 5,851-6,830 tokens per domain. The tokenizer must be the checkpoint's own:

```sh
python -m glm53_tf score-nll --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93/tokenizer.json \
  --out ../records/<run>/nll.json
```

Needs the `tokenizers` package in the environment that runs it; the Hugging Face lock does not install it. Each text is scored twice; the run passes when every request answered and the two scores of each text agree (argmax agreement 1.0 and no movement on the reference hosts).

| Domain (positions) | TP=2 | TP=3 | 1.x TP=2 defaults (1.26.0) |
|---|---|---|---|
| Japanese (6,826) | 2.5474 | 2.5313 | 2.5412 |
| English (6,678) | 2.9257 | 2.9001 | 2.9079 |
| Code (5,941) | 1.3184 | 1.3101 | 1.3145 |
| Math (5,847) | 0.6250 | 0.6237 | 0.6285 |

**Accepted when** the run passes and each domain equals the reference of its TP. The TP=3 values were identical in two launches with different prefill exchanges, so a different value means different bits.

## Prefill and decode speed

A 38,960-token prompt three times with a fresh nonce at its start (median), then 512 tokens after a short fixed prompt. Reference: TP=2 1,217.2 tok/s prefill and 35.61 tok/s decode (two rails, on a build before the `split` exchange); TP=3 1,673.1 and 1,667.9 tok/s prefill with `split` in two launches, 53.03 and 52.93 tok/s decode. With one rail TP=3 prefill was 13% slower and decode unchanged. The reference values let the hosts cool before each prompt. A 38,960-token prompt runs at one of two speeds about 7.5% apart, at the same GPU clock (2,184 MHz with no clock event reason), CPU frequencies and temperatures, below the heat wait. On 2.1.1 at TP=2, three back to back held at 1,327.0, 1,326.8 and 1,322.8 tok/s in one launch and gave 1,326.3, 1,227.1 and 1,228.6 in another; with `TF_GLM_PREFILL_REDUCE=gather` a prompt right after a cooling wait ran at 1,176.0 after one at 1,261.9. At TP=3 three back to back held at 1,653.6, 1,654.4 and 1,656.5. Heat does not explain which speed a prompt gets, and the cause is not known; the fall from 1,670 to 1,540 tok/s seen at TP=3 while 2.0.0 was accepted may be the same two speeds. On 2.1.4 at TP=2, 22 prompts in two launches, each after a cooling gate, all ran at the faster speed: 1,292.3-1,329.1 tok/s (median 1,326.2), and 1,184.6-1,191.8 in the launch with the engine's profiling on; the GPU's cumulative SW power cap counter did not grow during any of them (it grows only while no engine runs, at 208-305 MHz). The cause stays open and is watched in heavier runs. Compare the median of several prompts. `python -m glm53_tf bench` takes these figures; [benchmark method](benchmarks.md) gives the conditions.

## Long inputs

A passphrase in the middle of 199,652 tokens of ledger lines, and three passphrases (start, middle, end) in 499,622 and 1,036,859 tokens. Reference at TP=3: 145.6 s and correct at 199,652; 454.1 s and 3 of 3 at 499,622; 3 of 3 at 1,036,859 with the first token after 1,364 s (on a build before the `split` exchange and the indexer work; fitted to the 200K and 500K runs, the build that ran them is predicted at about 1,112 s). The hottest host reached 89.6-90.1 °C during these, below the 94 °C of the [thermal watch](../../host/README.md#during-long-runs). The 1M prompt is not part of TP=2's window.

## Tools through the tool-argument gate

tool-eval-bench with 1.x's invocation (69 scenarios, seed 42, temperature 0, parallel 1, effort low, `clear_thinking`, 4,096-token output, 600 s timeout), through the [gate](../SETUP.md#7-tool-argument-gate-optional):

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

Reference: 91/100 at both TP=2 and TP=3 with the Safety Gate passed (TC-43 passes through the gate); the structured-output scenarios TC-64 to TC-69 all pass, which needs xgrammar in the image. TP=2 failed TC-21 and TC-61, TP=3 TC-61 alone. One trial each, so a point or two is within what one trial moves.

## Stopping a reply

The release engine stops a decode on every rank within a round when the client disconnects or a stop string appears (upstream pull request #301); before it, a lone sequence decoded on to its token limit. Accepted when, at both TP=2 and TP=3: a streamed request with a large `max_tokens` cut by the client after a few seconds stops decoding (the `rounds` of `/health` stop growing, no rank keeps decoding), a request with a `stop` string that the reply reaches ends there with `finish_reason` `stop`, and a short request sent right after either one starts at once.

## Memory and temperature

The memory guard's log (`~/glm53-tf/logs/hostwatch-<label>.log`) gives each host's lowest `MemAvailable` during the run. Reference at TP=3: 29-31 GiB on ranks 0 and 1 and 35 GiB on rank 2 during the 1M request; at TP=2 about 9 GiB on rank 0 with the extensions built ahead.

The heat wait prints `[tensorfold] heat:` lines on every rank, one where a wait starts and one where it ends (and one a minute while it lasts), the same on every rank; the reply's `tensorfold` block gives `heat_wait_s`. Accepted when a long prompt finishes with no host at 94 °C, the [thermal watch](../../host/README.md#during-long-runs)'s limit.
