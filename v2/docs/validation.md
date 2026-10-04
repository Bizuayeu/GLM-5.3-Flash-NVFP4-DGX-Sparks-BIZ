# Validation (2.x)

[日本語](validation.ja.md) · [2.x overview](../README.md) · [Setup runbook](../SETUP.md)

What a 2.x launch is accepted on, in the order to run it, with the reference values. The reference values were measured on the reference hosts on 2026-10-02 and 10-03 with development builds of the engine, and 2.0.0 was accepted against them on 2026-10-04 ([measured on the release](../README.md#measured-on-the-release)). A check that differs is a finding to explain before routine use, not a value to replace.

Run the tools from `v1/` of the checkout on rank 0, against the engine on loopback (`http://127.0.0.1:8095`, model `glm-tf` unless the rank file sets others). They are the 1.x tools, which serve either engine (`decode_check.py` tells them apart by the server's `/metrics`). Let the hosts cool between long requests ([GPU clock cap](../../v1/docs/operations.md#gpu-clock-cap)) and keep the memory guard running.

## Decode check

Greedy 512 tokens after a fixed prompt of about 2,066 tokens, three times for each task, as in 1.x ([after a switch](../../v1/docs/launch-safety.md#after-a-switch-the-decode-check)):

```sh
for k in count prose code; do
  BASE=http://127.0.0.1:8095 MODEL=glm-tf PROMPT_KIND=$k SAMPLES=3 \
  TOKENS_OUT=../records/<run>/tokens-$k.json python3 tools/decode_check.py
done
```

Before each sample it sends `TF_GLM_CACHE_ENTRIES` (default 8, the engine's) short distinct requests, so every sample prefills the whole prompt (`cached` 0 in each row); if the server was started with another value, pass the same one. The summary gives the speed, the MTP acceptance length (1 + accepted / rounds, from each reply's `tensorfold` block) and `distinct_completions`.

**Accepted when** each task gives one completion within the launch (`distinct_completions` 1) and its `completion_sha256` is the reference of its TP:

| Task | TP=2 `completion_sha256` | TP=3 `completion_sha256` | TP=3 `token_ids_sha256` |
|---|---|---|---|
| count | `93951874af05c708` | `be0f5d346e96452b` | `3e398a9c0dfc5cd9` |
| prose | `e33450686f6b5624` | `8901c751b210f13c` | `0a3bb372ba424ae0` |
| code | `389d8fb9e3972b66` | `ac0a26c61c97838c` | `91f20cec01a74182` |

The TP=2 hashes held across seven development builds and with one or two rails; the TP=3 hashes across ten launches, one or two rails and the three prefill exchanges. TP=2 and TP=3 differ from each other by design (the ranks split the sums differently). Reference speeds: TP=2 41.16 / 26.82 / 34.87 tok/s, TP=3 52.90 / 38.29 / 48.66; acceptance length at TP=3 3.549 / 2.222 / 3.234. When a hash differs, `tools/decode_divergence.py` shows the first differing token between two runs' `TOKENS_OUT` files.

## Drafted equals serial

The same prompt with and without drafts (`"draft": false` in the request body decodes one token a round) must give the same text. Measured on prose, code and counting prompts, 256 tokens, at both TP=2 and TP=3. Compare whole texts: in a stream with drafts, one delta can carry both `reasoning_content` and `content`, and a reader that takes one field per delta finds a difference that is not there.

## Teacher-forced NLL

The NLL set of [`v1/config/nll_set.json`](../../v1/config/nll_set.json): four domains (Japanese, English, code, math) of four texts each, 5,851-6,830 tokens per domain. The tokenizer must be the checkpoint's own:

```sh
python3 tools/score_nll_set.py --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93/tokenizer.json \
  --out ../records/<run>/nll.json
```

Needs the `tokenizers` package in the environment that runs it. Each text is scored twice; the run passes when every request answered and the two scores of each text agree (argmax agreement 1.0 and no movement on the reference hosts).

| Domain (positions) | TP=2 | TP=3 | 1.x TP=2 defaults (1.26.0) |
|---|---|---|---|
| Japanese (6,826) | 2.5474 | 2.5313 | 2.5412 |
| English (6,678) | 2.9257 | 2.9001 | 2.9079 |
| Code (5,941) | 1.3184 | 1.3101 | 1.3145 |
| Math (5,847) | 0.6250 | 0.6237 | 0.6285 |

**Accepted when** the run passes and each domain equals the reference of its TP. The TP=3 values were identical in two launches with different prefill exchanges, so a different value means different bits.

## Prefill and decode speed

A 38,960-token prompt three times with a fresh nonce at its start (median), then 512 tokens after a short fixed prompt. Reference: TP=2 1,217.2 tok/s prefill and 35.61 tok/s decode (two rails, before the `split` exchange); TP=3 1,673.1 and 1,667.9 tok/s prefill with `split` in two launches, 53.03 and 52.93 tok/s decode. With one rail TP=3 prefill was 13% slower and decode unchanged. 2.0.0: TP=2 1,329.9 tok/s prefill and 35.31 decode; TP=3 1,668.5 prefill with the heat wait and 1,671.4 without, 52.93 decode. Let the hosts cool before each prompt: three back to back fell from 1,670 to 1,540 tok/s at TP=3. The measurement scripts are not part of this repository.

## Long inputs

A passphrase in the middle of 199,652 tokens of ledger lines, and three passphrases (start, middle, end) in 499,622 and 1,036,859 tokens. Reference at TP=3: 145.6 s and correct at 199,652; 454.1 s and 3 of 3 at 499,622; 3 of 3 at 1,036,859 with the first token after 1,364 s (an earlier build, before the `split` exchange and the indexer work; fitted to the 200K and 500K runs, the current build is predicted at about 1,112 s). The hottest host reached 89.6-90.1 °C during these, below the 94 °C at which the measurements stopped a run. The 1M prompt is not part of TP=2's window. 2.0.0: at 199,652 the first token after 133.2 s at TP=3 and 163.7 s at TP=2, both correct; at 1,036,859, 3 of 3 with the first token after 1,264.8 s, 170.1 s of it heat waits, and the hottest reading 92.8 °C. Without the heat wait the same prompt reached 94 °C after six and a half minutes.

## Tools through the tool-argument gate

tool-eval-bench with 1.x's invocation (69 scenarios, seed 42, temperature 0, parallel 1, effort low, `clear_thinking`, 4,096-token output, 600 s timeout), through the [gate](../SETUP.md#7-tool-argument-gate-optional):

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

Reference: 91/100 at both TP=2 and TP=3 with the Safety Gate passed (TC-43 passes through the gate); the structured-output scenarios TC-64 to TC-69 all pass, which needs xgrammar in the image. TP=2 failed TC-21 and TC-61, TP=3 TC-61 alone. 2.0.0: TP=2 93/100 and TP=3 91/100, each failing TC-61 alone. One trial each, so a point or two is within what one trial moves.

## Stopping a reply

The release engine stops a decode on every rank within a round when the client disconnects or a stop string appears (upstream pull request #301); before it, a lone sequence decoded on to its token limit. Accepted when, at both TP=2 and TP=3: a streamed request with a large `max_tokens` cut by the client after a few seconds stops decoding (the `rounds` of `/health` stop growing, no rank keeps decoding), a request with a `stop` string that the reply reaches ends there with `finish_reason` `stop`, and a short request sent right after either one starts at once.

## Memory and temperature

The memory guard's log (`~/glm53-tf/logs/hostwatch-<label>.log`) gives each host's lowest `MemAvailable` during the run. Reference at TP=3: 29-31 GiB on ranks 0 and 1 and 35 GiB on rank 2 during the 1M request; at TP=2 about 9 GiB on rank 0 with the extensions built ahead.

The heat wait prints `[tensorfold] heat:` lines on every rank, one where a wait starts and one where it ends (and one a minute while it lasts), the same on every rank; the reply's `tensorfold` block gives `heat_wait_s`. Accepted when a long prompt finishes with no host at 94 °C, where the thermal watch stops the engine.
