from jev_system_one.workflow import Workflow


class FakeJev:
    def __init__(self) -> None:
        self.routing = {"model": "jev", "answers": {"response_mode": {"choice": "factual"}}}
        self.review_result = {"model": "jev", "answers": {"answer_quality": {"score": 3}}}
        self.calls: list[tuple] = []

    def decide(self, question: str, history: list[dict] | None = None):
        self.calls.append(("decide", question, history))
        return self.routing

    def review(
        self,
        question: str,
        draft: dict,
        routing: dict,
        history: list[dict] | None = None,
    ):
        self.calls.append(("review", question, draft, routing, history))
        return self.review_result

    def routing_policy(self, decision: dict):
        assert decision == self.routing
        return {"response_mode": "factual"}

    def review_policy(self, decision: dict):
        assert decision == self.review_result
        return {"revision_required": False}


class FakePlanner:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def resolve_clarification(
        self,
        question: str,
        routing: dict,
        routing_policy: dict,
        history: list[dict] | None = None,
    ):
        self.calls.append(("resolve_clarification", question, routing, routing_policy, history))
        return {"assumptions": ["Assumed standard context."]}

    def draft(
        self,
        question: str,
        routing: dict,
        routing_policy: dict,
        clarifications: dict | None = None,
        history: list[dict] | None = None,
    ):
        self.calls.append(("draft", question, routing, routing_policy, clarifications, history))
        return {"answer": "draft"}

    def revise(
        self,
        question: str,
        routing: dict,
        routing_policy: dict,
        draft: dict,
        review: dict,
        review_policy: dict,
        history: list[dict] | None = None,
    ):
        self.calls.append(
            (
                "revise",
                question,
                routing,
                routing_policy,
                draft,
                review,
                review_policy,
                history,
            )
        )
        return {"answer": "revised draft"}

    def finalize(
        self,
        question: str,
        routing: dict,
        routing_policy: dict,
        draft: dict,
        review: dict,
        review_policy: dict,
        history: list[dict] | None = None,
    ):
        self.calls.append(
            (
                "finalize",
                question,
                routing,
                routing_policy,
                draft,
                review,
                review_policy,
                history,
            )
        )
        return {"answer": "final"}


def test_jev_controls_the_openai_pipeline():
    jev = FakeJev()
    planner = FakePlanner()
    progress: list[tuple[int, str]] = []

    result = Workflow(planner, jev).run(
        "question",
        on_progress=lambda step, message: progress.append((step, message)),
    )

    assert result.response == {"answer": "final"}
    assert result.decisions == {"routing": jev.routing, "review": jev.review_result}
    assert jev.calls == [
        ("decide", "question", []),
        ("review", "question", {"answer": "draft"}, jev.routing, []),
    ]
    assert planner.calls == [
        ("draft", "question", jev.routing, {"response_mode": "factual"}, None, []),
        (
            "finalize",
            "question",
            jev.routing,
            {"response_mode": "factual"},
            {"answer": "draft"},
            jev.review_result,
            {"revision_required": False},
            [],
        ),
    ]
    assert [step for step, _ in progress] == [0, 1, 2, 3, 4]


def test_workflow_supports_conversation_history_for_follow_ups():
    jev = FakeJev()
    planner = FakePlanner()
    history = [{"question": "What is Python?", "answer": "A programming language."}]

    result = Workflow(planner, jev).run("Can you show a hello world in it?", history=history)

    assert result.response == {"answer": "final"}
    assert jev.calls[0] == ("decide", "Can you show a hello world in it?", history)
    assert jev.calls[1] == (
        "review",
        "Can you show a hello world in it?",
        {"answer": "draft"},
        jev.routing,
        history,
    )
    assert planner.calls[0] == (
        "draft",
        "Can you show a hello world in it?",
        jev.routing,
        {"response_mode": "factual"},
        None,
        history,
    )
    assert planner.calls[1] == (
        "finalize",
        "Can you show a hello world in it?",
        jev.routing,
        {"response_mode": "factual"},
        {"answer": "draft"},
        jev.review_result,
        {"revision_required": False},
        history,
    )


def test_workflow_autonomous_clarification_without_interrupting_user():
    jev = FakeJev()
    planner = FakePlanner()
    jev.routing_policy = lambda d: {"response_mode": "clarify", "clarification_required": True}

    result = Workflow(planner, jev).run("Ambiguous prompt")

    assert result.response == {"answer": "final"}
    # Verify LangGraph routed through openai_resolve_clarification autonomously
    call_names = [call[0] for call in planner.calls]
    assert "resolve_clarification" in call_names
    assert call_names == ["resolve_clarification", "draft", "finalize"]


def test_workflow_autonomous_revision_loop():
    jev = FakeJev()
    planner = FakePlanner()
    # First review requires revision, second review passes
    reviews = [{"revision_required": True}, {"revision_required": False}]
    jev.review_policy = lambda d: reviews.pop(0)

    result = Workflow(planner, jev).run("Test prompt")

    assert result.response == {"answer": "final"}
    call_names = [call[0] for call in planner.calls]
    assert call_names == ["draft", "revise", "finalize"]
