import asyncio

from jev_system_one.tui import JevApp


async def capture() -> None:
    app = JevApp()
    async with app.run_test(size=(132, 42)) as pilot:
        app._render_result(
            "How should I design a safe AI-assisted project editor?",
            {
                "answer": (
                    "Start with a small command model: every user request becomes a typed "
                    "operation, validation runs before execution, and destructive changes require "
                    "confirmation. Keep the editor state authoritative and use AI for "
                    "interpretation rather than direct mutation."
                ),
                "assumptions": [
                    "The editor already exposes deterministic commands.",
                    "Humans must remain in control of state-changing operations.",
                ],
            },
            {
                "model": "jev-1.13.0",
                "request_id": "req_preview",
                "answers": {
                    "question_type": {
                        "type": "choice",
                        "choice": "instructional",
                        "confidence": 0.94,
                        "probabilities": {
                            "instructional": 0.96,
                            "factual": 0.03,
                            "opinion": 0.01,
                        },
                    },
                    "answers_question": {"type": "noul", "noul": 0.97},
                    "contains_unsupported_claims": {"type": "noul", "noul": 0.08},
                    "answer_quality": {
                        "type": "score",
                        "score": 2.78,
                        "confidence": 0.81,
                    },
                },
            },
        )
        await pilot.pause()
        app.save_screenshot(filename="tui-preview.svg", path="docs")


if __name__ == "__main__":
    asyncio.run(capture())
