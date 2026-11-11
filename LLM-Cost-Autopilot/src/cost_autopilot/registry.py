"""Model registry with real per-token pricing (USD per 1M tokens)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model_id: str
    cost_in_per_m: float      # USD per 1M input tokens
    cost_out_per_m: float     # USD per 1M output tokens
    avg_latency_s: float
    quality_tier: str         # high | medium | low


REGISTRY: dict[str, ModelConfig] = {
    "gpt-4o": ModelConfig("openai", "gpt-4o", 2.50, 10.00, 1.8, "high"),
    "gpt-4o-mini": ModelConfig("openai", "gpt-4o-mini", 0.15, 0.60, 0.9, "medium"),
    "claude-sonnet": ModelConfig("anthropic", "claude-sonnet-4-20250514", 3.00, 15.00, 1.9, "high"),
    "claude-haiku": ModelConfig("anthropic", "claude-haiku-4-5-20251001", 1.00, 5.00, 0.7, "medium"),
    "llama-3-8b": ModelConfig("ollama", "llama3:8b", 0.0, 0.0, 1.2, "low"),
}


def cost_of(model_key: str, input_tokens: int, output_tokens: int) -> float:
    config = REGISTRY[model_key]
    return (input_tokens * config.cost_in_per_m
            + output_tokens * config.cost_out_per_m) / 1_000_000
