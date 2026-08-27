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
    tokens: int = 0                      # candidate_tokens, always set regardless of the branch taken


def _framed_summary(summary: str) -> dict:
    return {"role": "system", "content": _SUMMARY_FRAME.format(summary=summary)}


def _as_chat_message(m: dict) -> dict:
    return {"role": m["role"], "content": m["content"]}


def build_history(prior_summary: str | None, tail: list[dict]) -> list[dict]:
    return ([_framed_summary(prior_summary)] if prior_summary else []) + [_as_chat_message(m) for m in tail]


def fetch_budget_inputs(users, user_id: uuid.UUID, conversation_id: uuid.UUID) -> tuple[str | None, list[dict]]:
    """Fetch (prior_summary, tail) for context-budget bookkeeping for a given
    conversation. Decoupled from ExecutionRequest so RequestHandler, the
    streaming persist path, and conversation-scoped API routes can all share
    this without duplicating it. Ownership is checked explicitly and first —
    get_conversation_context_state does not check it on its own."""
    users.assert_conversation_owner(user_id, conversation_id)
    state = users.get_conversation_context_state(conversation_id)
    ctx = state.get("context_summary")
    prior_summary = ctx["summary"] if ctx else None
    boundary_created_at = ctx["boundary_created_at"] if ctx else None
    boundary_rowid = ctx["boundary_rowid"] if ctx else None
    tail = users.get_messages_after_boundary(
        user_id, conversation_id, boundary_created_at, boundary_rowid
    )
    return prior_summary, tail


def check_context_budget(
    prior_summary: str | None, tail: list[dict], settings, generator, *, force: bool = False,
) -> BudgetCheck:
    """Cheap, synchronous, no I/O. Decides whether the given tail (plus any
    prior summary) fits the configured budget, and if not, how to split it
    into a fold (oldest, to be summarized) / keep (newest, kept verbatim).

    `generator` is the active generation connection's Generator, carrying its
    own compaction_enabled/compaction_context_window/compaction_summary_length
    (falling back to the global settings.max_context_tokens/summary_target_tokens
    when unset). Token counts are always computed regardless of
    compaction_enabled, since usage-display endpoints need them too — only
    needs_compaction itself is gated on the toggle.

    force=True skips both the enabled check and the budget check, and always
    folds down to MIN_KEEP_MESSAGES (via _split_force_fold) as long as
    there's anything productive to fold — used for user-initiated manual
    compaction, which should always do real work when clicked (regardless of
    whether auto-compaction is enabled for this connection), not only when
    the auto-trigger budget is exceeded.

    Concurrency note: this function and update_conversation_context_summary
    are not used atomically as a pair — two overlapping requests for the same
    conversation could both decide compaction is needed and race on the final
    metadata write. This is accepted as a benign limitation for now: the
    messages table itself is never mutated by this logic (only read), so the
    worst case is a redundant summarization call and one of two boundary
    updates being discarded — self-healing on the next turn.
    """
    candidate = build_history(prior_summary, tail)
    context_window = generator.compaction_context_window or settings.max_context_tokens
    summary_target = generator.compaction_summary_length or settings.summary_target_tokens
    effective_budget = int(context_window * SAFETY_MARGIN)
    candidate_tokens = count_message_tokens(candidate)
    _log.debug("context_budget_check", extra={
        "tail_len": len(tail),
        "has_prior_summary": prior_summary is not None,
        "prior_summary_tokens": count_tokens(prior_summary) if prior_summary else 0,
        "candidate_tokens": candidate_tokens,
        "effective_budget": effective_budget,
        "compaction_enabled": generator.compaction_enabled,
        "force": force,
    })

    if not tail:
        return BudgetCheck(history=candidate, needs_compaction=False, tokens=candidate_tokens)
    if not force and (not generator.compaction_enabled or candidate_tokens <= effective_budget):
        return BudgetCheck(history=candidate, needs_compaction=False, tokens=candidate_tokens)

    if force:
        fold, keep = _split_force_fold(tail)
    else:
        keep_budget = max(effective_budget - summary_target - RESERVE_FOR_NEW_TURN, 0)
        fold, keep = _split_oldest_to_fold(tail, keep_budget, effective_budget)
    if not fold:
        # Nothing productive to fold (e.g. a single message alone exceeds
        # budget, or the tail is too short) — compaction can't help here.
        # Pass through rather than calling run_compaction with an empty fold.
        _log.debug("context_budget_cannot_fold", extra={"tail_len": len(tail), "force": force})
        return BudgetCheck(history=candidate, needs_compaction=False, tokens=candidate_tokens)

    _log.info("context_budget_compaction_needed", extra={
        "tail_len": len(tail), "fold_len": len(fold), "keep_len": len(keep),
        "candidate_tokens": candidate_tokens, "effective_budget": effective_budget, "force": force,
    })
    return BudgetCheck(needs_compaction=True, fold=fold, keep=keep, tokens=candidate_tokens)


