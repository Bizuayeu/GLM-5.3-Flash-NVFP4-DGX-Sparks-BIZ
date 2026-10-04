"""The decode check after a switch: 512 greedy tokens after a fixed ~2,048-token prompt, with the completion.

Run on rank 0 against the loopback API, once per task type (PROMPT_KIND=count|prose|code), SAMPLES times at
temperature 0. Each sample prints one JSON line with the speed, the hash of the completion text and the hash of
its token ids (`return_token_ids`; TensorFold returns them in the reply's `tensorfold` block); the summary
carries the MTP acceptance length over the run, 1 + accepted / draft rounds: from vLLM's `/metrics` counters,
or on TensorFold from each reply's `tensorfold` block (`rounds`, `accepted`; `acceptance_from` says so, and
`acceptance_null` why a TensorFold run has none). TOKENS_OUT, a path, receives the completion text and token
ids of every sample, so two launches can be compared at their first diverging token with decode_divergence.py.
On vLLM the prompt stays below one prefix-cache block, so the prefix cache is not involved. TensorFold keeps
whole prompts and has no request field or endpoint that drops them, so before each sample TF_GLM_CACHE_ENTRIES
short distinct requests push the kept prompts out (`evicted_before_each`); each row's `cached` shows the
result. Within a launch the samples agree, and across launches the hashes are compared with the previous launch
of the same profile (docs/launch-safety.md, "After a switch").

    PROMPT_KIND=prose SAMPLES=3 TOKENS_OUT=../records/<run>/tokens-prose.json python3 tools/decode_check.py

Environment: BASE (default http://127.0.0.1:8893), MODEL (default glm-5.3-flash-nvidia), PROMPT_TOKENS (2048),
MAX_TOKENS (512), SAMPLES (3), TF_GLM_CACHE_ENTRIES (8, TensorFold's default; set it to the server's value).
Same measurement as the decode rows of docs/benchmarks.md since 1.6.0.
"""

import hashlib
import json
import os
import re
import statistics
import time
import urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1:8893")
MODEL = os.environ.get("MODEL", "glm-5.3-flash-nvidia")
PROMPT_TOKENS = int(os.environ.get("PROMPT_TOKENS", "2048"))
SAMPLES = int(os.environ.get("SAMPLES", "3"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "512"))
KIND = os.environ.get("PROMPT_KIND", "count")
TF_GLM_CACHE_ENTRIES = int(os.environ.get("TF_GLM_CACHE_ENTRIES", "8"))
TASKS = {
    "count": "Count upward from one, one number per line.",
    "prose": "上の行は無視して、日本の古代の道路網と現代の物流網の関係について、"
    "具体例を挙げながら随筆を書いてください。段落を分け、最後まで書き切ってください。",
    "code": "Ignore the lines above. Write a complete Python module implementing an LRU "
    "cache with TTL expiry, a thread-safe API, docstrings, type hints and unit tests.",
}
TEMPLATE = {"reasoning_effort": "low", "clear_thinking": True}
COUNTERS = {
    "vllm:spec_decode_num_drafts_total": "num_drafts",
    "vllm:spec_decode_num_draft_tokens_total": "num_draft_tokens",
    "vllm:spec_decode_num_accepted_tokens_total": "num_accepted_tokens",
    "vllm:generation_tokens_total": "generation_tokens",
}


