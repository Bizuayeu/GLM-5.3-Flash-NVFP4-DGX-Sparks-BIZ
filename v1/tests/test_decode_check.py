import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import decode_check, decode_divergence

VLLM_METRICS = (
    "# HELP vllm:spec_decode_num_drafts_total drafts\n"
    'vllm:spec_decode_num_drafts_total{{engine="0"}} {drafts}\n'
    'vllm:spec_decode_num_draft_tokens_total{{engine="0"}} {draft_tokens}\n'
    'vllm:spec_decode_num_accepted_tokens_total{{engine="0"}} {accepted}\n'
    'vllm:generation_tokens_total{{engine="0"}} {generated}\n'
)
FLAT = VLLM_METRICS.format(drafts=0, draft_tokens=0, accepted=0, generated=0)


def stream(ids=(16, 17)):
    """A streamed chat reply: one content chunk per id with its ids, then the end
    chunk and usage, as vLLM sends them with `return_token_ids`."""
    chunks = [
        {"choices": [{"delta": {"content": f"{t}\n"}, "token_ids": [t]}]} for t in ids
    ]
    end = {"choices": [{"delta": {}, "finish_reason": "length"}]}
    usage = {"prompt_tokens": 2066, "completion_tokens": len(ids)}
    chunks += [end, {"choices": [], "usage": usage}]
    return [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [b"data: [DONE]\n"]


class Reply(list):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"".join(self)


def run(replies, metrics, sent=None, tokens_out=None):
    """Run main() against canned replies; return its printed JSON lines.

    A streamed request gets the next reply, any other a short non-streamed one;
    `sent` collects every request body in order.
    """
    replies, metrics = iter(replies), iter(metrics)
    sent = [] if sent is None else sent

    def urlopen(req, timeout=None):
        if isinstance(req, str):
            return Reply([next(metrics).encode()])
        body = json.loads(req.data)
        sent.append(body)
        if body.get("stream"):
            return Reply(next(replies))
        return Reply(
            [json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()]
        )

    out = io.StringIO()
    clock = iter(range(1000))
    env = {"TOKENS_OUT": tokens_out} if tokens_out else {}
    with (
        patch.object(decode_check.urllib.request, "urlopen", urlopen),
        patch.object(decode_check.time, "monotonic", lambda: next(clock)),
        patch.object(decode_check, "SAMPLES", 3),
        patch.dict(os.environ, env),
        contextlib.redirect_stdout(out),
    ):
        decode_check.main()
    return [json.loads(line) for line in out.getvalue().splitlines()]


class TextTests(unittest.TestCase):
    def test_a_chunk_with_reasoning_and_content_keeps_both(self):
        """A draft round's chunk can end the reasoning and start the content; the text keeps both, in order."""
        chunks = [
            {
                "choices": [
                    {"delta": {"reasoning_content": "go to 200"}, "token_ids": [7]}
                ]
            },
            {
                "choices": [
                    {
                        "delta": {"reasoning_content": ".", "content": "1\n"},
                        "token_ids": [8],
                    }
                ]
            },
            {"choices": [{"delta": {"content": "2\n"}, "token_ids": [9]}]},
            {"choices": [{"delta": {}, "finish_reason": "length"}]},
            {"choices": [], "usage": {"prompt_tokens": 2066, "completion_tokens": 3}},
        ]
        reply = [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [
            b"data: [DONE]\n"
        ]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tokens.json")
            lines = run([reply] * 3, [FLAT, FLAT], tokens_out=path)
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
        want = "go to 200.1\n2\n"
        self.assertEqual(saved["samples"][0]["text"], want)
        self.assertEqual(
            lines[0]["completion_sha256"],
            hashlib.sha256(want.encode()).hexdigest()[:16],
        )


class AcceptanceLengthTests(unittest.TestCase):
    def test_vllm_reads_the_counter_deltas_and_adds_no_key(self):
        before = VLLM_METRICS.format(
            drafts=10, draft_tokens=30, accepted=20, generated=0
        )
        after = VLLM_METRICS.format(
            drafts=160, draft_tokens=480, accepted=390, generated=9
        )
        lines = run([stream()] * 3, [before, after])
        self.assertEqual(
            list(lines[-1]["summary"]),
            [
                "samples",
                "kind",
                "median_tok_per_s",
                "min_tok_per_s",
                "max_tok_per_s",
                "acceptance_length",
                "distinct_completions",
            ],
        )
        self.assertEqual(
            lines[-1]["summary"]["acceptance_length"], round(1 + 370 / 150, 3)
        )
        self.assertEqual(lines[0]["n_token_ids"], 2)

    def test_vllm_without_drafts_stays_null(self):
        summary = run([stream()] * 3, [FLAT, FLAT])[-1]["summary"]
        self.assertIsNone(summary["acceptance_length"])


class TokensOutTests(unittest.TestCase):
    def test_decode_divergence_finds_the_first_differing_token_in_tokens_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [str(Path(tmp) / "a.json"), str(Path(tmp) / "b.json")]
            for path, ids in zip(paths, ([16, 17, 18], [16, 99, 18])):
                run([stream(ids)] * 3, [FLAT] * 2, tokens_out=path)
            saved = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
            self.assertEqual(saved["samples"][0]["token_ids"], [16, 17, 18])
            out = io.StringIO()
            with (
                patch.object(decode_divergence.sys, "argv", ["dd", *paths]),
                contextlib.redirect_stdout(out),
            ):
                decode_divergence.main()
        first = out.getvalue().splitlines()[0]
        self.assertIn("first differing token 1/3 (ids [17, 18] vs [99, 18])", first)


class RequestTests(unittest.TestCase):
    def test_only_the_samples_are_sent(self):
        sent = []
        run([stream()] * 3, [FLAT, FLAT], sent)
        self.assertEqual([b.get("stream") for b in sent], [True] * 3)


if __name__ == "__main__":
    unittest.main()
