import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_tf import bench

# The reply's block on TensorFold: bench keeps prefill_s, heat_wait_s and cached.
BLOCK = {"prefill_s": 30.25, "heat_wait_s": 1.5, "cached": 0, "rounds": 1}
BLOCK_KEPT = {"prefill_s": 30.25, "heat_wait_s": 1.5, "cached": 0}


def prefill_reply(prompt_tokens=38960, cached=0):
    reply = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "length"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 1,
            "prompt_tokens_details": {"cached_tokens": cached},
        },
        "tensorfold": dict(BLOCK, token_ids=[7]),
    }
    return [json.dumps(reply).encode()]


def decode_reply(n=4):
    """A streamed reply: one reasoning chunk, then content, the end chunk and usage."""
    chunks = [{"choices": [{"delta": {"reasoning_content": "go"}}]}]
    chunks += [{"choices": [{"delta": {"content": f"{i}\n"}}]} for i in range(n - 1)]
    chunks += [
        {
            "choices": [{"delta": {}, "finish_reason": "length"}],
            "tensorfold": dict(BLOCK, token_ids=list(range(n))),
        },
        {"choices": [], "usage": {"prompt_tokens": 17, "completion_tokens": n}},
    ]
    return [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [b"data: [DONE]\n"]


class Reply(list):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"".join(self)


def run(argv, sent=None, auth=None):
    """Run main() against canned replies; return its printed JSON lines.

    Every monotonic reading is one second after the previous; `sent` collects the
    request bodies and `auth` their Authorization headers.
    """
    sent = [] if sent is None else sent
    auth = [] if auth is None else auth

    def urlopen(req, timeout=None):
        auth.append(req.get_header("Authorization"))
        body = json.loads(req.data)
        sent.append(body)
        return Reply(decode_reply() if body.get("stream") else prefill_reply())

    out = io.StringIO()
    clock = iter(range(1000))
    with (
        patch.object(bench.urllib.request, "urlopen", urlopen),
        patch.object(bench.time, "monotonic", lambda: next(clock)),
        patch.object(bench.time, "time", lambda: 1759700000.04),
        contextlib.redirect_stdout(out),
    ):
        bench.main(argv)
    return [json.loads(line) for line in out.getvalue().splitlines()]


class PromptTests(unittest.TestCase):
    def test_the_prefill_prompt_is_the_documented_one(self):
        body = bench.prefill_body("N")
        text = body["messages"][0]["content"]
        lines = text.split("\n")
        self.assertEqual(bench.LINES, 3200)
        self.assertEqual(lines[0], "nonce N")
        self.assertEqual(lines[1], "measurement line 0 of the fixed prefill prompt.")
        self.assertEqual(
            lines[3200], "measurement line 3199 of the fixed prefill prompt."
        )
        self.assertEqual(lines[-1], "Reply ok.")
        self.assertEqual(len(lines), 3202)
        self.assertEqual(body["messages"][0]["role"], "user")
        self.assertEqual(
            {k: body[k] for k in ("model", "max_tokens", "temperature")},
            {"model": bench.MODEL, "max_tokens": 1, "temperature": 0},
        )
        self.assertEqual(
            body["chat_template_kwargs"],
            {"reasoning_effort": "low", "clear_thinking": True},
        )
        self.assertNotIn("stream", body)

    def test_the_line_count_can_be_changed(self):
        text = bench.prefill_body("N", 250)["messages"][0]["content"]
        self.assertEqual(len(text.split("\n")), 252)

    def test_every_prefill_has_a_fresh_nonce(self):
        sent = []
        run(["--kinds", "prefill", "--runs", "2"], sent=sent)
        first = [b["messages"][0]["content"].split("\n")[0] for b in sent]
        self.assertEqual(len(set(first)), 2)
        self.assertTrue(all(line.startswith("nonce ") for line in first))

    def test_the_decode_prompt_is_the_documented_one(self):
        body = bench.decode_body()
        self.assertEqual(
            body["messages"],
            [
                {
                    "role": "user",
                    "content": "Count upward from one, one number per line.",
                }
            ],
        )
        self.assertEqual(
            {k: body[k] for k in ("max_tokens", "ignore_eos", "temperature", "stream")},
            {"max_tokens": 512, "ignore_eos": True, "temperature": 0, "stream": True},
        )
        self.assertEqual(body["stream_options"], {"include_usage": True})
        self.assertEqual(
            body["chat_template_kwargs"],
            {"reasoning_effort": "low", "clear_thinking": True},
        )


class RowTests(unittest.TestCase):
    def test_a_prefill_row(self):
        (row, summary) = run(["--kinds", "prefill", "--runs", "1"])
        self.assertEqual(
            row,
            {
                "kind": "prefill",
                "prompt_tokens": 38960,
                "cached": 0,
                "seconds": 1.0,
                "tok_per_s": 38960.0,
                "tensorfold": BLOCK_KEPT,
                "start_epoch": 1759700000.0,
                "end_epoch": 1759700000.0,
            },
        )

    def test_a_decode_row_times_from_the_first_streamed_token(self):
        # monotonic: 0 at the request, 1 at the first (reasoning) piece, 2 at the end.
        (row, summary) = run(["--kinds", "decode", "--runs", "1"])
        self.assertEqual(
            row,
            {
                "kind": "decode",
                "completion_tokens": 4,
                "ttft": 1.0,
                "seconds_after_first": 1.0,
                "tok_per_s": 3.0,
                "tensorfold": BLOCK_KEPT,
                "start_epoch": 1759700000.0,
                "end_epoch": 1759700000.0,
            },
        )

    def test_a_reply_without_a_block_records_an_empty_one(self):
        self.assertEqual(bench.kept(None), {})
        self.assertEqual(bench.kept({"rounds": 3}), {})


class RunTests(unittest.TestCase):
    def test_kinds_in_order_runs_each_and_the_summary_takes_medians(self):
        lines = run(["--runs", "3"])
        self.assertEqual(
            [r["kind"] for r in lines[:-1]], ["prefill"] * 3 + ["decode"] * 3
        )
        summary = lines[-1]
        self.assertEqual(
            summary["summary"], {"prefill": 38960.0, "decode": 3.0}, summary
        )
        self.assertEqual(summary["all"]["prefill"], [38960.0] * 3)
        self.assertIn("at", summary)

    def test_runs_default_to_three(self):
        lines = run(["--kinds", "decode"])
        self.assertEqual(len(lines), 4)

    def test_out_appends_one_row_per_request(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "bench.jsonl")
            path.write_text('{"earlier": 1}\n', encoding="utf-8")
            lines = run(
                ["--kinds", "prefill,decode", "--runs", "1", "--out", str(path)]
            )
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(rows, [{"earlier": 1}] + lines[:-1])

    def test_an_unknown_kind_is_a_usage_error(self):
        with (
            self.assertRaises(SystemExit) as caught,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            bench.main(["--kinds", "prefill,nope"])
        self.assertEqual(caught.exception.code, 2)


class ApiKeyTests(unittest.TestCase):
    def test_with_a_key_every_request_carries_it(self):
        auth = []
        with patch.dict(os.environ, {"TENSORFOLD_API_KEY": "k1"}):
            run(["--runs", "1"], auth=auth)
        self.assertEqual(auth, ["Bearer k1"] * 2)

    def test_without_a_key_no_request_carries_one(self):
        auth = []
        with patch.dict(os.environ):
            os.environ.pop("TENSORFOLD_API_KEY", None)
            run(["--runs", "1"], auth=auth)
        self.assertEqual(auth, [None] * 2)


if __name__ == "__main__":
    unittest.main()
