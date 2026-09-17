# jev-system-one

A polished terminal app that combines OpenAI answers with TypeSafe Jev decisions.

Ask any general question in plain English. OpenAI writes a structured answer, then Jev independently evaluates the question type, relevance, unsupported claims, and answer quality. The Textual interface shows the conversation and complete Jev decision report side by side.

## Setup

```bash
git clone <your-repository-url>
cd jev-system-one
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Set both keys in `.env`:

```dotenv
JEV_API_KEY=your_typesafe_api_key
OPENAI_API_KEY=your_openai_api_key
```

The app reads `JEV_API_KEY` and passes it explicitly to `TypeSafeClient`.

## Run

```bash
jev
```

The full-screen TUI supports:

- animated OpenAI and Jev thinking states;
- a two-stage progress bar;
- conversation history and a detailed decision panel;
- mouse wheel or `Page Up`/`Page Down` to scroll the current answer;
- `Ctrl+L` to clear, `Ctrl+R` to focus the input, and `Ctrl+Q` to quit.

Each new question replaces the previous answer and Jev report, keeping the interface focused on the current request.

For a non-interactive single question:

```bash
jev ask "Why is the sky blue?"
```

The API keys stay local in `.env` and are ignored by Git.

## Test and lint

```bash
pytest
ruff check .
```

## Architecture

`tui.py` provides the Textual interface and background workers. `llm.py` generates structured answers with the OpenAI SDK. `jev.py` uses the official TypeSafe SDK with typed `Choice`, `Noul`, and `Score` questions plus retries. `workflow.py` coordinates both models for non-interactive use.

## License

MIT
