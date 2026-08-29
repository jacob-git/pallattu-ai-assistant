# Pallattu AI Assistant

A cost-efficient, local-first AI voice assistant and robotics platform for Raspberry Pi 5.

The first real release is an always-on assistant: idle listening stays on the Pi, a wake phrase activates the interaction, local VAD captures only useful speech, and cloud AI is called only when there is something to answer.

## v0.1 architecture

```text
Microphone (always local)
        |
        v
Porcupine wake-word detector
        |
        | wake phrase
        v
Cobra local VAD + utterance capture
        |
        | speech only
        v
GPT-4o mini Transcribe
        |
        v
GPT-5.6 Luna
        |
        v
GPT-4o mini TTS
        |
        v
ALSA / speaker
        |
        v
10-second local follow-up window
        |
        +-- speech --> another interaction
        |
        +-- timeout --> wake-word mode
```

Idle room audio is not sent to OpenAI.

## Current milestone: v0.1 Always-On Voice Assistant

Implemented:

- Always-on local wake-word detection with Porcupine
- Local voice activity detection with Cobra
- Speech/end-of-speech capture with a short pre-roll
- OpenAI speech-to-text
- Cost-sensitive GPT-5.6 Luna reasoning
- OpenAI text-to-speech
- Spoken playback through ALSA `aplay`
- Multi-turn follow-up window without repeating the wake phrase
- Automatic return to wake-word-only mode
- JSONL latency/usage metrics per cloud interaction
- Configuration validation
- User-level systemd service template

## Raspberry Pi setup

Requires Raspberry Pi OS, Python 3.11+, a working microphone, speaker, and `alsa-utils`.

```bash
git clone git@github.com:jacob-git/pallattu-ai-assistant.git
cd pallattu-ai-assistant

sudo apt update
sudo apt install -y python3-venv alsa-utils

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

cp .env.example .env
```

Add these two secrets to `.env`:

```text
OPENAI_API_KEY=...
PICOVOICE_ACCESS_KEY=...
```

Porcupine requires a Picovoice AccessKey. Wake-word and VAD inference run locally on the Pi.

### Wake phrase

The default bootstrap keyword is `porcupine`, because it is shipped with Porcupine and works without a custom model.

For the intended wake phrase **Hey Pallattu**:

1. Create the phrase in Picovoice Console for Raspberry Pi.
2. Download the generated `.ppn` file to the Pi, for example `models/hey-pallattu.ppn`.
3. Set this in `.env`:

```text
PALLATTU_WAKE_WORD_MODEL=/home/YOUR_USER/pallattu-ai-assistant/models/hey-pallattu.ppn
```

Do not commit the custom model or credentials to the public repository.

## Run

```bash
source .venv/bin/activate
pallattu-ai-assistant
```

Expected flow:

```text
say wake phrase
-> speak request
-> local silence detection ends recording
-> transcription
-> AI response
-> spoken response
-> follow-up listening
-> timeout back to wake mode
```

## Run automatically

Install the included service as a user service:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/pallattu-ai-assistant.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now pallattu-ai-assistant.service
```

To allow the user service to start after boot even before an interactive login:

```bash
sudo loginctl enable-linger "$USER"
```

Logs:

```bash
journalctl --user -u pallattu-ai-assistant -f
```

## Configuration

See `.env.example`. Useful tuning values include:

- `PALLATTU_AUDIO_INPUT_DEVICE_INDEX`
- `PALLATTU_VAD_THRESHOLD`
- `PALLATTU_END_SILENCE_SECONDS`
- `PALLATTU_FOLLOW_UP_SECONDS`
- `PALLATTU_MAX_UTTERANCE_SECONDS`
- `PALLATTU_LLM_MODEL`
- `PALLATTU_TTS_VOICE`

Usage/latency records are appended to `data/usage.jsonl` by default.

## Cost strategy

The assistant intentionally does not maintain a cloud realtime audio connection while idle.

- Wake-word detection: local
- VAD: local
- Silence/room audio: local only
- STT: called once per actual utterance
- Reasoning: defaults to the cost-sensitive GPT-5.6 Luna model
- TTS: generated only for the final spoken response
- Conversation history: bounded to the most recent turns

This architecture can later switch an active conversation to a realtime model if measured latency justifies the additional cost.

## Roadmap

| Version | Capability | Outcome |
| --- | --- | --- |
| v0.1 | Always-on voice assistant | Wake, converse, follow up, sleep |
| v0.2 | Tool router | Safe local actions and home/robot tools |
| v0.3 | Durable memory | Useful preferences and summarized context |
| v0.4 | Vision | Camera perception and person/object awareness |
| v0.5 | Sensors | Environment awareness |
| v0.6 | Mobility | Safe motor control and obstacle handling |
| v1.0 | Integrated assistant | Voice + perception + tools + physical action |

## Development

```bash
ruff check .
pytest
```

Never commit `.env`, API keys, Wi-Fi credentials, recordings, personal conversations, or home-network configuration.

## License

A license will be selected before the first public release. Until then, all rights are reserved.
