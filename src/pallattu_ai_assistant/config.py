from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path.home() / ".pallattu-ai-assistant" / ".env"
DEFAULT_MEMORY_PATH = Path.home() / ".pallattu-ai-assistant" / "memory.sqlite3"


@dataclass(frozen=True)
class Settings:
    log_level: str
    openai_api_key: str
    audio_input_device_index: int
    wake_model: str
    wake_word_model: Path | None
    wake_threshold: float
    wake_ack: str
    wake_ack_text: str
    vad_engine: str
    vad_threshold: float
    webrtc_vad_mode: int
    end_silence_seconds: float
    follow_up_seconds: float
    max_utterance_seconds: float
    output_gain: float
    llm_model: str
    transcription_model: str
    tts_model: str
    tts_voice: str
    system_prompt: str
    memory_path: Path
    memory_max_messages: int
    metrics_path: Path


def _optional_path(value: str | None) -> Path | None:
    return Path(value).expanduser() if value else None


def resolve_config_path() -> Path | None:
    explicit = os.getenv("PALLATTU_CONFIG")
    if explicit:
        return Path(explicit).expanduser()

    local = Path.cwd() / ".env"
    if local.exists():
        return local

    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    return None


def load_settings() -> Settings:
    config_path = resolve_config_path()
    if config_path is not None:
        load_dotenv(dotenv_path=config_path)

    return Settings(
        log_level=os.getenv("PALLATTU_LOG_LEVEL", "INFO"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        audio_input_device_index=int(os.getenv("PALLATTU_AUDIO_INPUT_DEVICE_INDEX", "-1")),
        wake_model=os.getenv("PALLATTU_WAKE_MODEL", "hey jarvis"),
        wake_word_model=_optional_path(os.getenv("PALLATTU_WAKE_WORD_MODEL")),
        wake_threshold=float(os.getenv("PALLATTU_WAKE_THRESHOLD", "0.5")),
        wake_ack=os.getenv("PALLATTU_WAKE_ACK", "beep_and_voice").lower(),
        wake_ack_text=os.getenv("PALLATTU_WAKE_ACK_TEXT", "I'm listening."),
        vad_engine=os.getenv("PALLATTU_VAD_ENGINE", "silero").lower(),
        vad_threshold=float(os.getenv("PALLATTU_VAD_THRESHOLD", "0.5")),
        webrtc_vad_mode=int(os.getenv("PALLATTU_WEBRTC_VAD_MODE", "2")),
        end_silence_seconds=float(os.getenv("PALLATTU_END_SILENCE_SECONDS", "0.8")),
        follow_up_seconds=float(os.getenv("PALLATTU_FOLLOW_UP_SECONDS", "10")),
        max_utterance_seconds=float(os.getenv("PALLATTU_MAX_UTTERANCE_SECONDS", "20")),
        output_gain=float(os.getenv("PALLATTU_OUTPUT_GAIN", "1.0")),
        llm_model=os.getenv("PALLATTU_LLM_MODEL", "gpt-5.6-luna"),
        transcription_model=os.getenv("PALLATTU_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe"),
        tts_model=os.getenv("PALLATTU_TTS_MODEL", "gpt-4o-mini-tts"),
        tts_voice=os.getenv("PALLATTU_TTS_VOICE", "coral"),
        system_prompt=os.getenv(
            "PALLATTU_SYSTEM_PROMPT",
            (
                "You are Pallattu AI Assistant, a concise and helpful voice assistant. "
                "Answer naturally for spoken playback. Prefer short answers unless the user asks for detail. "
                "Use an available tool whenever a request depends on current time, current weather, or the "
                "status of the device running the assistant. Never claim live information is unavailable when "
                "an available tool can answer it. Use remember_fact when the user explicitly asks you to "
                "remember a stable fact or preference. Use forget_memory when the user asks you to forget one. "
                "Never store credentials or secrets in long-term memory."
            ),
        ),
        memory_path=Path(os.getenv("PALLATTU_MEMORY_PATH", str(DEFAULT_MEMORY_PATH))).expanduser(),
        memory_max_messages=int(os.getenv("PALLATTU_MEMORY_MAX_MESSAGES", "500")),
        metrics_path=Path(os.getenv("PALLATTU_METRICS_PATH", "data/usage.jsonl")),
    )


def validate_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    if not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required")
    if settings.wake_word_model and not settings.wake_word_model.exists():
        errors.append(f"Wake-word model not found: {settings.wake_word_model}")
    if not 0.0 <= settings.wake_threshold <= 1.0:
        errors.append("PALLATTU_WAKE_THRESHOLD must be between 0 and 1")
    if settings.wake_ack not in {"beep_and_voice", "beep", "voice", "none"}:
        errors.append("PALLATTU_WAKE_ACK must be beep_and_voice, beep, voice, or none")
    if settings.vad_engine not in {"silero", "webrtc"}:
        errors.append("PALLATTU_VAD_ENGINE must be 'silero' or 'webrtc'")
    if not 0.0 <= settings.vad_threshold <= 1.0:
        errors.append("PALLATTU_VAD_THRESHOLD must be between 0 and 1")
    if settings.webrtc_vad_mode not in {0, 1, 2, 3}:
        errors.append("PALLATTU_WEBRTC_VAD_MODE must be 0, 1, 2, or 3")
    if not 0.0 < settings.output_gain <= 4.0:
        errors.append("PALLATTU_OUTPUT_GAIN must be greater than 0 and at most 4.0")
    if settings.memory_max_messages < 20:
        errors.append("PALLATTU_MEMORY_MAX_MESSAGES must be at least 20")
    return errors
