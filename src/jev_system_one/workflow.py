from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .jev import DecisionEngine
from .llm import Planner

ProgressCallback = Callable[[int, str], None]
MAX_REVISIONS = 2


class WorkflowState(TypedDict, total=False):
    question: str
    history: list[dict[str, Any]]
    routing: dict[str, Any]
    routing_policy: dict[str, Any]
    clarifications: dict[str, Any] | None
    draft: dict[str, Any]
    review: dict[str, Any]
    review_policy: dict[str, Any]
    revision_count: int
    response: dict[str, Any]


@dataclass
class WorkflowResult:
    response: dict[str, Any]
    decisions: dict[str, Any]


class Workflow:
    def __init__(self, planner: Planner, jev: DecisionEngine) -> None:
        self.planner = planner
        self.jev = jev
        self._on_progress: ProgressCallback | None = None
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(WorkflowState)

        graph.add_node("jev_route", self._node_jev_route)
        graph.add_node("openai_resolve_clarification", self._node_openai_resolve_clarification)
        graph.add_node("openai_draft", self._node_openai_draft)
        graph.add_node("jev_review", self._node_jev_review)
        graph.add_node("openai_revise", self._node_openai_revise)
        graph.add_node("openai_finalize", self._node_openai_finalize)

        graph.add_edge(START, "jev_route")
        graph.add_conditional_edges(
            "jev_route",
            self._route_after_jev,
            {
                "resolve": "openai_resolve_clarification",
                "draft": "openai_draft",
            },
        )
        graph.add_edge("openai_resolve_clarification", "openai_draft")
        graph.add_edge("openai_draft", "jev_review")
        graph.add_conditional_edges(
            "jev_review",
            self._route_after_review,
            {
                "revise": "openai_revise",
                "finalize": "openai_finalize",
            },
        )
        graph.add_edge("openai_revise", "jev_review")
        graph.add_edge("openai_finalize", END)

        return graph.compile()

    def run(
        self,
        question: str,
        history: list[dict[str, Any]] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> WorkflowResult:
        self._on_progress = on_progress
        initial_state: WorkflowState = {
            "question": question,
            "history": history or [],
            "revision_count": 0,
            "clarifications": None,
        }
        final_state = self._graph.invoke(initial_state)
        self._progress(4, "Complete")
        return WorkflowResult(
            response=final_state["response"],
            decisions={
                "routing": final_state.get("routing", {}),
                "review": final_state.get("review", {}),
            },
        )

    def _node_jev_route(self, state: WorkflowState) -> dict[str, Any]:
        self._progress(0, "Jev is deciding the response policy…")
        routing = self.jev.decide(state["question"], history=state.get("history"))
        routing_policy = self.jev.routing_policy(routing)
        return {"routing": routing, "routing_policy": routing_policy}

    def _route_after_jev(self, state: WorkflowState) -> str:
        policy = state.get("routing_policy", {})
        if policy.get("clarification_required") or policy.get("response_mode") == "clarify":
            return "resolve"
        return "draft"

    def _node_openai_resolve_clarification(self, state: WorkflowState) -> dict[str, Any]:
        self._progress(1, "OpenAI is resolving clarification autonomously…")
        clarifications = self.planner.resolve_clarification(
            state["question"],
            state["routing"],
            state["routing_policy"],
            history=state.get("history"),
        )
        return {"clarifications": clarifications}

    def _node_openai_draft(self, state: WorkflowState) -> dict[str, Any]:
        self._progress(1, "OpenAI is drafting from Jev's decision…")
        draft = self.planner.draft(
            state["question"],
            state["routing"],
            state["routing_policy"],
            clarifications=state.get("clarifications"),
            history=state.get("history"),
        )
        return {"draft": draft}

    def _node_jev_review(self, state: WorkflowState) -> dict[str, Any]:
        self._progress(2, "Jev is reviewing and scoring the draft…")
        review = self.jev.review(
            state["question"],
            state["draft"],
            state["routing"],
            history=state.get("history"),
        )
        review_policy = self.jev.review_policy(review)
        return {"review": review, "review_policy": review_policy}

    def _route_after_review(self, state: WorkflowState) -> str:
        policy = state.get("review_policy", {})
        count = state.get("revision_count", 0)
        if policy.get("revision_required") and count < MAX_REVISIONS:
            return "revise"
        return "finalize"

    def _node_openai_revise(self, state: WorkflowState) -> dict[str, Any]:
        count = state.get("revision_count", 0) + 1
        self._progress(2, f"OpenAI is revising draft per Jev review (iteration {count})…")
        revised = self.planner.revise(
            state["question"],
            state["routing"],
            state["routing_policy"],
            state["draft"],
            state["review"],
            state["review_policy"],
            history=state.get("history"),
        )
        return {"draft": revised, "revision_count": count}

    def _node_openai_finalize(self, state: WorkflowState) -> dict[str, Any]:
        self._progress(3, "OpenAI is finalizing from Jev's review…")
        response = self.planner.finalize(
            state["question"],
            state["routing"],
            state["routing_policy"],
            state["draft"],
            state["review"],
            state["review_policy"],
            history=state.get("history"),
        )
        return {"response": response}

    def _progress(self, step: int, message: str) -> None:
        if self._on_progress:
            self._on_progress(step, message)