def post(path, body, timeout=900):
    req = urllib.request.Request(
        BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    return urllib.request.urlopen(req, timeout=timeout)


def spec_counters():
    text = urllib.request.urlopen(BASE + "/metrics", timeout=10).read().decode()
    out = {}
    for line in text.splitlines():
        match = re.match(r"([a-z_:]+)(?:\{[^}]*\})? ([0-9.e+-]+)$", line)
        if match and match[1] in COUNTERS:
            out[COUNTERS[match[1]]] = out.get(COUNTERS[match[1]], 0.0) + float(match[2])
    return out, any(line.startswith("tensorfold:") for line in text.splitlines())


def evict():
    """Push TensorFold's kept prompts out: its GLM engine resumes a later prompt from
    the longest kept strict prefix and keeps the last TF_GLM_CACHE_ENTRIES prompts."""
    for i in range(TF_GLM_CACHE_ENTRIES):
        body = {
            "model": MODEL,
            "messages": [{"role": "user", "content": f"Say ok. {time.time_ns()} {i}"}],
            "max_tokens": 1,
            "temperature": 0,
            "chat_template_kwargs": TEMPLATE,
        }
        with post("/v1/chat/completions", body) as r:
            r.read()


def prompt_text():
    # About 10 tokens per line on this tokenizer; the usage field gives the exact count.
    lines = "".join(
        f"measurement line {i} of the fixed decode prompt.\n"
        for i in range(PROMPT_TOKENS // 10)
    )
    return f"{lines}{TASKS[KIND]}"


def decode(prompt):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "ignore_eos": True,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": TEMPLATE,
        "return_token_ids": True,
    }
    start = time.monotonic()
    first = None
    spec = None
    usage = None
    text = hashlib.sha256()
    pieces = []
    ids = []
    with post("/v1/chat/completions", body) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                usage = chunk["usage"]
            if chunk.get("tensorfold"):
                spec = chunk["tensorfold"]
            choice = (chunk.get("choices") or [{}])[0]
            if choice.get("token_ids"):
                ids.extend(choice["token_ids"])
            delta = choice.get("delta") or {}
            piece = (
                delta.get("content")
                or delta.get("reasoning_content")
                or delta.get("reasoning")
            )
            if piece:
                text.update(piece.encode())
                pieces.append(piece)
                if first is None:
                    first = time.monotonic()
    end = time.monotonic()
    if not ids and spec and spec.get("token_ids"):
        ids = spec["token_ids"]
    tokens = usage["completion_tokens"]
    row = {
        "kind": "decode",
        "prompt_tokens": usage["prompt_tokens"],
        "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        "completion_tokens": tokens,
        "ttft": round(first - start, 3),
        "seconds_after_first": round(end - first, 3),
        "tok_per_s": round((tokens - 1) / (end - first), 2),
        "completion_sha256": text.hexdigest()[:16],
        "token_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:16],
        "n_token_ids": len(ids),
    }
    return row, {"text": "".join(pieces), "token_ids": ids}, spec


def acceptance(before, after, blocks):
    """The acceptance length and any keys it adds to the summary.

    vLLM: the counter deltas over the run. TensorFold, whose `/metrics` has no draft rounds: the sum of the
    replies' `tensorfold` blocks, exact per request. Without drafts both give null.
    """
    if not any(blocks):
        drafts = after.get("num_drafts", 0) - before.get("num_drafts", 0)
        accepted = after.get("num_accepted_tokens", 0) - before.get(
            "num_accepted_tokens", 0
        )
        return (round(1 + accepted / drafts, 3) if drafts else None), {}
    extra = {"acceptance_from": "tensorfold reply blocks"}
    if not all(b and "rounds" in b and "accepted" in b for b in blocks):
        return None, dict(extra, acceptance_null="a reply without rounds/accepted")
    rounds = sum(b["rounds"] for b in blocks)
    if not rounds or not sum(b.get("drafted", 0) for b in blocks):
        return None, dict(extra, acceptance_null="no drafts")
    return round(1 + sum(b["accepted"] for b in blocks) / rounds, 3), extra


def main():
    prompt = prompt_text()
    before, tensorfold = spec_counters()
    rows = []
    fulls = []
    blocks = []
    for _ in range(SAMPLES):
        if tensorfold:
            evict()
        row, full, spec = decode(prompt)
        rows.append(row)
        fulls.append(full)
        blocks.append(spec)
        print(json.dumps(row), flush=True)
    after, _ = spec_counters()
    if os.environ.get("TOKENS_OUT"):
        with open(os.environ["TOKENS_OUT"], "w", encoding="utf-8") as f:
            json.dump(
                {"kind": KIND, "samples": [dict(r, **x) for r, x in zip(rows, fulls)]},
                f,
                ensure_ascii=False,
            )
    speeds = [r["tok_per_s"] for r in rows]
    length, extra = acceptance(before, after, blocks)
    if tensorfold:
        extra["evicted_before_each"] = TF_GLM_CACHE_ENTRIES
    print(
        json.dumps(
            {
                "summary": {
                    "samples": len(rows),
                    "kind": KIND,
                    "median_tok_per_s": round(statistics.median(speeds), 2),
                    "min_tok_per_s": min(speeds),
                    "max_tok_per_s": max(speeds),
                    "acceptance_length": length,
                    "distinct_completions": len({r["completion_sha256"] for r in rows}),
                    **extra,
                },
                "all": speeds,
                "spec_before": before,
                "spec_after": after,
                "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
