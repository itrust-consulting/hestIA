from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from hestia.domain.chat.tokens import count_message_tokens, count_tokens

_log = logging.getLogger("hestia.system")

# tiktoken/cl100k_base is an approximation of whatever model is actually
# configured, not its exact tokenizer — this margin absorbs that drift rather
# than chasing exactness. See docs in tokens.py.
SAFETY_MARGIN = 0.9
# Tokens reserved for the new user turn + framing overhead not yet known when
# deciding how much of the tail to keep.
RESERVE_FOR_NEW_TURN = 1000
# The most recent messages are never folded away, even if that leaves the
# result over budget -- recency takes priority over strict budget adherence.
MIN_KEEP_MESSAGES = 5

_SUMMARY_FRAME = (
    "The following is a summary of earlier parts of this conversation that are no longer "
    "shown verbatim, to preserve context:\n\n{summary}"
)

_SUMMARIZE_PROMPT = """
You are maintaining a rolling summary of an ongoing conversation between a user and an
assistant, so that older turns can be dropped from the raw context without losing information
the assistant may need later.

{existing_summary_block}

Summarize the following additional conversation turns and merge them into a single updated
summary. Requirements:
- Preserve concrete facts, decisions, names, numbers, constraints, and open questions.
- Do NOT add commentary, opinions, or anything not present in the source material.
- Be concise: target roughly {target_tokens} tokens or fewer.
- Write the summary in plain prose (no meta-commentary like "the user asked..." framing unless
  needed for clarity of who said what).

<conversation-turns-to-fold-in>
{turns}
</conversation-turns-to-fold-in>
""".strip()


@dataclass
class BudgetCheck:
    history: list[dict] | None = None    # set when already under budget — nothing else needed
    needs_compaction: bool = False
    fold: list[dict] | None = None       # oldest messages to fold in, only set if needs_compaction
    keep: list[dict] | None = None       # newest messages to keep verbatim


def _framed_summary(summary: str) -> dict:
    return {"role": "system", "content": _SUMMARY_FRAME.format(summary=summary)}


def _as_chat_message(m: dict) -> dict:
    return {"role": m["role"], "content": m["content"]}


def check_context_budget(prior_summary: str | None, tail: list[dict], settings) -> BudgetCheck:
    """Cheap, synchronous, no I/O. Decides whether the given tail (plus any
    prior summary) fits the configured budget, and if not, how to split it
    into a fold (oldest, to be summarized) / keep (newest, kept verbatim).

    Concurrency note: this function and update_conversation_context_summary
    are not used atomically as a pair — two overlapping requests for the same
    conversation could both decide compaction is needed and race on the final
    metadata write. This is accepted as a benign limitation for now: the
    messages table itself is never mutated by this logic (only read), so the
    worst case is a redundant summarization call and one of two boundary
    updates being discarded — self-healing on the next turn.
    """
    candidate = ([_framed_summary(prior_summary)] if prior_summary else []) + [
        _as_chat_message(m) for m in tail
    ]
    effective_budget = int(settings.max_context_tokens * SAFETY_MARGIN)
    candidate_tokens = count_message_tokens(candidate)
    _log.debug("context_budget_check", extra={
        "tail_len": len(tail),
        "has_prior_summary": prior_summary is not None,
        "candidate_tokens": candidate_tokens,
        "effective_budget": effective_budget,
    })

    if not tail or candidate_tokens <= effective_budget:
        return BudgetCheck(history=candidate, needs_compaction=False)

    keep_budget = max(effective_budget - settings.summary_target_tokens - RESERVE_FOR_NEW_TURN, 0)
    fold, keep = _split_oldest_to_fold(tail, keep_budget)
    if not fold:
        # Nothing productive to fold (e.g. a single message alone exceeds
        # budget) — compaction can't help here. Pass through rather than
        # calling run_compaction with an empty fold.
        _log.debug("context_budget_cannot_fold", extra={"tail_len": len(tail), "keep_budget": keep_budget})
        return BudgetCheck(history=candidate, needs_compaction=False)

    _log.info("context_budget_compaction_needed", extra={
        "tail_len": len(tail), "fold_len": len(fold), "keep_len": len(keep),
        "candidate_tokens": candidate_tokens, "effective_budget": effective_budget,
    })
    return BudgetCheck(needs_compaction=True, fold=fold, keep=keep)


