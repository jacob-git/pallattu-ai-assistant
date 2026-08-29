# Pallattu AI Assistant

Portable, cost-efficient, local-first AI voice assistant runtime.

The application is intentionally **not coupled to Raspberry Pi OS, Linux, systemd, ALSA, or any specific AI provider**. Raspberry Pi 5 is one deployment target, not part of the application architecture.

## Goal

Download the distribution, install it, configure your local AI keys, and run:

```bash
pip install pallattu_ai_assistant-*.whl
pallattu-ai-assistant init
# edit .env and add your keys
pallattu-ai-assistant run
```

No source-code changes should be required for a normal installation.

## Architecture

```text
External world
     |
     v
Perception adapter
(wake word + VAD + microphone)
     |
     v
+-------------------------+
| Portable Application    |
| Assistant state machine |
| Conversation behavior   |
+-----------+-------------+
            |
        Port interfaces
   +--------+--------+
   |        |        |
   v        v        v
Voice AI   Audio   Metrics
adapter    output  adapter
   |        |
OpenAI   sounddevice
```

The application core imports only domain types and port interfaces. Technology choices are wired at the composition root in `bootstrap.py`.

Current adapters:

- Picovoice Porcupine + Cobra + PvRecorder for local wake word, VAD, and microphone capture
- OpenAI for STT, reasoning, and TTS
- `sounddevice` for portable audio playback
- JSONL for local usage/latency metrics

Future adapters can replace any of these without changing the assistant state machine.

## Runtime behavior

```text
SLEEPING
   |
   | local wake word
   v
LISTENING
   |
   | local VAD detects end of speech
   v
THINKING
   |
   | STT -> LLM -> TTS
   v
SPEAKING
   |
   v
FOLLOW-UP WINDOW
   |              |
 speech        timeout
   |              |
   +-> LISTENING  +-> SLEEPING
```

Idle room audio is processed locally. Cloud AI is invoked only after wake activation and speech capture.

## Install from a distribution

A tagged build produces a Python wheel and source distribution through GitHub Actions.

On the target machine, with Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate   # use the equivalent command on your platform
pip install pallattu_ai_assistant-*.whl
pallattu-ai-assistant init
```

`init` creates a local `.env` file. Add:

```text
OPENAI_API_KEY=...
PICOVOICE_ACCESS_KEY=...
```

Then:

```bash
pallattu-ai-assistant run
```

For the first run the built-in Porcupine keyword is used. To use a custom phrase such as **Hey Pallattu**, store the Picovoice `.ppn` file anywhere locally and set:

```text
PALLATTU_WAKE_WORD_MODEL=/your/local/path/hey-pallattu.ppn
```

No machine-specific path is embedded in the program.

## Project boundaries

```text
src/pallattu_ai_assistant/
├── domain.py           # portable value types
├── ports.py            # interfaces owned by the application
├── app.py              # assistant behavior/state machine
├── bootstrap.py        # chooses concrete adapters
├── audio_runtime.py    # Picovoice perception adapter
├── openai_pipeline.py  # OpenAI voice adapter
├── adapters.py         # playback + metrics adapters
├── config.py           # environment/local configuration
└── main.py             # portable CLI
```

Operating-system startup mechanisms belong outside the application. A systemd unit, launchd configuration, Windows service wrapper, Docker image, or process supervisor may be supplied as optional deployment examples, but the core never depends on them.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
```

## Security

Never commit `.env`, API keys, custom private configuration, recordings, personal conversations, or household/network information.

## Roadmap

The next architectural layer is a tool/action port so conversational AI can safely request local capabilities such as sensors, home automation, vision, or robot motion without directly controlling hardware.
