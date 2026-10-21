"""OpenAI Chat Completions compatibility for GPT-5 / reasoning models."""

# Headroom added on top of the caller's requested answer size when the model is a
# reasoning model.
#
# Why this exists: `max_tokens` on a classic model caps the ANSWER, but
# `max_completion_tokens` on a reasoning model caps reasoning AND answer
# together, and reasoning runs first. A budget sized for the answer alone is
# therefore spent entirely on thinking, and the API returns 200 OK with empty
# content — no error, nothing in the logs, just a silently blank answer.
#
# Measured against gpt-5 with ~7k characters of retrieved context: a routine
# question spends 200-500 reasoning tokens, while a multi-part analytical one
# spends 3,100+ and was observed consuming budgets of 900, 1400 and 2500 in full
# without emitting a single visible token. The headroom covers that worst case with
# margin, since reasoning cost varies with question difficulty rather than context size.
#
# These are ceilings, not spend: a short answer still costs only what it uses.
REASONING_HEADROOM_TOKENS = 4000
MIN_REASONING_BUDGET = 5000


def _is_reasoning_model(model: str) -> bool:
    name = model.lower()
    return name.startswith("gpt-5") or name.startswith(("o1", "o3", "o4"))


def reasoning_budget(max_output_tokens: int) -> int:
    """Total budget a reasoning model needs to return `max_output_tokens` of text."""
    return max(max_output_tokens + REASONING_HEADROOM_TOKENS, MIN_REASONING_BUDGET)


def chat_completion_kwargs(
    model: str,
    *,
    max_output_tokens: int,
    temperature: float | None = None,
) -> dict:
    """Return token/temperature kwargs appropriate for the model family.

    `max_output_tokens` is what the caller wants to read back. For reasoning
    models the request is widened to cover the thinking that precedes it, so
    call sites can keep expressing the answer length they actually want.
    """
    if _is_reasoning_model(model):
        return {"max_completion_tokens": reasoning_budget(max_output_tokens)}
    kwargs: dict = {"max_tokens": max_output_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    return kwargs
