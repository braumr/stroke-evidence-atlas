"""OpenAI client wrapper for low-cost structured extraction."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass

from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from .config import DEFAULT_LLM_MODEL

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


class FatalAPIError(RuntimeError):
    """Raised for API failures where continuing would waste money or time."""


class BudgetExceeded(RuntimeError):
    """Raised when the configured extraction cost cap has been reached."""


MODEL_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o-mini": (0.15, 0.60),
}


def _base_model(model: str) -> str:
    for prefix in sorted(MODEL_PRICING_PER_1M, key=len, reverse=True):
        if model.startswith(prefix):
            return prefix
    return model


def _is_fatal_api_error(exc: Exception) -> bool:
    text = str(exc).lower()
    fatal_markers = [
        "credit_balance_exhausted",
        "insufficient_quota",
        "no credits remaining",
        "billing",
        "quota",
    ]
    return any(marker in text for marker in fatal_markers)


@dataclass
class UsageTotals:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class UsageBudget:
    """Thread-safe token/cost tracker for one extraction run."""

    def __init__(self, max_cost_usd: float | None = None) -> None:
        self.max_cost_usd = max_cost_usd
        self._lock = threading.Lock()
        self.totals = UsageTotals()

    def record(self, model: str, prompt_tokens: int, completion_tokens: int) -> UsageTotals:
        input_rate, output_rate = MODEL_PRICING_PER_1M.get(_base_model(model), MODEL_PRICING_PER_1M["gpt-4.1-mini"])
        cost = (prompt_tokens / 1_000_000 * input_rate) + (completion_tokens / 1_000_000 * output_rate)
        with self._lock:
            self.totals.requests += 1
            self.totals.input_tokens += prompt_tokens
            self.totals.output_tokens += completion_tokens
            self.totals.estimated_cost_usd += cost
            snapshot = UsageTotals(
                self.totals.requests,
                self.totals.input_tokens,
                self.totals.output_tokens,
                self.totals.estimated_cost_usd,
            )
        if self.max_cost_usd is not None and snapshot.estimated_cost_usd >= self.max_cost_usd:
            raise BudgetExceeded(
                f"Estimated API cost ${snapshot.estimated_cost_usd:.2f} reached cap ${self.max_cost_usd:.2f}"
            )
        return snapshot


_USAGE_BUDGET = UsageBudget()


def configure_usage_budget(max_cost_usd: float | None = None) -> None:
    global _USAGE_BUDGET
    _USAGE_BUDGET = UsageBudget(max_cost_usd=max_cost_usd)


def usage_totals() -> UsageTotals:
    return _USAGE_BUDGET.totals


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

            self.client = OpenAI(timeout=120, max_retries=0)
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install dependencies with `pip install -r requirements.txt` before extraction.") from exc
        except Exception as exc:
            raise RuntimeError("Could not initialize the OpenAI client. Check your OpenAI API key.") from exc

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(2),
        retry=retry_if_not_exception_type((FatalAPIError, BudgetExceeded)),
        reraise=True,
    )
    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        """Return JSON text from the configured model."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            if _is_fatal_api_error(exc):
                raise FatalAPIError(str(exc)) from exc
            raise
        if response.usage:
            _USAGE_BUDGET.record(
                self.model,
                response.usage.prompt_tokens or 0,
                response.usage.completion_tokens or 0,
            )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")
        return content
