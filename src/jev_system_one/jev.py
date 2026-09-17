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

    def decide(self, question: str) -> dict[str, Any]:
        return self._ask(
            state={"user_question": question},
            questions={
                "response_mode": Choice(
                    instructions="What response mode should OpenAI use for `user_question`?",
                    criteria={
                        "factual": "Provide factual explanation or direct information.",
                        "instructional": "Provide steps, guidance, or advice.",
                        "creative": "Provide original ideas, writing, or brainstorming.",
                        "opinion": "Provide a recommendation with stated trade-offs.",
                        "clarify": (
                            "Ask a concise follow-up because the request is materially unclear."
                        ),
                    },
                ),
                "requires_clarification": Noul(
                    instructions="Does `user_question` require a clarification before answering?",
                    criteria={
                        "true": (
                            "A material detail is missing and guessing would make the answer "
                            "misleading."
                        ),
                        "false": "The question can be answered usefully without a follow-up.",
                    },
                ),
                "requires_uncertainty_notice": Noul(
                    instructions="Should the answer explicitly disclose uncertainty or limits?",
                    criteria={
                        "true": (
                            "The answer depends on incomplete, time-sensitive, ambiguous, or "
                            "uncertain information."
                        ),
                        "false": (
                            "A normal answer can be given without a special uncertainty notice."
                        ),
                    },
                ),
                "response_depth": Score(
                    instructions="How much detail should the answer contain?",
                    criteria=[
                        "brief: one direct answer with minimal context",
                        "standard: a concise answer with useful explanation",
                        "detailed: a thorough answer with structured reasoning or steps",
                    ],
                ),
            },
            label="routing decision",
        )

    def review(
        self,
        question: str,
        draft: dict[str, Any],
        routing: dict[str, Any],
    ) -> dict[str, Any]:
        return self._ask(
            state={
                "user_question": question,
                "jev_routing_decision": routing,
                "openai_draft": draft,
            },
            questions={
                "answers_question": Noul(
                    instructions="Does `openai_draft.answer` directly answer `user_question`?",
                    criteria={
                        "true": "The draft addresses the actual request with relevant information.",
                        "false": "The draft is off-topic, evasive, or incomplete for the request.",
                    },
                ),
                "contains_unsupported_claims": Noul(
                    instructions=(
                        "Does `openai_draft.answer` present uncertain or unsupported claims as "
                        "established facts?"
                    ),
                    criteria={
                        "true": (
                            "The draft makes claims without adequate basis or disclosed "
                            "uncertainty."
                        ),
                        "false": "Claims are supported, stable, or appropriately qualified.",
                    },
                ),
                "answer_quality": Score(
                    instructions=(
                        "How useful and complete is `openai_draft.answer` for `user_question`?"
                    ),
                    criteria=[
                        "poor: incorrect, irrelevant, or unusable",
                        "limited: partly useful but missing important information",
                        "good: relevant, clear, and sufficiently complete",
                        "excellent: precise, complete, and immediately useful",
                    ],
                ),
                "requires_revision": Noul(
                    instructions="Should OpenAI revise `openai_draft.answer` before it is shown?",
                    criteria={
                        "true": (
                            "The draft needs a material correction, qualification, or improvement."
                        ),
                        "false": "The draft can be shown without a material revision.",
                    },
                ),
            },
            label="draft review",
        )

    def _ask(
        self,
        state: dict[str, Any],
        questions: dict[str, Any],
        label: str,
    ) -> dict[str, Any]:
        try:
            result = self.client.system_one(state=state, questions=questions)
            return self._response_json(result)
        except Exception as exc:
            raise JevError(f"Jev {label} failed: {exc}") from exc

    @staticmethod
    def routing_policy(decision: dict[str, Any]) -> dict[str, Any]:
        answers = decision.get("answers", {})
        depth = answers.get("response_depth", {}).get("score", 1)
        levels = ("brief", "standard", "detailed")
        return {
            "response_mode": answers.get("response_mode", {}).get("choice", "clarify"),
            "response_mode_confidence": answers.get("response_mode", {}).get("confidence", 0),
            "clarification_required": answers.get("requires_clarification", {}).get("noul", 1)
            >= 0.5,
            "uncertainty_notice_required": answers.get(
                "requires_uncertainty_notice",
                {},
            ).get("noul", 1)
            >= 0.5,
            "response_depth": levels[max(0, min(2, round(depth)))],
            "response_depth_score": depth,
        }

    @staticmethod
    def review_policy(decision: dict[str, Any]) -> dict[str, Any]:
        answers = decision.get("answers", {})
        return {
            "answers_question_probability": answers.get("answers_question", {}).get("noul", 0),
            "unsupported_claim_probability": answers.get(
                "contains_unsupported_claims",
                {},
            ).get("noul", 1),
            "answer_quality_score": answers.get("answer_quality", {}).get("score", 0),
            "answer_quality_confidence": answers.get("answer_quality", {}).get("confidence", 0),
            "revision_required": answers.get("requires_revision", {}).get("noul", 1) >= 0.5,
        }

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
