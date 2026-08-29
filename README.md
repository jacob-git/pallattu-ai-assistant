# Pallattu AI Assistant

Portable, cost-efficient, local-first AI voice assistant runtime.

The application is intentionally **not coupled to Raspberry Pi OS, Linux, systemd, ALSA, or a proprietary wake-word service**. macOS is the first validated desktop target; Raspberry Pi 5 is a deployment target, not part of the application architecture.

## Goal

Download the distribution, install it, configure one AI key locally, and run:

```bash
pip install pallattu_ai_assistant-*.whl
pallattu-ai-assistant init
# edit .env and add OPENAI_API_KEY
pallattu-ai-assistant doctor
pallattu-ai-assistant run
```

No source-code changes should be required for a normal installation.

## Local voice stack

The always-listening path is open source and runs locally:

```text
Microphone
   |
   v
sounddevice
   |
   v
openWakeWord
   |
   | activation
   v
VAD strategy
   |-- Silero (default)
   `-- WebRTC (switchable)
   |
   | captured speech only
   v
OpenAI STT -> LLM -> TTS
```

No Picovoice account or access key is required.

### Wake word

The first-run model is `hey jarvis`, one of openWakeWord's pretrained models. Later, point the application at a custom openWakeWord model for **Hey Pallattu**:

```text
PALLATTU_WAKE_WORD_MODEL=/your/local/path/hey-pallattu.tflite
```

Tune activation if needed:

```text
PALLATTU_WAKE_THRESHOLD=0.5
```

### Switch VAD engines

Silero is the default:

```text
PALLATTU_VAD_ENGINE=silero
PALLATTU_VAD_THRESHOLD=0.5
```

To compare WebRTC VAD on the same machine:

```text
PALLATTU_VAD_ENGINE=webrtc
PALLATTU_WEBRTC_VAD_MODE=2
```

WebRTC aggressiveness ranges from `0` to `3`; higher values reject more non-speech audio.

## macOS first run

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pallattu_ai_assistant-*.whl
pallattu-ai-assistant init
```

Add your OpenAI key to `.env`:

```text
OPENAI_API_KEY=...
```

Then:

```bash
pallattu-ai-assistant doctor
pallattu-ai-assistant run
```

If macOS blocks microphone access, allow your terminal application under **System Settings > Privacy & Security > Microphone**.

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

- openWakeWord for local wake-word detection
- Silero VAD as the default local speech detector
- WebRTC VAD as a switchable lightweight alternative
- `sounddevice` for portable microphone/audio playback
- OpenAI for STT, reasoning, and TTS
- JSONL for local usage/latency metrics

## Runtime behavior

```text
SLEEPING
   |
   | local wake word
   v
LISTENING
   |
   | selected local VAD detects end of speech
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

Idle room audio stays local. Cloud AI is invoked only after wake activation and speech capture.

## Project boundaries

```text
src/pallattu_ai_assistant/
├── domain.py           # portable value types
├── ports.py            # interfaces owned by the application
├── app.py              # assistant behavior/state machine
├── bootstrap.py        # chooses concrete adapters
├── audio_runtime.py    # openWakeWord + selectable VAD perception adapter
├── openai_pipeline.py  # OpenAI voice adapter
├── adapters.py         # playback + metrics adapters
├── doctor.py           # portable environment/audio diagnostics
├── config.py           # environment/local configuration
└── main.py             # portable CLI
```

Operating-system startup mechanisms belong outside the application.

## CI and distribution validation

CI runs on both Ubuntu and macOS. Each job lints, tests, builds the distribution, installs the wheel into a clean virtual environment, and validates the installed CLI.

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
