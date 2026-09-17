import json
import logging
from typing import Any

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    Markdown,
    ProgressBar,
    Static,
)

from .config import ConfigError, Settings
from .jev import DecisionEngine
from .llm import Planner
from .logging_setup import configure_logging
from .workflow import Workflow

log = logging.getLogger(__name__)


class ScrollPane(VerticalScroll):
    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self.scroll_relative(y=max(3, abs(event.delta_y) * 3), immediate=True)
        event.stop()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self.scroll_relative(y=-max(3, abs(event.delta_y) * 3), immediate=True)
        event.stop()


class JevApp(App[None]):
    TITLE = "Jev System One"
    SUB_TITLE = "Jev decides · OpenAI writes"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+r", "focus_input", "Ask"),
    ]
    CSS = """
    Screen { background: #080b12; color: #e6edf7; }
    Header { background: #111827; color: #f8fafc; }
    #shell { height: 1fr; padding: 1 2; }
    #hero { height: 3; content-align: left middle; color: #8da2c0; }
    #workspace { height: 1fr; }
    .pane { border: round #26344d; background: #0d1320; padding: 1 2; }
    #conversation-pane { width: 2fr; margin-right: 1; }
    #decision-pane { width: 1fr; }
    .pane-title { height: 2; color: #71d7ff; text-style: bold; }
    #conversation, #decisions { height: 1fr; }
    ScrollPane {
        overflow-y: scroll;
        scrollbar-size-vertical: 2;
        scrollbar-color: #22d3ee;
        scrollbar-color-hover: #67e8f9;
        scrollbar-color-active: #a78bfa;
    }
    #thinking { height: 3; display: none; color: #a78bfa; }
    #progress { height: 1; display: none; color: #22d3ee; background: #162033; }
    #status { height: 2; color: #93a4bf; content-align: left middle; }
    #composer { height: 5; padding: 1 2; background: #111827; }
    #question { width: 1fr; border: tall #344766; }
    #question:focus { border: tall #22d3ee; }
    #send { width: 14; margin-left: 1; background: #0891b2; color: white; }
    Footer { background: #0d1320; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.settings: Settings | None = None
        self.history: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="shell"):
            yield Static(
                "Jev decides the policy and reviews the draft. OpenAI only writes from "
                "those decisions.",
                id="hero",
            )
            with Horizontal(id="workspace"):
                with Vertical(id="conversation-pane", classes="pane"):
                    yield Static("CONVERSATION", classes="pane-title")
                    with ScrollPane(id="conversation"):
                        yield Markdown("*Your answer will appear here.*", id="answer")
                with Vertical(id="decision-pane", classes="pane"):
                    yield Static("JEV DECISION TRAIL", classes="pane-title")
                    with ScrollPane(id="decisions"):
                        yield Markdown("*Waiting for a question.*", id="decision-content")
            yield LoadingIndicator(id="thinking")
            yield ProgressBar(total=4, show_eta=False, id="progress")
            yield Static("Ready", id="status")
        with Horizontal(id="composer"):
            yield Input(placeholder="Ask a general question…", id="question")
            yield Button("Ask  ↵", id="send", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.settings = Settings.from_env()
            configure_logging(self.settings.log_level)
            self.query_one("#question", Input).focus()
        except ConfigError as exc:
            self.query_one("#status", Static).update(f"Configuration error: {exc}")
            self.notify(str(exc), severity="error", timeout=8)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send":
            self._submit(self.query_one("#question", Input).value)

    def _submit(self, question: str) -> None:
        question = question.strip()
        if not question or not self.settings:
            return
        input_widget = self.query_one("#question", Input)
        input_widget.value = ""
        input_widget.disabled = True
        self.query_one("#send", Button).disabled = True
        self.query_one("#thinking", LoadingIndicator).display = True
        self.query_one("#progress", ProgressBar).display = True
        self.query_one("#progress", ProgressBar).update(progress=0)
        self._update_conversation_display(pending_question=question)
        self.query_one("#decision-content", Markdown).update("*Waiting for Jev…*")
        self.query_one("#status", Static).update("Jev is deciding the response policy…")
        self.process_question(question)

    @work(thread=True, exclusive=True, exit_on_error=False)
    def process_question(self, question: str) -> None:
        assert self.settings is not None
        try:
            planner = Planner(self.settings.llm_api_key, self.settings.llm_model)
            with DecisionEngine(self.settings.jev_api_key, self.settings.jev_model) as jev:
                result = Workflow(planner, jev).run(
                    question,
                    history=self.history,
                    on_progress=lambda step, message: self.call_from_thread(
                        self._stage,
                        step,
                        message,
                    ),
                )
            self.call_from_thread(
                self._render_result,
                question,
                result.response,
                result.decisions,
            )
        except Exception as exc:
            log.exception("question processing failed")
            self.call_from_thread(self._render_error, str(exc))

    def _stage(self, progress: int, status: str) -> None:
        self.query_one("#progress", ProgressBar).update(progress=progress)
        self.query_one("#status", Static).update(status)

    def _update_conversation_display(self, pending_question: str | None = None) -> None:
        blocks: list[str] = []
        for turn in self.history:
            assumptions = turn.get("assumptions") or []
            assumption_text = ""
            if assumptions:
                assumption_text = "\n\n**Assumptions**\n" + "\n".join(
                    f"- {item}" for item in assumptions
                )
            blocks.append(
                f"## You\n\n{turn['question']}\n\n## Answer\n\n{turn['answer']}{assumption_text}"
            )
        if pending_question:
            blocks.append(f"## You\n\n{pending_question}\n\n*Thinking…*")

        content = "\n\n---\n\n".join(blocks) if blocks else "*Your answer will appear here.*"
        self.query_one("#answer", Markdown).update(content)

    def _render_result(
        self,
        question: str,
        response: dict[str, Any],
        decisions: dict[str, Any],
    ) -> None:
        self.history.append(
            {
                "question": question,
                "answer": response["answer"],
                "assumptions": response.get("assumptions") or [],
                "decisions": decisions,
            }
        )
        self._update_conversation_display()
        self.query_one("#decision-content", Markdown).update(self._decision_markdown(decisions))
        self.query_one("#conversation", ScrollPane).scroll_end(animate=False)
        self.query_one("#decisions", ScrollPane).scroll_home(animate=False)
        self.query_one("#progress", ProgressBar).update(progress=4)
        self._finish("Complete · Jev decisions guided the final answer")

    def _render_error(self, message: str) -> None:
        self._update_conversation_display()
        self._finish(f"Error · {message}")
        self.notify(message, severity="error", timeout=8)

    def _finish(self, status: str) -> None:
        self.query_one("#thinking", LoadingIndicator).display = False
        self.query_one("#progress", ProgressBar).display = False
        self.query_one("#status", Static).update(status)
        self.query_one("#question", Input).disabled = False
        self.query_one("#send", Button).disabled = False
        self.query_one("#question", Input).focus()

    @staticmethod
    def _decision_markdown(decisions: dict[str, Any]) -> str:
        sections = []
        for stage, decision in decisions.items():
            title = stage.replace("_", " ").title()
            sections.append(f"## Jev {title}\n\n**Model:** `{decision.get('model', 'unknown')}`")
            for name, value in decision.get("answers", {}).items():
                answer_title = name.replace("_", " ").title()
                sections.append(
                    f"### {answer_title}\n\n```json\n{json.dumps(value, indent=2)}\n```"
                )
            request_id = decision.get("request_id")
            if request_id:
                sections.append(f"**Request ID:** `{request_id}`")
        return "\n\n".join(sections)

    def action_clear(self) -> None:
        self.history.clear()
        self.query_one("#answer", Markdown).update("*Conversation cleared.*")
        self.query_one("#decision-content", Markdown).update("*Waiting for a question.*")
        self.query_one("#status", Static).update("Ready")

    def action_focus_input(self) -> None:
        self.query_one("#question", Input).focus()
