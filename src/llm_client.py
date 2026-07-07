"""OpenAI client wrapper for low-cost structured extraction."""

from __future__ import annotations

import os

from tenacity import retry, stop_after_attempt, wait_exponential

from .config import DEFAULT_LLM_MODEL

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


class LLMClient:
    """Small wrapper around the OpenAI chat completions API."""

    def __init__(self, model: str | None = None) -> None:
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not visible to Python. Run "
                "`export OPENAI_API_KEY=\"your_key_here\"` in this terminal, "
                "or create a project-root `.env` file containing `OPENAI_API_KEY=your_key_here`."
            )
        self.model = model or DEFAULT_LLM_MODEL
        try:
            from openai import OpenAI

            self.client = OpenAI()
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install dependencies with `pip install -r requirements.txt` before extraction.") from exc
        except Exception as exc:
            raise RuntimeError("Could not initialize the OpenAI client. Check your OpenAI API key.") from exc

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(4))
    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        """Return JSON text from the configured model."""

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")
        return content