def _split_oldest_to_fold(
    tail: list[dict], keep_budget: int, effective_budget: int
) -> tuple[list[dict], list[dict]]:
    """Walk the tail backwards from the newest message, accumulating tokens,
    until the next-older message would exceed keep_budget. Snap the cut to a
    'user' role boundary so the kept tail never starts mid-exchange with an
    orphaned assistant reply. Always folds at least one message (forward
    progress) if the tail has more than one message and is over budget at all.

    Tries to keep at least MIN_KEEP_MESSAGES messages regardless of the
    token-budget walk above -- recency takes priority over strict budget
    adherence for normal-sized messages. But this floor never pulls in a
    message that alone exceeds effective_budget (e.g. a giant RAG-augmented
    prompt or a large pasted block): such a message can never coexist with a
    summary + new turn no matter how recent it is, so protecting it here
    would just guarantee compaction re-triggers on every subsequent turn
    without ever making progress.
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

    floor_cut = max(0, n - MIN_KEEP_MESSAGES)
    while cut > floor_cut:
        next_msg_tokens = count_message_tokens([_as_chat_message(tail[cut - 1])])
        if next_msg_tokens > effective_budget:
            break
        cut -= 1

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


def _split_force_fold(tail: list[dict]) -> tuple[list[dict], list[dict]]:
    """Fold everything except the most recent MIN_KEEP_MESSAGES, regardless of
    token budget -- used for user-initiated manual compaction, which should
    always do real work when clicked rather than only when the auto-trigger
    budget is exceeded."""
    n = len(tail)
    cut = max(0, n - MIN_KEEP_MESSAGES)
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
    target_tokens = generator.compaction_summary_length or settings.summary_target_tokens
    turns_text = "\n".join(f"{m['role']}: {m['content']}" for m in fold)
    prompt = _SUMMARIZE_PROMPT.format(
        existing_summary_block=existing_summary_block,
        target_tokens=target_tokens,
        turns=turns_text,
    )
    # 3-tier fallback: this connection's own compaction model override, then
    # the global summary-model preference, then the connection's normal model.
    model = generator.compaction_model or settings.summary_model or generator.default_model
    _log.debug("context_compaction_prompt_built", extra={
        "conversation_id": str(conversation_id), "prompt_tokens": count_tokens(prompt), "model": model,
    })

    # Uses chat(), not generate(): the raw completions endpoint has no chat
    # template, so the model has no reliable turn-ending signal there -- in
    # practice that produced wildly inconsistent summary lengths (as little as
    # 24 tokens, as much as 8000+ on the same prompt shape) and leaked raw
    # <think>...</think> reasoning tags into the persisted summary. A single
    # user-role message is still a stateless, one-shot call, just properly
    # templated. max_tokens is still an explicit safety cap, not a target --
    # 1.5x headroom since summary_target_tokens is a soft ask in the prompt.
    new_summary = await generator.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        options={"temperature": 0.0, "max_tokens": int(target_tokens * 1.5)},
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
