# Pallattu AI Assistant

A cost-efficient, local-first AI voice assistant and robotics platform for Raspberry Pi 5.

The project starts as a reliable voice assistant and is designed to grow into a home robot with memory, vision, sensors, tools, and safe physical actions.

## Goals

- Natural voice conversations on Raspberry Pi 5
- Keep always-on processing local where practical
- Send only useful speech/context to cloud AI services
- Track latency and cloud cost from the beginning
- Keep AI providers behind clean interfaces
- Separate AI reasoning from hardware control and safety
- Grow incrementally from voice chat to robotics

## Architecture

```text
Microphone
    |
    v
Local Audio Pipeline
(VAD / wake word / recording)
    |
    v
Speech-to-Text
    |
    v
Conversation Orchestrator -----> Memory
    |                    \
    |                     ---> Tool Requests
    v                              |
Language Model                     v
    |                       Robot Controller
    |                       (safety boundary)
    v                              |
Text-to-Speech              GPIO / motors / sensors
    |
    v
Speaker
```

The core principle is **local first, cloud when valuable**. Wake-word detection, voice activity detection, device state, hardware control, and safety rules should remain local. Cloud services can initially provide high-quality speech recognition, reasoning, and speech synthesis.

## Roadmap

| Version | Capability | Outcome |
| --- | --- | --- |
| v0.1 | Audio foundation | Record and play audio reliably on Pi 5 |
| v0.2 | Push-to-talk AI | First end-to-end AI voice conversation |
| v0.3 | Hands-free voice | Local VAD detects speech and silence |
| v0.4 | Wake word | Local activation without idle API usage |
| v0.5 | Conversation memory | Context-aware multi-turn conversations |
| v0.6 | Tool execution | Safe AI-requested robot actions |
| v0.7 | Sensors | Environmental awareness |
| v0.8 | Vision | Camera perception and object/person detection |
| v0.9 | Mobility | Motors, navigation, obstacle handling |
| v1.0 | Integrated assistant | Voice + perception + safe physical action |

See [`docs/roadmap.md`](docs/roadmap.md) for milestones and acceptance criteria.

## Project structure

```text
pallattu-ai-assistant/
├── docs/
│   ├── architecture.md
│   └── roadmap.md
├── src/pallattu_ai_assistant/
│   ├── __init__.py
│   ├── config.py
│   └── main.py
├── tests/
├── .github/workflows/
├── .env.example
├── .gitignore
└── pyproject.toml
```

Modules for audio, AI providers, conversation, robotics, vision, observability, and cost tracking will be introduced only when their milestone begins. This keeps the codebase honest and avoids empty abstractions.

## Development setup

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pallattu-ai-assistant
```

Run checks:

```bash
ruff check .
pytest
```

## Configuration

Copy the example configuration:

```bash
cp .env.example .env
```

Never commit `.env`, API keys, Wi-Fi credentials, recordings, personal conversations, or home-network configuration.

## Current milestone: v0.1 Audio Foundation

The first implementation milestone is deliberately simple:

1. Detect the USB microphone and speaker on Raspberry Pi 5.
2. Record a short WAV file from Python.
3. Play it back through the configured speaker.
4. Make device selection configurable.
5. Add hardware diagnostics and tests that can run directly on the Pi.

AI integration comes in v0.2 after the audio path is reliable.

## License

A license will be selected before the first public release. Until then, all rights are reserved.