def _split_oldest_to_fold(tail: list[dict], keep_budget: int) -> tuple[list[dict], list[dict]]:
    """Walk the tail backwards from the newest message, accumulating tokens,
    until the next-older message would exceed keep_budget. Snap the cut to a
    'user' role boundary so the kept tail never starts mid-exchange with an
    orphaned assistant reply. Always folds at least one message (forward
    progress) if the tail has more than one message and is over budget at all.
    Never lets the token-budget calculation alone fold away the most recent
    MIN_KEEP_MESSAGES messages -- recency takes priority over strict budget
    adherence. This floor applies before the forced-progress/user-boundary
    steps below, so it never blocks folding at least one message when the
    tail itself is smaller than the floor (e.g. shrinking an oversized prior
    summary), nor does it block the user-boundary snap from running past it
    when there's no user-role message within the floor to land on.
    """
    n = len(tail)
    running = 0
    cut = n  # index into tail where "keep" starts; tail[:cut] gets folded
    for i in range(n - 1, -1, -1):
        msg_tokens = count_message_tokens([_as_chat_message(tail[i])])
        if running + msg_tokens > keep_budget and i != n - 1:
            break
        running += msg_tokens
        cut = i

    cut = min(cut, max(0, n - MIN_KEEP_MESSAGES))

    if cut == 0 and n > 1:
        # guarantee forward progress: never fold nothing when we got here
        # because we were over budget in the first place. Applied BEFORE the
        # user-boundary snap below, so the snap always has final say on where
        # "keep" actually starts.
        cut = 1

    # snap forward to the next 'user' message so keep never starts with an
    # orphaned assistant reply
    while cut < n and tail[cut]["role"] != "user":
        cut += 1

    return tail[:cut], tail[cut:]


async def run_compaction(
    generator,
    settings,
    users,
    conversation_id: uuid.UUID,
    prior_summary: str | None,
    fold: list[dict],
    keep: list[dict],
) -> list[dict]:
    """Runs the (slow) summarization LLM call and persists the new summary +
    boundary. Returns the final history to use for this turn."""
    _log.info("context_compaction_start", extra={
        "conversation_id": str(conversation_id),
        "fold_len": len(fold), "keep_len": len(keep),
        "has_prior_summary": prior_summary is not None,
    })

    existing_summary_block = (
        f"An existing summary already covers everything before this point:\n\n{prior_summary}\n\n"
        "Merge it with the new turns below into one updated summary — do not summarize from scratch."
        if prior_summary
        else "No summary exists yet — this is the first summarization for this conversation."
    )
    turns_text = "\n".join(f"{m['role']}: {m['content']}" for m in fold)
    prompt = _SUMMARIZE_PROMPT.format(
        existing_summary_block=existing_summary_block,
        target_tokens=settings.summary_target_tokens,
        turns=turns_text,
    )
    model = settings.summary_model or settings.default_gen_model
    _log.debug("context_compaction_prompt_built", extra={
        "conversation_id": str(conversation_id), "prompt_tokens": count_tokens(prompt), "model": model,
    })

    # /v1/completions defaults max_tokens to a tiny value (16) when unset, unlike
    # the chat endpoint — without this, the summary gets cut off after one sentence
    # regardless of summary_target_tokens. 1.5x headroom since the target is a soft
    # ask in the prompt, not a hard clip point.
    new_summary = await generator.generate(
        prompt=prompt,
        model=model,
        options={"temperature": 0.0, "max_tokens": int(settings.summary_target_tokens * 1.5)},
        stream=False,
    )

    last_folded = fold[-1]
    users.update_conversation_context_summary(
        conversation_id,
        summary=new_summary,
        boundary_created_at=last_folded["created_at"],
        boundary_rowid=last_folded["rowid"],
    )

    _log.info("context_compaction_done", extra={
        "conversation_id": str(conversation_id),
        "summary_tokens": count_tokens(new_summary),
        "boundary_created_at": last_folded["created_at"],
        "boundary_rowid": last_folded["rowid"],
    })
    return [_framed_summary(new_summary)] + [_as_chat_message(m) for m in keep]
