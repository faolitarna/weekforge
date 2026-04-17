"""LLM call cost + run-level accumulator.

Each agent call produces a `CallMetadata`; a workflow accumulates them into a
`RunCost` and renders the total at completion.

Field names track Pydantic AI's `RunUsage` (`input_tokens` / `output_tokens`),
so values can be forwarded without translation.
"""
from dataclasses import dataclass

from pydantic import BaseModel


class CallMetadata(BaseModel, frozen=True):
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model_used: str
    cost_eur: float = 0.0


@dataclass
class RunCost:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    call_count: int = 0
    total_latency_ms: int = 0
    total_cost_eur: float = 0.0

    def add(self, meta: CallMetadata) -> None:
        self.total_input_tokens += meta.input_tokens
        self.total_output_tokens += meta.output_tokens
        self.call_count += 1
        self.total_latency_ms += meta.latency_ms
        self.total_cost_eur += meta.cost_eur

    def summary(self) -> str:
        """Rich-markup line. Callers compose into whichever Panel they render."""
        latency_s = self.total_latency_ms / 1000
        cost = f"€ {self.total_cost_eur:.4f}" if self.total_cost_eur else "€ —"
        return (
            f"[bold]Tokens:[/bold] {self.total_input_tokens} in / "
            f"{self.total_output_tokens} out  "
            f"[bold]Latency:[/bold] {latency_s:.2f}s  "
            f"[bold]Calls:[/bold] {self.call_count}  "
            f"[bold]Cost:[/bold] {cost}"
        )
