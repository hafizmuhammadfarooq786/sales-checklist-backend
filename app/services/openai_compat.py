"""OpenAI Chat Completions compatibility for GPT-5 / reasoning models."""


def _is_reasoning_model(model: str) -> bool:
    name = model.lower()
    return name.startswith("gpt-5") or name.startswith(("o1", "o3", "o4"))


def chat_completion_kwargs(
    model: str,
    *,
    max_output_tokens: int,
    temperature: float | None = None,
) -> dict:
    """Return token/temperature kwargs appropriate for the model family."""
    if _is_reasoning_model(model):
        return {"max_completion_tokens": max_output_tokens}
    kwargs: dict = {"max_tokens": max_output_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    return kwargs
