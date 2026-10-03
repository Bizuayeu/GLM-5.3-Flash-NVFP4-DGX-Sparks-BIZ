import copy
import hashlib
import json
import unittest
from pathlib import Path

from tools import score_nll_set

SET = Path(__file__).resolve().parents[1] / "config/nll_set.json"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def small_set():
    """Two Japanese texts of 3 and 5 tokens, one code text of 2 (one character a token)."""
    texts = [("ja1", "ja", "abc"), ("ja2", "ja", "abcde"), ("code1", "code", "xy")]
    return {
        "version": 1,
        "max_tokens": 1800,
        "tokenizer": {"sha256": sha("tok")},
        "texts": [
            {"name": n, "domain": d, "text": t, "sha256": sha(t), "tokens": len(t)}
            for n, d, t in texts
        ],
    }


def tokenize(text):
    return [ord(c) for c in text]


def complete_at(logprob_of):
    """A /v1/completions reply in vLLM's prompt_logprobs shape; every prompt token of a
    text at ``logprob_of(token_ids)``."""

    def complete(token_ids, top_k):
        value = logprob_of(token_ids)
        rows = [{str(t): {"logprob": value, "rank": 1}} for t in token_ids[1:]]
        return {"choices": [{"prompt_logprobs": [None, *rows], "text": ""}]}

    return complete


class SetTests(unittest.TestCase):
    def test_the_published_set_matches_its_recorded_hashes(self):
        data = json.loads(SET.read_text(encoding="utf-8"))
        self.assertEqual(score_nll_set.problems(data, None), [])
        domains = [t["domain"] for t in data["texts"]]
        self.assertEqual(
            {d: domains.count(d) for d in domains},
            dict.fromkeys(score_nll_set.DOMAINS, 4),
        )
        self.assertTrue(all(t["tokens"] <= data["max_tokens"] for t in data["texts"]))

    def test_a_different_tokenizer_or_text_is_named(self):
        data = small_set()
        self.assertEqual(score_nll_set.problems(data, b"tok"), [])
        self.assertEqual(
            score_nll_set.problems(data, b"other"),
            ["tokenizer.json differs from the one the set was built with"],
        )
        changed = copy.deepcopy(data)
        changed["texts"][1]["text"] += " "
        self.assertEqual(
            score_nll_set.problems(changed, b"tok"),
            ["text ja2 differs from its recorded sha256"],
        )


class ScoreTests(unittest.TestCase):
    def test_each_domain_is_weighted_by_its_positions(self):
        # ja1: 2 positions at NLL 1, ja2: 4 at NLL 2 -> (2 + 8) / 6; code1: 1 position at 0.5
        summary, result = score_nll_set.score(
            small_set(),
            tokenize,
            complete_at(lambda ids: {3: -1.0, 5: -2.0, 2: -0.5}[len(ids)]),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(summary["ja"]["positions"], 6)
        self.assertEqual(summary["ja"]["mean_nll"], round(10 / 6, 4))
        self.assertEqual(summary["ja"]["texts"], {"ja1": 1.0, "ja2": 2.0})
        self.assertEqual(
            summary["code"], {"mean_nll": 0.5, "positions": 1, "texts": {"code1": 0.5}}
        )
        self.assertNotIn("en", summary)

    def test_a_failed_text_is_left_out_of_its_domain_and_fails_the_run(self):
        def complete(token_ids, top_k):
            if token_ids[0] == ord("x"):
                raise OSError("refused")
            return complete_at(lambda ids: -1.0)(token_ids, top_k)

        summary, result = score_nll_set.score(small_set(), tokenize, complete)
        self.assertFalse(result["passed"])
        self.assertNotIn("code", summary)
        self.assertEqual(summary["ja"]["positions"], 6)


if __name__ == "__main__":
    unittest.main()
