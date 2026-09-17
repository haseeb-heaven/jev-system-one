import json
from typing import Any

from openai import OpenAI


class LLMError(RuntimeError):
    pass


class Planner:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def draft(
        self,
        question: str,
        routing: dict[str, Any],
        routing_policy: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self._generate(
            "Write a draft answer using Jev's routing decision as the sole authority for "
            "response mode, clarification, uncertainty, and depth. "
            "If the question is a follow-up, interpret it within the ongoing conversation.",
            {
                "user_question": question,
                "conversation_history": [
                    {"question": item.get("question", ""), "answer": item.get("answer", "")}
                    for item in (history or [])
                ],
                "jev_routing_decision": routing,
                "jev_routing_policy": routing_policy,
                "rules": [
                    "Do not independently classify the question or decide response policy.",
                    "Follow the Jev decision probabilities and scores supplied in the state.",
                    "Use conversation_history to resolve follow-ups, pronouns, or clarifications.",
                    "Generate answer text only; Jev will review it before it is shown.",
                ],
            },
            history=history,
        )

    def finalize(
        self,
        question: str,
        routing: dict[str, Any],
        routing_policy: dict[str, Any],
        draft: dict[str, Any],
        review: dict[str, Any],
        review_policy: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self._generate(
            "Write the final answer. Jev owns every decision: use its routing decision and "
            "draft review exactly as supplied. Do not override them or make new policy decisions. "
            "Ensure the answer fits naturally into the ongoing conversation.",
            {
                "user_question": question,
                "conversation_history": [
                    {"question": item.get("question", ""), "answer": item.get("answer", "")}
                    for item in (history or [])
                ],
                "jev_routing_decision": routing,
                "jev_routing_policy": routing_policy,
                "openai_draft": draft,
                "jev_draft_review": review,
                "jev_review_policy": review_policy,
                "rules": [
                    "Use the Jev answer-quality score and probabilities to revise the draft.",
                    "If Jev flags unsupported claims, remove or qualify them.",
                    (
                        "If Jev requires clarification, ask the concise clarification instead "
                        "of guessing."
                    ),
                    "Maintain conversational context from prior turns when answering follow-ups.",
                    "Return answer wording only; do not explain or alter Jev's decisions.",
                ],
            },
            history=history,
        )

    def _generate(
        self,
        instruction: str,
        state: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        prompt = {
            "instruction": instruction,
            "state": state,
            "output": {
                "answer": "A direct, useful answer in plain language.",
                "summary": "One-sentence summary.",
                "assumptions": ["Only assumptions that materially affect the answer."],
            },
            "rules": [
                "Return valid JSON only.",
                "Keep assumptions empty when none are needed.",
            ],
        }
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You write answers; Jev is the decision authority. "
                    "When conversation history is present, interpret follow-up questions in "
                    "context while strictly following Jev's decisions."
                ),
            }
        ]
        if history:
            for turn in history:
                q = turn.get("question")
                a = turn.get("answer")
                if q:
                    messages.append({"role": "user", "content": q})
                if a:
                    messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": json.dumps(prompt)})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=messages,
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            if not isinstance(result, dict) or not isinstance(result.get("answer"), str):
                raise ValueError("response lacks an answer")
            return result
        except Exception as exc:
            raise LLMError(f"OpenAI answer generation failed: {exc}") from exc
