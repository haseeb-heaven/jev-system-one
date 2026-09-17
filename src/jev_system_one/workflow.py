from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .jev import DecisionEngine
from .llm import Planner

ProgressCallback = Callable[[int, str], None]


@dataclass
class WorkflowResult:
    response: dict[str, Any]
    decisions: dict[str, Any]


class Workflow:
    def __init__(self, planner: Planner, jev: DecisionEngine) -> None:
        self.planner = planner
        self.jev = jev

    def run(
        self,
        question: str,
        on_progress: ProgressCallback | None = None,
    ) -> WorkflowResult:
        self._progress(on_progress, 0, "Jev is deciding the response policy…")
        routing = self.jev.decide(question)
        routing_policy = self.jev.routing_policy(routing)
        self._progress(on_progress, 1, "OpenAI is drafting from Jev's decision…")
        draft = self.planner.draft(question, routing, routing_policy)
        self._progress(on_progress, 2, "Jev is reviewing and scoring the draft…")
        review = self.jev.review(question, draft, routing)
        review_policy = self.jev.review_policy(review)
        self._progress(on_progress, 3, "OpenAI is finalizing from Jev's review…")
        response = self.planner.finalize(
            question,
            routing,
            routing_policy,
            draft,
            review,
            review_policy,
        )
        self._progress(on_progress, 4, "Complete")
        return WorkflowResult(response, {"routing": routing, "review": review})

    @staticmethod
    def _progress(
        callback: ProgressCallback | None,
        step: int,
        message: str,
    ) -> None:
        if callback:
            callback(step, message)
