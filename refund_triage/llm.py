"""Thin wrapper around the Anthropic SDK that tracks tokens, latency and cost."""
import time
from dataclasses import dataclass, field

from .config import EFFORT, MAX_TOKENS, MODEL, PRICES


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0   # includes thinking tokens, which are billed as output
    calls: int = 0
    seconds: float = 0.0

    def cost_usd(self, model: str) -> float:
        p_in, p_out = PRICES[model]
        return (self.input_tokens * p_in + self.output_tokens * p_out) / 1_000_000

    def as_dict(self, model: str) -> dict:
        return {
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "llm_calls": self.calls, "llm_seconds": round(self.seconds, 3),
            "cost_usd": round(self.cost_usd(model), 6),
        }


class LLM:
    def __init__(self, model: str = MODEL, client=None):
        self.model = model
        self._client = client
        self.usage = Usage()

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()  # credentials from ANTHROPIC_API_KEY or `ant auth login`
        return self._client

    def create(self, **kwargs):
        kwargs.setdefault("max_tokens", MAX_TOKENS)
        kwargs.setdefault("output_config", {"effort": EFFORT})
        t0 = time.perf_counter()
        resp = self.client.messages.create(model=self.model, **kwargs)
        self.usage.seconds += time.perf_counter() - t0
        self.usage.calls += 1
        self.usage.input_tokens += resp.usage.input_tokens
        self.usage.output_tokens += resp.usage.output_tokens
        return resp
