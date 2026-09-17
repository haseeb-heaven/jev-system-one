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

    def draft(
        self,
        question: str,
        routing: dict,
        routing_policy: dict,
        history: list[dict] | None = None,
    ):
        self.calls.append(("draft", question, routing, routing_policy, history))
        return {"answer": "draft"}

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
        ("decide", "question", None),
        ("review", "question", {"answer": "draft"}, jev.routing, None),
    ]
    assert planner.calls == [
        ("draft", "question", jev.routing, {"response_mode": "factual"}, None),
        (
            "finalize",
            "question",
            jev.routing,
            {"response_mode": "factual"},
            {"answer": "draft"},
            jev.review_result,
            {"revision_required": False},
            None,
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
