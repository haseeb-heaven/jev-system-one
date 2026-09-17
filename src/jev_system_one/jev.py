from typing import Any

from typesafe_sdk import Choice, Noul, RetryPolicy, Score, TypeSafeClient


class JevError(RuntimeError):
    pass


class DecisionEngine:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = TypeSafeClient(
            api_key=api_key,
            model=model,
            retry=RetryPolicy(max_retries=3, backoff_max=1.0, timeout=15.0),
            timeout=30.0,
        )

    def assess(self, question: str, answer: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.system_one(
                state={"user_question": question, "openai_response": answer},
                questions={
                    "question_type": Choice(
                        instructions=(
                            "What kind of response does `user_question` primarily require?"
                        ),
                        criteria={
                            "factual": "A factual explanation or direct information.",
                            "instructional": "Steps, guidance, or advice for doing something.",
                            "creative": "Original ideas, writing, or brainstorming.",
                            "opinion": "A recommendation or subjective judgment.",
                            "unclear": "The intended request cannot be determined reliably.",
                        },
                    ),
                    "answers_question": Noul(
                        instructions=(
                            "Does `openai_response.answer` directly answer `user_question`?"
                        ),
                        criteria={
                            "true": (
                                "The response addresses the user's actual request with relevant "
                                "information."
                            ),
                            "false": (
                                "The response is off-topic, evasive, or fails to provide the "
                                "requested information."
                            ),
                        },
                    ),
                    "contains_unsupported_claims": Noul(
                        instructions=(
                            "Does `openai_response.answer` present uncertain or unsupported "
                            "claims as established facts?"
                        ),
                        criteria={
                            "true": (
                                "The response makes specific factual claims without adequate "
                                "basis or without acknowledging uncertainty."
                            ),
                            "false": (
                                "Claims are supported, are common stable knowledge, or "
                                "uncertainty is clearly disclosed."
                            ),
                        },
                    ),
                    "answer_quality": Score(
                        instructions=(
                            "How useful and complete is `openai_response.answer` for "
                            "`user_question`?"
                        ),
                        criteria=[
                            "poor: incorrect, irrelevant, or unusable",
                            "limited: partly useful but missing important information",
                            "good: relevant, clear, and sufficiently complete",
                            "excellent: precise, complete, and immediately useful",
                        ],
                    ),
                },
            )
            return self._response_json(result)
        except Exception as exc:
            raise JevError(f"Jev assessment failed: {exc}") from exc

    @staticmethod
    def _response_json(result: Any) -> dict[str, Any]:
        try:
            raw = result.raw_http_response.json()
            return {
                "model": result.model,
                "request_id": result.request_id,
                "usage": raw.get("usage", {}),
                "answers": raw.get("answers", {}),
            }
        except Exception:
            return {"answers": {name: repr(answer) for name, answer in result.answers.items()}}

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "DecisionEngine":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
