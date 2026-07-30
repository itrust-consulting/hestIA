from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

from hestia.domain.chat.context_budget import (
    check_context_budget,
    run_compaction,
)


def _run(coro):
    return asyncio.run(coro)


def _settings(max_context_tokens=100, summary_target_tokens=20, summary_model=None, default_gen_model="test-model"):
    s = MagicMock()
    s.max_context_tokens = max_context_tokens
    s.summary_target_tokens = summary_target_tokens
    s.summary_model = summary_model
    s.default_gen_model = default_gen_model
    return s


def _msg(role, content, created_at, rowid):
    return {"role": role, "content": content, "created_at": created_at, "rowid": rowid}


def _big_msg(role, i):
    # ~67 tokens each (see manual check against tiktoken cl100k_base)
    return _msg(role, "word " * 100, i, i)


# ---------------------------------------------------------------------------
# check_context_budget
# ---------------------------------------------------------------------------

class TestCheckContextBudget:

    def test_under_budget_passthrough(self):
        settings = _settings(max_context_tokens=100_000)
        tail = [_msg("user", "hi", 1, 1), _msg("assistant", "hello", 2, 2)]
        check = check_context_budget(None, tail, settings)
        assert check.needs_compaction is False
        assert check.history is not None
        assert check.fold is None
        assert check.keep is None

    def test_empty_tail_never_needs_compaction(self):
        settings = _settings(max_context_tokens=1)
        check = check_context_budget("a huge prior summary " * 500, [], settings)
        assert check.needs_compaction is False

    def test_over_budget_triggers_compaction(self):
        settings = _settings(max_context_tokens=200, summary_target_tokens=20)
        tail = [_big_msg("user" if i % 2 == 0 else "assistant", i) for i in range(10)]
        check = check_context_budget(None, tail, settings)
        assert check.needs_compaction is True
        assert check.fold
        assert check.keep is not None
        # fold + keep must reconstruct the full tail, in order, no gaps/dupes
        assert check.fold + check.keep == tail

    def test_cut_point_never_leaves_keep_starting_with_assistant(self):
        settings = _settings(max_context_tokens=2000, summary_target_tokens=100)
        tail = [_big_msg("user" if i % 2 == 0 else "assistant", i) for i in range(20)]
        check = check_context_budget(None, tail, settings)
        assert check.needs_compaction is True
        assert check.keep  # a real middle cut, not "fold everything"
        assert check.keep[0]["role"] == "user"

    def test_keeps_at_least_min_recent_messages_even_under_tiny_budget(self):
        # Reproduces the production scenario where a tiny effective budget
        # relative to message size folded the *entire* tail (keep_len=0),
        # leaving the model with no verbatim recent messages at all. The
        # MIN_KEEP_MESSAGES floor in _split_oldest_to_fold must keep at least
        # a handful of the newest messages regardless of budget pressure.
        settings = _settings(max_context_tokens=200, summary_target_tokens=20)
        tail = [_big_msg("user" if i % 2 == 0 else "assistant", i) for i in range(30)]
        check = check_context_budget(None, tail, settings)
        assert check.needs_compaction is True
        assert len(check.keep) >= 4
        assert check.fold + check.keep == tail

    def test_single_message_tail_over_budget_passes_through(self):
        # nothing productive to fold when the tail is just one (huge) message —
        # compaction can't help, so this must not crash and must not compact
        settings = _settings(max_context_tokens=10, summary_target_tokens=2)
        tail = [_big_msg("user", 1)]
        check = check_context_budget(None, tail, settings)
        assert check.needs_compaction is False
        assert check.history is not None

    def test_oversized_prior_summary_still_folds_at_least_one_message(self):
        # tail alone fits comfortably, but a bloated prior summary pushes the
        # combined candidate over budget — compaction should still trigger
        # (re-compressing the prior summary) rather than silently passing
        # an over-budget candidate through.
        settings = _settings(max_context_tokens=100, summary_target_tokens=20)
        oversized_summary = "word " * 500
        tail = [_msg("user", "hi", 1, 1), _msg("assistant", "hello", 2, 2)]
        check = check_context_budget(oversized_summary, tail, settings)
        assert check.needs_compaction is True
        assert len(check.fold) >= 1
        assert check.keep[0]["role"] == "user" if check.keep else True


# ---------------------------------------------------------------------------
# run_compaction
# ---------------------------------------------------------------------------

