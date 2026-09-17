import json
import logging

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel

from .config import ConfigError, Settings
from .jev import DecisionEngine, JevError
from .llm import LLMError, Planner
from .logging_setup import configure_logging
from .tui import JevApp
from .workflow import Workflow

app = typer.Typer(add_completion=False, invoke_without_command=True)
console = Console()
log = logging.getLogger(__name__)


@app.callback()
def main(ctx: typer.Context) -> None:
    """Open the Jev System One TUI, or use `jev ask QUESTION`."""
    if ctx.invoked_subcommand is None:
        JevApp().run()


@app.command()
def ask(question: str = typer.Argument(..., help="Any plain-English question.")) -> None:
    try:
        settings = Settings.from_env()
        configure_logging(settings.log_level)
        with DecisionEngine(settings.jev_api_key, settings.jev_model) as jev:
            result = Workflow(Planner(settings.llm_api_key, settings.llm_model), jev).run(question)
        console.print(Panel(result.response["answer"], title="Answer", border_style="green"))
        console.print(Panel(JSON(json.dumps(result.decisions)), title="Jev decisions",
                            border_style="magenta"))
    except (ConfigError, LLMError, JevError) as exc:
        log.error("question failed: %s", exc)
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc
