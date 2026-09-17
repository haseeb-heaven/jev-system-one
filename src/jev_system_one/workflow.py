from dataclasses import dataclass
from typing import Any

from .jev import DecisionEngine
from .llm import Planner


@dataclass
class WorkflowResult:
    response: dict[str, Any]
    decisions: dict[str, Any]


class Workflow:
    def __init__(self, planner: Planner, jev: DecisionEngine) -> None:
        self.planner = planner
        self.jev = jev

    def run(self, question: str) -> WorkflowResult:
        response = self.planner.answer(question)
        decisions = self.jev.assess(question, response)
        return WorkflowResult(response, decisions)
