<div align="center">

# Jev System One

### Ask in plain English. Get an answer. See the decisions behind it.

[![CI](https://github.com/haseeb-heaven/jev-system-one/actions/workflows/ci.yml/badge.svg)](https://github.com/haseeb-heaven/jev-system-one/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![TypeSafe Jev](https://img.shields.io/badge/TypeSafe-Jev-8B5CF6)](https://typesafe.ai/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22C55E.svg)](LICENSE)

A polished terminal interface where OpenAI generates useful answers and TypeSafe Jev independently evaluates their relevance, reliability, and quality.

</div>

![Jev System One terminal interface](docs/tui-preview.png)

## How it works

```text
Plain-English question
        ↓
OpenAI generates a structured answer
        ↓
Jev evaluates the question and answer
        ↓
The TUI presents the answer and decision report side by side
```

Jev makes four typed judgments for every answer:

| Decision | Primitive | What it measures |
| --- | --- | --- |
| Question type | Choice | Factual, instructional, creative, opinion, or unclear |
| Answers the question | Noul | Probability that the answer directly addresses the request |
| Unsupported claims | Noul | Probability that uncertain claims are presented as facts |
| Answer quality | Score | Usefulness and completeness on an ordered four-level rubric |

The report includes probabilities, confidence, model version, token usage, and the TypeSafe request ID.

## Features

- Full-screen Textual interface with responsive answer and decision panes
- Animated OpenAI → Jev processing state and progress bar
- Mouse wheel, two-finger trackpad, and draggable scrollbar support
- A clean current-question view that replaces stale results
- Non-interactive mode for scripts and shell workflows
- Explicit retries, timeouts, structured errors, and safe credential handling
- Automated linting and tests on GitHub Actions

## Quick start

```bash
git clone https://github.com/haseeb-heaven/jev-system-one.git
cd jev-system-one
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create `.env` in the project root:

```dotenv
JEV_API_KEY=your_jev_api_key
OPENAI_API_KEY=your_openai_api_key
```

Launch the interactive interface:

```bash
jev
```

Ask one question without opening the full-screen interface:

```bash
jev ask "How should I design a safe AI-assisted project editor?"
```

## Controls

| Input | Action |
| --- | --- |
| `Enter` or **Ask** | Submit the question |
| Mouse wheel / two-finger gesture | Scroll the pane under the pointer |
| Drag the cyan scrollbar | Move through long answers or reports |
| `Ctrl+R` | Focus the question input |
| `Ctrl+L` | Clear the current result |
| `Ctrl+Q` | Quit |

## Project layout

```text
src/jev_system_one/
├── cli.py             # TUI launcher and one-shot command
├── config.py          # Environment configuration
├── jev.py             # Official TypeSafe SDK integration
├── llm.py             # OpenAI structured answer generation
├── logging_setup.py   # Application and SDK logging
├── tui.py             # Textual interface and background workers
└── workflow.py        # OpenAI → Jev orchestration
```

The TypeSafe integration uses the official Python SDK with `TypeSafeClient`, `Choice`, `Noul`, `Score`, and `RetryPolicy`.

## Development

```bash
source .venv/bin/activate
pytest -q
ruff check .
```

Regenerate the interface screenshot after a visual change:

```bash
python scripts/capture_tui.py
rsvg-convert -o docs/tui-preview.png docs/tui-preview.svg
```

`master` contains the latest stable state. `develop` is the integration branch for ongoing work.

## Security

`.env` is ignored by Git. Never commit API keys, tokens, request payloads containing private data, or debug logs with sensitive content.

## License

[MIT](LICENSE)
