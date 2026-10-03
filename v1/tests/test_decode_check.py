import contextlib
import io
import json
import unittest
from unittest.mock import patch

from tools import decode_check

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


def stream(block=None):
    """A streamed chat reply: two content chunks, then the end chunk and usage."""
    chunks = [
        {"choices": [{"delta": {"content": "1\n"}, "token_ids": [16]}]},
        {"choices": [{"delta": {"content": "2\n"}, "token_ids": [17]}]},
        {"choices": [{"delta": {}, "finish_reason": "length"}]},
        {"choices": [], "usage": {"prompt_tokens": 2066, "completion_tokens": 2}},
    ]
    if block is not None:
        chunks[2]["tensorfold"] = block
    return [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [b"data: [DONE]\n"]


class Reply(list):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"".join(self)


def run(replies, metrics):
    """Run main() against canned replies; return its printed JSON lines."""
    replies, metrics = iter(replies), iter(metrics)

    def urlopen(req, timeout=None):
        if isinstance(req, str):
            return Reply([next(metrics).encode()])
        return Reply(next(replies))

    out = io.StringIO()
    clock = iter(range(1000))
    with (
        patch.object(decode_check.urllib.request, "urlopen", urlopen),
        patch.object(decode_check.time, "monotonic", lambda: next(clock)),
        patch.object(decode_check, "SAMPLES", 3),
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


if __name__ == "__main__":
    unittest.main()