class TestRunCompaction:

    def _users(self):
        return MagicMock()

    def test_no_prior_summary_calls_llm_once_and_persists_boundary(self):
        settings = _settings()
        generator = MagicMock()
        generator.generate = AsyncMock(return_value="a concise summary")
        users = self._users()
        conversation_id = uuid.uuid4()
        fold = [_msg("user", "old q", 1, 10), _msg("assistant", "old a", 2, 11)]
        keep = [_msg("user", "recent q", 3, 12)]

        history = _run(run_compaction(generator, settings, users, conversation_id, None, fold, keep))

        generator.generate.assert_awaited_once()
        users.update_conversation_context_summary.assert_called_once_with(
            conversation_id,
            summary="a concise summary",
            boundary_created_at=2,
            boundary_rowid=11,
        )
        assert history[0]["role"] == "system"
        assert "a concise summary" in history[0]["content"]
        assert history[1:] == [{"role": "user", "content": "recent q"}]

    def test_prior_summary_is_included_in_prompt_as_rolling_update(self):
        settings = _settings()
        generator = MagicMock()
        generator.generate = AsyncMock(return_value="updated summary")
        users = self._users()
        conversation_id = uuid.uuid4()
        fold = [_msg("user", "new turn", 5, 20)]
        keep = []

        _run(run_compaction(generator, settings, users, conversation_id, "PRIOR SUMMARY TEXT", fold, keep))

        prompt = generator.generate.await_args.kwargs["prompt"]
        assert "PRIOR SUMMARY TEXT" in prompt
        assert "do not summarize from scratch" in prompt.lower()

    def test_no_prior_summary_prompt_says_first_summarization(self):
        settings = _settings()
        generator = MagicMock()
        generator.generate = AsyncMock(return_value="summary")
        users = self._users()
        fold = [_msg("user", "hi", 1, 1)]

        _run(run_compaction(generator, settings, users, uuid.uuid4(), None, fold, []))

        prompt = generator.generate.await_args.kwargs["prompt"]
        assert "no summary exists yet" in prompt.lower()

    def test_uses_summary_model_override_when_set(self):
        settings = _settings(summary_model="override-model", default_gen_model="default-model")
        generator = MagicMock()
        generator.generate = AsyncMock(return_value="summary")
        users = self._users()
        fold = [_msg("user", "hi", 1, 1)]

        _run(run_compaction(generator, settings, users, uuid.uuid4(), None, fold, []))

        assert generator.generate.await_args.kwargs["model"] == "override-model"

    def test_falls_back_to_default_gen_model(self):
        settings = _settings(summary_model=None, default_gen_model="default-model")
        generator = MagicMock()
        generator.generate = AsyncMock(return_value="summary")
        users = self._users()
        fold = [_msg("user", "hi", 1, 1)]

        _run(run_compaction(generator, settings, users, uuid.uuid4(), None, fold, []))

        assert generator.generate.await_args.kwargs["model"] == "default-model"


# ---------------------------------------------------------------------------
# Retry idempotency: a retry right after compaction must not re-trigger it
# ---------------------------------------------------------------------------

class TestRetryIdempotency:

    def test_retry_after_compaction_does_not_recompact(self):
        # Budget sized generously relative to MIN_KEEP_MESSAGES: after the
        # first compaction, at least ~5 real messages stay in `keep` by
        # design (see _split_oldest_to_fold), so the budget must have enough
        # headroom for those plus the summary to fit -- otherwise a retry
        # would legitimately need to recompact again, which isn't what this
        # test is checking.
        settings = _settings(max_context_tokens=900, summary_target_tokens=100)

        # Turn 1: tail is over budget, compaction runs and persists a boundary.
        tail = [_big_msg("user" if i % 2 == 0 else "assistant", i) for i in range(10)]
        first_check = check_context_budget(None, tail, settings)
        assert first_check.needs_compaction is True

        generator = MagicMock()
        generator.generate = AsyncMock(return_value="short summary")
        users = MagicMock()
        conversation_id = uuid.uuid4()
        _run(run_compaction(
            generator, settings, users, conversation_id, None, first_check.fold, first_check.keep
        ))
        boundary_call = users.update_conversation_context_summary.call_args
        persisted_boundary_created_at = boundary_call.kwargs["boundary_created_at"]
        persisted_boundary_rowid = boundary_call.kwargs["boundary_rowid"]

        # Retry: the client deletes the turn that triggered compaction (the
        # last message(s) in `keep`, simulating retryMessage's awaited
        # deletes) before resending — so the DB tail the retry sees is
        # whatever's left after the persisted boundary, minus the deleted
        # turn. Model this by simulating the fresh DB read: everything after
        # the boundary that ISN'T the just-deleted trailing turn.
        remaining_after_boundary = [
            m for m in tail
            if (m["created_at"], m["rowid"]) > (persisted_boundary_created_at, persisted_boundary_rowid)
        ]
        deleted = set(id(m) for m in first_check.keep[-2:])  # the retried user+assistant pair
        tail_for_retry = [m for m in remaining_after_boundary if id(m) not in deleted]

        second_check = check_context_budget("short summary", tail_for_retry, settings)

        assert second_check.needs_compaction is False
        generator.generate.assert_awaited_once()  # still only the one call from turn 1
