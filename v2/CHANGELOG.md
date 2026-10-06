# Changelog

[日本語](CHANGELOG.ja.md) (this English file is canonical and the GitHub Release is made from it)

The 2.x line, served by TensorFold. A `v2.*` tag publishes its section from this file. The 1.x line's history is in [v1/CHANGELOG.md](../v1/CHANGELOG.md).

## 2.1.8 — 2026-10-06

### Documentation

- [Validation](docs/validation.md#image-input) has the image checks, with their criterion (each answered correctly, a video refused with 400); the README's row links them instead of listing them. Validation keeps the acceptance lengths and links each release's speeds.
- The README's Status names the accepted images through their changelog sections and the current one, 2.1.4's, which it had left out. Limits no longer says several images are encoded in one call (each has its own call since 2.1.1), and its memory note links the serving defaults. The heat note and the [benchmark method](docs/benchmarks.md) no longer say prefill slows as a host heats: two speeds about 7.5% apart are not explained by heat ([validation](docs/validation.md#prefill-and-decode-speed)). The 2.1.0 prefill row names its first run (1,221.5 tok/s). The engine description names #421; the settings table names the TP=3 rank files' `NCCL_NET_PLUGIN=none`.

### Tests

- The image tag in the pages' build, inspect and create-container commands is the Dockerfile's, and the README's Status and release measurements name that image's version. The memory guard's floor is quoted from `hostwatch.sh`.

The image is unchanged; it stays 2.1.4's.

## 2.1.7 — 2026-10-06

### Documentation

- [Decisions](docs/decisions.md): the heat bands' row no longer says `serve.sh` keeps them provisional (2.0.7 dropped that), and the 2.0.0 row without image input points to the row that reopened it. The example rank files no longer date their values. The [repository README](../README.md) lists images among this line's inputs. `decode-check` and `score-nll` say what they still share with 1.x's tools.

### Tests

- The publication audit checks that each Japanese page has its English page's headings, table rows and code blocks. This line's copies of 1.x's `download`, `io`, `verify_download` and the tool gate's check and repair are checked to differ only in the package name. CI's required job installs filelock, so this line's download lock test runs there.

The image is unchanged; it stays 2.1.4's.

## 2.1.6 — 2026-10-06

### Fixed

- The [host tools'](../host/README.md#install) `install.sh` restarts the telemetry logger, so a reinstall runs the new program; before, `enable --now` left a running logger on the old one, and 2.1.5's counters appeared only after a manual `systemctl restart gb10-telemetry`. It also reads the last record from the newest day's file: with more than one day of records, `tail -1` over all of them stopped the script before it printed `installed for <user>`. Hosts that reinstalled 2.1.5 and restarted the logger by hand need nothing more.

## 2.1.5 — 2026-10-06

### Added

- `python -m glm53_tf bench`: the prefill and decode speed of [benchmark method](docs/benchmarks.md#prefill-and-decode-speed) (a 38,960-token prompt with a fresh nonce, then 512 tokens after a short fixed prompt), one JSON line per request with the reply's `prefill_s`, `heat_wait_s` and `cached`, and a summary of medians.
- `python -m glm53_tf long-input`: the [long inputs](docs/benchmarks.md#long-inputs), one passphrase in the middle of a ledger or three at one twentieth from the start, the middle and one twentieth from the end, the length set in lines or fitted to a token count with the engine's `/tokenize`; it exits 1 when a passphrase is missing.
- The [host telemetry](../host/README.md#telemetry-record) records the GPU's cumulative clock event counters (`event_counters_us`: SW power cap, sync boost, SW and HW thermal slowdown, HW power brake). On GB10 the power limit and the memory clock read N/A, and an SW power cap that comes and goes between samples shows only there. The existing fields keep their names and order. Reinstall the host tools to pick it up.

### Documentation

- [Validation](docs/validation.md#prefill-and-decode-speed): on 2.1.4 at TP=2, 22 prompts of 38,960 tokens in two launches, each after a cooling gate, all ran at the faster of the two speeds, and the SW power cap counter did not grow during any of them; it grows only while no engine runs. The cause stays open.
- [Benchmark method](docs/benchmarks.md) names the two commands instead of scripts outside the repository.

### Accepted

On the reference pair on 2026-10-06 at TP=2 with 2.1.4's image (unchanged): `bench` read a 38,961-token prompt at 1,322.0 tok/s and decoded 512 tokens at 35.88 tok/s; `long-input` fitted three passphrases to 59,976 tokens and one passphrase over 800 lines, and the replies held all of them. The new telemetry field read integers on rank 0's host.

## 2.1.4 — 2026-10-06

### Engine

- The image builds TensorFold from the branch `release/2.1.4` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `a265436de869bd596b20a915758de0cc829fb5a0` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.1.1's engine and TensorFold pull request #421 (m-naoki-m), taken before upstream merges it. `_take_over` now decides which kept prompts stay before it copies any, so a new conversation after a long one no longer copies and drops the others first; issue #420 measured that at about 15 GiB per rank. The pull request's tests failed on 2.1.1's engine (3 of 6) and pass on this one, and two upstream tests' fake snapshots gained the `drafter_rows` field the real one has.

### Documentation

- [Operations](docs/operations.md#start-outcomes): a start that refuses the window right after a new image or another engine read the weights, and what to do (the page cache).

### Accepted

Measured on the reference pair on 2026-10-06 at TP=2 with image input on, with the release candidate image (linux/arm64 `sha256:257c69ba7c8586bd8ce5f158e9cf87af6365a78e2b7baa00338d1ac0c0d4a717`, the same on the three hosts):

- The decode check gave 2.1.1's token ids and texts, and the image checks passed.
- Issue #420's scenario: a conversation grown to 247,330 tokens over 11 turns, then one that shares no prefix with it. Through the new conversation `MemAvailable` held at 11–12 GiB on rank 0 and 12–15 GiB on rank 1, and its first request answered in 1.4 s.
- A 200,000×20 image (vLLM #59126's) and a 114,000×28 one were refused with 400 (the decoded pixel limit), and the engine kept serving.
- The engine's own tests: the brief set 1,263 passed; the tiny model's bit checks equal 2.1.1's.

## 2.1.3 — 2026-10-06

### Added

- The decode check and `score-nll` send the server's API key (`Authorization: Bearer`) when `TENSORFOLD_API_KEY` is set where they run, and nothing without it. An engine started with a key, from a `TENSORFOLD_API_KEY` line in rank 0's rank file, refuses every request without it, `/metrics` included; the [Security](README.md#quick-start) note says how to serve beyond loopback with one, and the rank 0 examples carry the line commented out.

### Documentation

- [Validation](docs/validation.md#prefill-and-decode-speed) corrects 2.1.2: a long prompt runs at one of two speeds about 7.5% apart at the same clocks and temperatures, and three prompts back to back held in two launches but not in a third; heat does not explain it and the cause is not known. The claim that the first long prompt after a start is slower is withdrawn (it was fast in one launch). [Decisions](docs/decisions.md) adds TP=2's comparison of `split` and `gather`: about 5% for `split` in both speeds, the same tokens.
- [Setup](SETUP.md#3-image): the image tag names the last version that changed a file the image copies; a version for documents or host-side tools keeps it.
- [CONTRIBUTING](../CONTRIBUTING.md): the 1.x tests that need CUDA or the pinned vLLM image run on the GPU hosts only.

### Accepted

On the reference pair on 2026-10-06 at TP=2 with 2.1.1's image (unchanged) and a key in rank 0's rank file: `/health` answered 200 without the key; `/v1/models` and `/metrics` answered 401 without it or with a wrong one and 200 with it; the decode check with the key gave 2.1.1's token ids and texts; without it, it stopped at 401. Rank 0's serve and memory-guard logs and the check logs did not contain the key.

## 2.1.2 — 2026-10-05

### Documentation

- [Validation](docs/validation.md#prefill-and-decode-speed) no longer says to cool the hosts because back-to-back prefills slow down: on 2.1.1 three 38,960-token prefills without cooling held their speed at TP=2 and TP=3, with the clocks and CPU frequencies unchanged and below the heat wait. The fall from 1,670 to 1,540 tok/s at TP=3 it quoted, seen while 2.0.0 was accepted, did not come back. It also says to run one long prompt after a start before measuring, since the first is slower.

The image, the scripts and the serving defaults are unchanged, so 2.1.1's image and acceptance stand.

## 2.1.1 — 2026-10-05

### Engine

- The image builds TensorFold from the branch `release/2.1.1` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `1a3fb1789830f4c336179eae21129f21c5abae0f` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.1.0's engine and the fix below.

### Fixed

- A request with several images had them encoded in one call of the image tower, and an image's features then changed with the other images in that call (on the real tower, a 448×448 image beside an 896×672 one gave the first different bits wherever it stood). Each image is now its own tower call, so its features are the same whatever else the request carries.

### Accepted

Measured on the reference hosts on 2026-10-05 at TP=2 with image input on, with the release candidate image (linux/arm64 `sha256:54cf0e5bc7fe56a218a91f704443285caa11f68f5389fa618ef577d7b9fcad67`, the same on the three hosts) ([measured](README.md#measured-on-the-release)):

- The decode check gave 2.1.0's token ids, text hashes and acceptance lengths.
- The image checks passed; two images of one size read the same numbers asked one at a time and together.
- Three 38,960-token prefills back to back, without cooling between them, ran at 1,327.0, 1,326.8 and 1,322.8 tok/s. Through them the GPU clock held 2,184 MHz with no clock event reason, every CPU core held its full frequency, and the hottest ACPI zone rose from 56 to 88.5 °C, below the heat wait.

## 2.1.0 — 2026-10-05

### Engine

- The image builds TensorFold from the branch `release/2.1.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `9a1c7cc9fd231c65ebf5bffaed421937303e0796` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.0.0's additions moved onto upstream v0.6.5 without a conflict, plus:
  - **Image input** from upstream pull request #194 (rank 0 encodes, the features go to the other ranks), carried to three ranks, with one image up to the checkpoint's 8,000 visual tokens and rank 0's workspace from a measurement of the tower ([decisions](docs/decisions.md#engine-commits-not-named-elsewhere)).
  - The latent path's second copy of `kv_b` (`latent.AbsorbW`, `AbsorbQ4`) counted in the weights' bytes and the startup estimate, which had left it out.
- Upstream v0.6.5 brings API keys (`--api-key`, `--api-key-file`, `TENSORFOLD_API_KEY`); this line sets none ([Quick Start](README.md#quick-start)).

### Serving defaults

- **Image input is on, by a switch in the rank file**: `VISION=1` on every rank, as the examples set it, makes `serve.sh` pass `--vision`; `VISION=0` turns it off. The window is unchanged; at TP=2 rank 0 holds the 1.05 GiB tower and other conversations' kept prompts get 2.4 GiB of the default 3 GiB (TP=3 keeps the 3 GiB).
- **TP=2 opens four NCCL channels and names the IB transport** in its rank files, as TP=3 does: decode +0.8-1.0% and about 1.5 GiB more room at start against the 64 channels NCCL opened on its own, prefill within 0.4%. Pinning the ranks to the performance cores and fixed draft depths were measured and not taken ([decisions](docs/decisions.md)).

### Fixed

- The decode check kept one field of a streamed delta, so when a draft round's chunk ended the reasoning and started the content it dropped the reasoning's tail ("200." read "200"), and its text hash moved with the draft depth while the token ids did not. It keeps both now. Counting and code have new reference hashes for their texts ([validation](docs/validation.md#decode-check)); the token ids are 2.0.0's.

### Accepted

Measured on the reference hosts on 2026-10-05 with the release candidate image (linux/arm64 `sha256:d4d2014ca311841a5ff65c09d97a33abdf2c7db00ba4386dc7ecf7fd689cbb69`, the same on the three hosts) ([measured](README.md#measured-on-the-release)):

- The decode check gave 2.0.0's token ids and acceptance lengths at TP=2 and TP=3, with image input off and on.
- At TP=2 with image input off, the NLL set equalled 2.0.0's at full precision, and three 38,960-token prefills ran at 1,221.5 (the first), 1,331.1 and 1,329.9 tok/s.
- Image input at both TP sizes: one image, a 4:3 image of 7,966 prompt tokens, two images in order, a single colour, an image in a tool result, a text question and a tool round trip answered correctly; a video part was refused with 400.

The other 2.0.0 results stand: the prompt and decode paths give the same tokens. The tag in the commands is `glm53-tf:2.1.0`.

## 2.0.10 — 2026-10-05

### Documentation

- [Decisions](docs/decisions.md) lists LPA among 1.x's measures 2.x has not taken up: 1.x's late-prefill approximation changes a long prefill's result by design, while 2.x's reference hashes and NLL are the exact prefill's.
- The [QSFP network](../docs/qsfp-network.md#8-three-hosts-in-a-ring) page says that its dummy interface `glmhost` is an example name; the reference ring's is `tp3host0`, the name this line's TP=3 rank files give `NCCL_SOCKET_IFNAME`.

The image, the scripts and the serving defaults are unchanged, so 2.0.7's image and acceptance stand.

## 2.0.9 — 2026-10-05

### Tests

- The tool-argument gate's test of an oversized body waits for the gate's handler threads to end before it checks that nothing reached the upstream, instead of sleeping 0.3 s; a relay put back 0.5 s late now fails it.

### Changed

- CI installs the check tools from the checkout root's `requirements/dev.lock.txt` (Ruff, one version for every line) rather than from 1.x's lock ([CONTRIBUTING](../CONTRIBUTING.md)).

The image, the scripts and the serving defaults are unchanged, so 2.0.7's image and acceptance stand.

## 2.0.8 — 2026-10-05

### Documentation

- The comparison with 1.x said that 1.x handled heat with the cooling gate and the thermal watch. 1.x has no wait in the engine; its measurements rested the hosts between requests with a cooling gate, and no record shows the thermal watch on 1.x.
- The cluster file's `CHECKOUT` is the repository's root on every host, where 1.x's `--checkout` names its `v1/`; the configuration table says so.

### Tests

- The test of a paused download under `--wait` is one test with all its checks; the separate `test_transfer_state.py` repeated it.

The image, the scripts and the serving defaults are unchanged, so 2.0.7's image and acceptance stand (the repository's `.dockerignore` lost lines that admitted nothing more; the build context is the same).

## 2.0.7 — 2026-10-05

### Changed

- The image is rebuilt and accepted again. The Dockerfile pins NVIDIA's base by digest (`nvcr.io/nvidia/pytorch@sha256:2140e699…`, the one 2.0.0 was accepted on) instead of the tag `26.07-py3`; the image carries a changed `THIRD_PARTY_NOTICES.md` (the licensing guide's new place, and that this image carries the file) and a corrected comment in `serve.sh`. The base, the packages and the engine are 2.0.0's, layer for layer. On 2026-10-05 the rebuilt image was accepted on the reference hosts by equivalence: at TP=2 and TP=3 the [decode check](docs/validation.md#decode-check) gave the reference hashes, token ids and acceptance lengths, and the NLL set equalled 2.0.0's at full precision. 2.0.0's other results stand for it. The tag in the commands is `glm53-tf:2.0.7`.
- The host tools moved from `v2/host/` to [`host/`](../host/README.md) at the checkout root, beside the [host preparation](../docs/hosts.md) and fabric pages every line shares: `python3 host/cool-gate`, `python3 host/thermal-watch`, and `sudo sh install.sh` from `host/`.
- The cluster file goes to `state/cluster.env`, which Git ignores; the steps had it at `my-cluster.env` in the checkout root, which Git does not ignore.

### Added

- [Operations](docs/operations.md): how a start ends, a rank that stops while the others wait, NCCL over sockets, recreating the container, moving to a new image, a host that powered off, handing the hosts to 1.x.
- [Decisions](docs/decisions.md): what 2.x adopted or rejected, with the date, the measured effect and what would reopen it; the release branch's commits the changelog does not name; the measures from 1.x not yet evaluated on 2.x.
- [Benchmark method](docs/benchmarks.md): how the release measurements and the validation references were taken.

### Documentation

- [Setup](SETUP.md) §6 and §9 say how `cluster.sh` start ends (READY, FAILED with every rank's log tail, TIMEOUT after 15 minutes), where the logs are, and that stop waits up to 60 s a rank. The README names `TF_GLM_CACHE_GIB` and the endpoints the NLL check uses, and its prefill row says that TP=2's three prompts ran back to back after one cooling.

### Tests

- The pages' quotes of `serve.sh`, the scripts' defaults, the gate's ports, `TENSORFOLD_REF`, the pinned base and revision are tested in both languages; the cluster file stays under `state/`; every shell script must parse. Two checks lost in the copy from 1.x are back (the body score-nll sends, and the decode check's token record read by decode-divergence).

## 2.0.6 — 2026-10-04

### Added

- The publication audit now checks this line too: its required files, a release version with a changelog section in both languages, the Apache-2.0 license and a pinned model revision in `config/model.lock.json`.

### Documentation

- The release measurements describe the engine builds they ran on (the release, the build one printed line before it, a build before the heat wait) instead of naming unreleased commits, and say that without the heat wait the [thermal watch](../host/README.md#during-long-runs) stopped the engine at 94 °C, as recorded. The slowing of prefill as a host heats is stated once, in [validation](docs/validation.md#prefill-and-decode-speed). The 1.x column of the comparison names its sources in 1.x's benchmarks.

The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

## 2.0.5 — 2026-10-04

### Changed

- This line runs its own tools: [`glm53_tf`](README.md#repository-layout), run from `v2/` as `python -m glm53_tf download | verify-download | tool-gate | decode-check | decode-divergence | score-nll`, in place of 1.x's tools from `v1/`. They are copies of 1.x's, with the same arguments; the decode check and the tool-argument gate default to this line's engine (`http://127.0.0.1:8095`, model `glm-tf`; the gate listens on 8896). The model pin is `config/model.lock.json`, the NLL set `config/nll_set.json` (a byte copy of 1.x's) and the Hugging Face client lock `requirements/huggingface.lock.txt`; tests keep `scripts/serve.sh`'s revision and the set's hash from drifting. The [setup runbook](SETUP.md) and [validation](docs/validation.md) give the new commands. The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

### Documentation

- [`host/`](../host/README.md) records what was checked on a reference host without sudo (the logger, `cool-gate` in both outcomes, `thermal-watch` stopping a process started in the container) and that `thermal-watch` cannot stop a container's PID 1.
- The repository README says that each line is self-contained and that the root's `tools/` holds the repository's publication audit and release notes.

## 2.0.4 — 2026-10-04

### Fixed

- `host/gb10-telemetry` and the host-tool tests write `datetime.UTC` for UTC, the spelling ruff asks for on Python 3.11 and later; 2.0.3's CI stopped on it. Nothing else changes.

## 2.0.3 — 2026-10-04

### Added

- [`host/`](../host/README.md): the hosts' thermal tools this line was measured with, which lived only in the maintainer's records: the GPU clock-cap unit, the telemetry logger with its unit and installer, `cool-gate` (waits for a host to cool between long requests) and `thermal-watch` (stops the engine after two readings in a row at or above 94 °C). The installer takes the service user as an argument; `thermal-watch` was verified with this line's engine only. Their CPU tests are in `tests/`, and CI runs them.

### Documentation

- The comparison with 1.x cites 1.x's published TP=3 decode check, 51.00 / 30.10 / 39.48 tok/s; 49.59 / 28.32 / 38.33 came from a run with a prefill cap of 512 that no template sets. The 1.x tool-argument gate result is TP=2's, the rows that compare runs of other lengths give 1.x's lengths, and the NLL row names its set.
- What both lines share moved to the [repository README](../README.md). The facts 1.x owns (the clock cap, the checkpoint size per host, the host kernel, the download, the decode check, the repeatability switches) are pointed to instead of restated; [validation](docs/validation.md) keeps the reference values and states the decode check's prompt as `decode_check.py` does.
- The example cluster files name the default clone directory as `CHECKOUT`.

The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

## 2.0.2 — 2026-10-04

### Documentation

- [Next Action](README.md#next-action), from a review of upstream and the recipes on 2026-10-04:
  - Upstream reviews pull request #320 for 0.6.6 as the GLM stop on both ranks, not #301, which the release branch carries; either one merged replaces #301. None of this line's issues #308, #309, #310, #339 and pull request #333 is on upstream's list for 0.6.6.
  - Following upstream to v0.6.5 brings API keys to the engine. The security note in [Quick Start](README.md#quick-start) now says that the missing authentication is v0.6.4's.
  - Upstream 0.6.6 is watched for three fixes this line meets: tool-call markup leaking into the reply text, a guard against a token repeated without end, and the open-file limit.
  - Image input reads upstream pull request #194 (GLM-5.3-Flash image input on CUDA over two ranks) before wiring its own.
  - The hosts' CPU-frequency check in 1.x's Next Action applies to this line's figures too.

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
