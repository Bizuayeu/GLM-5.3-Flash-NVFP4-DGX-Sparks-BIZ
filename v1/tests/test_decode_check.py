import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from tools import decode_check, decode_divergence

# The stream's last chunk on TensorFold (records/20261003-tp3/t5, U3 on b1-2rail).
TF_BLOCK = {"rounds": 26, "accepted": 38, "drafted": 59, "tokens_per_round": 2.423}
VLLM_METRICS = (
    "# HELP vllm:spec_decode_num_drafts_total drafts\n"
    'vllm:spec_decode_num_drafts_total{{engine="0"}} {drafts}\n'
    'vllm:spec_decode_num_draft_tokens_total{{engine="0"}} {draft_tokens}\n'
    'vllm:spec_decode_num_accepted_tokens_total{{engine="0"}} {accepted}\n'
    'vllm:generation_tokens_total{{engine="0"}} {generated}\n'
)
TF_METRICS = (
    "tensorfold:spec_decode_num_draft_tokens_total 4304\n"
    "tensorfold:spec_decode_num_accepted_tokens_total 3433\n"
)


def stream(block=None, ids=(16, 17)):
    """A streamed chat reply: one content chunk per id, then the end chunk and usage.

    vLLM puts each chunk's ids in its choice. TensorFold puts none there and, with
    `return_token_ids`, all of them in the end chunk's block (its cuda/server.py).
    """
    chunks = [
        {"choices": [{"delta": {"content": f"{t}\n"}, "token_ids": [t]}]} for t in ids
    ]
    end = {"choices": [{"delta": {}, "finish_reason": "length"}]}
    if block is not None:
        for c in chunks:
            del c["choices"][0]["token_ids"]
        end["tensorfold"] = dict(block, token_ids=list(ids))
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


class AcceptanceLengthTests(unittest.TestCase):
    def test_tensorfold_reply_blocks_give_one_plus_accepted_over_rounds(self):
        lines = run([stream(TF_BLOCK)] * 3, [TF_METRICS, TF_METRICS])
        summary = lines[-1]["summary"]
        self.assertEqual(summary["acceptance_length"], round(1 + 114 / 78, 3))
        self.assertEqual(summary["acceptance_from"], "tensorfold reply blocks")

    def test_the_t5_needle_reply_matches_its_tokens_per_round(self):
        block = {"rounds": 11, "accepted": 26, "drafted": 33, "tokens_per_round": 3.364}
        self.assertEqual(decode_check.acceptance({}, {}, [block])[0], 3.364)

    def test_tensorfold_without_drafts_is_null_with_a_reason(self):
        block = {"rounds": 511, "accepted": 0, "drafted": 0, "drafts": False}
        length, extra = decode_check.acceptance({}, {}, [block] * 3)
        self.assertIsNone(length)
        self.assertIn("acceptance_null", extra)

    def test_a_sample_without_its_block_is_null_with_a_reason(self):
        length, extra = decode_check.acceptance({}, {}, [TF_BLOCK, None, TF_BLOCK])
        self.assertIsNone(length)
        self.assertIn("acceptance_null", extra)

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
        flat = VLLM_METRICS.format(drafts=0, draft_tokens=0, accepted=0, generated=0)
        summary = run([stream()] * 3, [flat, flat])[-1]["summary"]
        self.assertIsNone(summary["acceptance_length"])
        self.assertNotIn("acceptance_null", summary)


class TensorFoldTokenIdsTests(unittest.TestCase):
    def test_the_ids_come_from_the_block_when_the_choices_carry_none(self):
        ids = [16, 17, 18]
        row = run([stream(TF_BLOCK, ids)] * 3, [TF_METRICS] * 2)[0]
        self.assertEqual(row["n_token_ids"], 3)
        digest = hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:16]
        self.assertEqual(row["token_ids_sha256"], digest)

    def test_decode_divergence_finds_the_first_differing_token_in_tokens_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [str(Path(tmp) / "a.json"), str(Path(tmp) / "b.json")]
            for path, ids in zip(paths, ([16, 17, 18], [16, 99, 18])):
                run([stream(TF_BLOCK, ids)] * 3, [TF_METRICS] * 2, tokens_out=path)
            saved = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
            self.assertEqual(saved["samples"][0]["token_ids"], [16, 17, 18])
            out = io.StringIO()
            with (
                patch.object(decode_divergence.sys, "argv", ["dd", *paths]),
                contextlib.redirect_stdout(out),
                warnings.catch_warnings(),
            ):
                warnings.simplefilter("ignore", ResourceWarning)
                decode_divergence.main()
        first = out.getvalue().splitlines()[0]
        self.assertIn("first differing token 1/3 (ids [17, 18] vs [99, 18])", first)


class TensorFoldPrefixCacheTests(unittest.TestCase):
    def test_each_sample_follows_enough_distinct_requests_to_drop_kept_prompts(self):
        sent, n = [], 3
        with patch.object(decode_check, "TF_GLM_CACHE_ENTRIES", n):
            lines = run([stream(TF_BLOCK)] * 3, [TF_METRICS] * 2, sent)
        summary = lines[-1]["summary"]
        streamed = [i for i, body in enumerate(sent) if body.get("stream")]
        self.assertEqual(streamed, [n, 2 * n + 1, 3 * n + 2])
        fillers = [b["messages"][0]["content"] for b in sent if not b.get("stream")]
        self.assertEqual(len(set(fillers)), 3 * n)
        self.assertEqual(summary["evicted_before_each"], n)

    def test_vllm_sends_only_the_samples(self):
        sent = []
        flat = VLLM_METRICS.format(drafts=0, draft_tokens=0, accepted=0, generated=0)
        run([stream()] * 3, [flat, flat], sent)
        self.assertEqual([b.get("stream") for b in sent], [True] * 3)


if __name__ == "__main__":
    unittest.main()
