"""Prefill and decode speed, as docs/benchmarks.md ("Prefill and decode speed") describes.

Run on rank 0 against the loopback API, one request at a time, temperature 0, effort low.
prefill: one user message, a line `nonce <a fresh UUID>`, --lines fixed lines and `Reply ok.`,
  max_tokens 1; the default 3,200 lines give 38,960 tokens with the chat template. The rate is the
  prompt tokens over the request's wall time at the client. The engine has no endpoint that drops its
  kept prompts, so the fresh nonce keeps any of them from matching; each row's `cached` shows it.
decode: `Count upward from one, one number per line.`, streamed, 512 tokens with ignore_eos. The rate
  is the completion tokens after the first over the time after the first streamed token; the prompt is
  the same every time, so the acceptance stays comparable between runs.
Each row also carries the reply's `tensorfold` fields prefill_s, heat_wait_s and cached, and the
request's start and end epochs. One JSON line per request, then a summary with each kind's median.

    python -m glm53_tf bench --kinds prefill --runs 1 --lines 250    (warm-up, about 3,000 tokens)
    python -m glm53_tf bench --out ../records/<run>/bench.jsonl

Environment: BASE (default http://127.0.0.1:8095), MODEL (default glm-tf), TENSORFOLD_API_KEY (sent as
the bearer token when set). The prompts and requests are those of the scripts that took the release's
figures, copied, so the same measurement reads the same.
"""

import argparse
import json
import os
import statistics
import time
import urllib.request
import uuid

BASE = os.environ.get("BASE", "http://127.0.0.1:8095")
MODEL = os.environ.get("MODEL", "glm-tf")
LINES = 3200
KINDS = ("prefill", "decode")
TEMPLATE = {"reasoning_effort": "low", "clear_thinking": True}
KEPT = ("prefill_s", "heat_wait_s", "cached")


def auth():
    """The server's API key, when TENSORFOLD_API_KEY is set where the bench runs."""
    key = os.environ.get("TENSORFOLD_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def post(path, body, timeout=900):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", **auth()},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def prefill_body(nonce, lines=LINES):
    text = "".join(
        f"measurement line {i} of the fixed prefill prompt.\n" for i in range(lines)
    )
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"nonce {nonce}\n{text}Reply ok."}],
        "max_tokens": 1,
        "temperature": 0,
        "chat_template_kwargs": TEMPLATE,
    }


def decode_body():
    return {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "Count upward from one, one number per line."}
        ],
        "max_tokens": 512,
        "ignore_eos": True,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": TEMPLATE,
    }


def kept(block):
    """The fields of the reply's `tensorfold` block a row keeps."""
    return {k: v for k, v in (block or {}).items() if k in KEPT}


def prefill(lines):
    start_epoch = time.time()
    start = time.monotonic()
    with post("/v1/chat/completions", prefill_body(uuid.uuid4(), lines)) as r:
        reply = json.load(r)
    seconds = time.monotonic() - start
    usage = reply["usage"]
    return {
        "kind": "prefill",
        "prompt_tokens": usage["prompt_tokens"],
        "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        "seconds": round(seconds, 3),
        "tok_per_s": round(usage["prompt_tokens"] / seconds, 1),
        "tensorfold": kept(reply.get("tensorfold")),
        "start_epoch": round(start_epoch, 1),
        "end_epoch": round(time.time(), 1),
    }


def decode():
    start_epoch = time.time()
    start = time.monotonic()
    first = None
    usage = None
    block = None
    with post("/v1/chat/completions", decode_body()) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                usage = chunk["usage"]
            if chunk.get("tensorfold"):
                block = chunk["tensorfold"]
            delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
            if first is None and (
                delta.get("content")
                or delta.get("reasoning_content")
                or delta.get("reasoning")
            ):
                first = time.monotonic()
    end = time.monotonic()
    tokens = usage["completion_tokens"]
    return {
        "kind": "decode",
        "completion_tokens": tokens,
        "ttft": round(first - start, 3),
        "seconds_after_first": round(end - first, 3),
        "tok_per_s": round((tokens - 1) / (end - first), 2),
        "tensorfold": kept(block),
        "start_epoch": round(start_epoch, 1),
        "end_epoch": round(time.time(), 1),
    }


def kinds(text):
    names = text.split(",")
    unknown = [k for k in names if k not in KINDS]
    if unknown:
        raise argparse.ArgumentTypeError("unknown kind: " + ", ".join(unknown))
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--kinds",
        type=kinds,
        default=list(KINDS),
        help="comma-separated, run in this order (default prefill,decode)",
    )
    parser.add_argument("--runs", type=int, default=3, help="requests of each kind")
    parser.add_argument("--lines", type=int, default=LINES, help="the prefill's lines")
    parser.add_argument("--out", help="a JSONL file that receives one row per request")
    args = parser.parse_args(argv)
    speeds = {}
    for kind in args.kinds:
        for _ in range(args.runs):
            row = prefill(args.lines) if kind == "prefill" else decode()
            speeds.setdefault(kind, []).append(row["tok_per_s"])
            if args.out:
                with open(args.out, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
    print(
        json.dumps(
            {
                "summary": {k: statistics.median(v) for k, v in speeds.items()},
                "all": speeds,
                "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
