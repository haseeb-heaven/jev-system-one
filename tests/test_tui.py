import asyncio

from jev_system_one.tui import JevApp


def test_tui_starts(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev-test")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")

    async def check() -> None:
        async with JevApp().run_test() as pilot:
            assert pilot.app.query_one("#question")
            assert pilot.app.query_one("#decision-content")
            pilot.app._render_result(
                "first question",
                {"answer": "first answer", "assumptions": []},
                {"model": "jev-test", "answers": {}},
            )
            pilot.app._render_result(
                "second question",
                {"answer": "second answer", "assumptions": []},
                {"model": "jev-test", "answers": {}},
            )
            await pilot.pause()
            answer = pilot.app.query_one("#answer").source
            assert "second answer" in answer
            assert "first answer" not in answer
            await pilot.press("pagedown")
            assert pilot.app.query_one("#conversation").has_focus

    asyncio.run(check())
