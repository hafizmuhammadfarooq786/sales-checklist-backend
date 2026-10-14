"""Token budget behaviour for reasoning vs classic models.

The failure these guard against is silent: a reasoning model spends
`max_completion_tokens` on thinking before it writes anything, so a budget sized
for the answer alone returns 200 OK with empty content — no exception, nothing in
the logs, just a blank answer in the product.
"""
import pytest

from app.services.openai_compat import chat_completion_kwargs, reasoning_budget

REASONING_MODELS = ["gpt-5", "gpt-5-mini", "o1", "o1-preview", "o3", "o3-mini", "o4"]
CLASSIC_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]

# Every max_output_tokens value used across the services today.
CALL_SITE_BUDGETS = [600, 700, 900, 1000, 1200, 1400, 2000, 4000, 8000]

# Measured against gpt-5 with ~7k characters of retrieved context: a multi-part
# analytical question spent ~3,136 reasoning tokens before emitting any visible
# text, and budgets of 900, 1400 and 2500 were each consumed in full, returning
# an empty answer. These are deliberately absolute rather than derived from the
# module's own constants — a test that reads those constants would keep passing
# if someone set them back to zero.
OBSERVED_WORST_CASE_REASONING = 3136
MIN_ANSWER_ROOM = 250


@pytest.mark.parametrize("model", CLASSIC_MODELS)
def test_classic_models_cap_the_answer_only(model):
    """Classic models are unaffected: max_tokens caps visible output."""
    assert chat_completion_kwargs(model, max_output_tokens=900, temperature=0.2) == {
        "max_tokens": 900,
        "temperature": 0.2,
    }
    assert chat_completion_kwargs(model, max_output_tokens=900) == {"max_tokens": 900}


@pytest.mark.parametrize("model", REASONING_MODELS)
def test_reasoning_models_use_completion_tokens_without_temperature(model):
    kwargs = chat_completion_kwargs(model, max_output_tokens=900, temperature=0.2)
    assert "max_completion_tokens" in kwargs
    assert "max_tokens" not in kwargs
    # Reasoning models reject temperature.
    assert "temperature" not in kwargs


@pytest.mark.parametrize("asked", CALL_SITE_BUDGETS)
def test_every_call_site_can_absorb_worst_case_reasoning(asked):
    """Every call site must survive the hardest question we measured and still
    have tokens left to write an answer with."""
    budget = chat_completion_kwargs("gpt-5", max_output_tokens=asked)[
        "max_completion_tokens"
    ]
    assert budget >= OBSERVED_WORST_CASE_REASONING + MIN_ANSWER_ROOM


@pytest.mark.parametrize("asked", CALL_SITE_BUDGETS)
def test_headroom_is_added_to_the_request_not_taken_from_it(asked):
    """The caller asks for answer length; reasoning room is added on top."""
    assert reasoning_budget(asked) - asked >= OBSERVED_WORST_CASE_REASONING - asked
    assert reasoning_budget(asked) > asked


def test_budget_never_shrinks_as_the_request_grows():
    budgets = [reasoning_budget(n) for n in range(0, 10_000, 250)]
    assert budgets == sorted(budgets)


def test_large_requests_keep_their_full_answer_allowance():
    """checklist_analyzer asks for 8k of output; the floor must not cap it."""
    assert reasoning_budget(8000) >= 8000 + OBSERVED_WORST_CASE_REASONING
