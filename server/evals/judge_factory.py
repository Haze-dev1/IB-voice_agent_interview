"""Judge LLM for the eval harness.

The harness defaults to a local Ollama judge. This machine has no Ollama, so
scenarios point `judge.eval` here and reuse the bot's Groq key instead of
pulling a ~7.6 GB local model.
"""

import os

from pipecat.services.groq.llm import GroqLLMService


def judge(config: dict) -> GroqLLMService:
    """Build the judge LLM from a scenario's `judge.eval` mapping.

    Args:
        config: The `eval` mapping from the scenario, carrying `model`.

    Returns:
        A Groq service; Groq is OpenAI-compatible, which the judge requires.
    """
    return GroqLLMService(
        api_key=os.environ["GROQ_API_KEY"],
        # reasoning_effort is load-bearing: omit it and gpt-oss-120b spends its
        # whole budget on reasoning tokens, handing the judge empty content.
        # Groq accepts only low/medium/high here — "none" is a 400.
        settings=GroqLLMService.Settings(
            model=config.get("model", "openai/gpt-oss-120b"),
            reasoning_effort="low",
        ),
    )
