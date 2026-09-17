import asyncio

from jev_system_one.tui import JevApp


def test_tui_starts(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev-test")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")

    async def check() -> None:
        async with JevApp().run_test() as pilot:
            assert pilot.app.query_one("#question")
            assert pilot.app.query_one("#decision-content")

    asyncio.run(check())
