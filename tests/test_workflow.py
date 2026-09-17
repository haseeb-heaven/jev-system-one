from jev_system_one.workflow import Workflow


class FakeJev:
    def __init__(self) -> None:
        self.routing = {"model": "jev", "answers": {"response_mode": {"choice": "factual"}}}
        self.review_result = {"model": "jev", "answers": {"answer_quality": {"score": 3}}}
        self.calls: list[tuple] = []

    def decide(self, question: str):
        self.calls.append(("decide", question))
        return self.routing

    def review(self, question: str, draft: dict, routing: dict):
        self.calls.append(("review", question, draft, routing))
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

    def draft(self, question: str, routing: dict, routing_policy: dict):
        self.calls.append(("draft", question, routing, routing_policy))
        return {"answer": "draft"}

    def finalize(
        self,
        question: str,
        routing: dict,
        routing_policy: dict,
        draft: dict,
        review: dict,
        review_policy: dict,
    ):
        self.calls.append(
            ("finalize", question, routing, routing_policy, draft, review, review_policy)
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
        ("decide", "question"),
        ("review", "question", {"answer": "draft"}, jev.routing),
    ]
    assert planner.calls == [
        ("draft", "question", jev.routing, {"response_mode": "factual"}),
        (
            "finalize",
            "question",
            jev.routing,
            {"response_mode": "factual"},
            {"answer": "draft"},
            jev.review_result,
            {"revision_required": False},
        ),
    ]
    assert [step for step, _ in progress] == [0, 1, 2, 3, 4]
