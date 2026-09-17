import json
import logging
from typing import Any

from openai import OpenAI

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class Planner:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def answer(self, question: str) -> dict[str, Any]:
        prompt = {
            "question": question,
            "output": {
                "answer": "A direct, useful answer in plain language.",
                "summary": "One-sentence summary.",
                "assumptions": ["Only assumptions that materially affect the answer."],
            },
            "rules": [
                "Return valid JSON only.",
                "Answer the user's actual question.",
                "Say when information is uncertain or unavailable.",
                "Keep assumptions empty when none are needed.",
            ],
        }
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise, concise general-purpose assistant.",
                    },
                    {"role": "user", "content": json.dumps(prompt)},
                ],
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            if not isinstance(result, dict) or not isinstance(result.get("answer"), str):
                raise ValueError("response lacks an answer")
            return result
        except Exception as exc:
            raise LLMError(f"OpenAI answer generation failed: {exc}") from exc
