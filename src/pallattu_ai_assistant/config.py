from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    log_level: str
    openai_api_key: str
    picovoice_access_key: str
    audio_input_device_index: int
    wake_keyword: str
    wake_word_model: Path | None
    vad_threshold: float
    end_silence_seconds: float
    follow_up_seconds: float
    max_utterance_seconds: float
    llm_model: str
    transcription_model: str
    tts_model: str
    tts_voice: str
    system_prompt: str
    metrics_path: Path


def _optional_path(value: str | None) -> Path | None:
    return Path(value).expanduser() if value else None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        log_level=os.getenv("PALLATTU_LOG_LEVEL", "INFO"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        picovoice_access_key=os.getenv("PICOVOICE_ACCESS_KEY", ""),
        audio_input_device_index=int(os.getenv("PALLATTU_AUDIO_INPUT_DEVICE_INDEX", "-1")),
        wake_keyword=os.getenv("PALLATTU_WAKE_KEYWORD", "porcupine"),
        wake_word_model=_optional_path(os.getenv("PALLATTU_WAKE_WORD_MODEL")),
        vad_threshold=float(os.getenv("PALLATTU_VAD_THRESHOLD", "0.55")),
        end_silence_seconds=float(os.getenv("PALLATTU_END_SILENCE_SECONDS", "0.8")),
        follow_up_seconds=float(os.getenv("PALLATTU_FOLLOW_UP_SECONDS", "10")),
        max_utterance_seconds=float(os.getenv("PALLATTU_MAX_UTTERANCE_SECONDS", "20")),
        llm_model=os.getenv("PALLATTU_LLM_MODEL", "gpt-5.6-luna"),
        transcription_model=os.getenv("PALLATTU_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe"),
        tts_model=os.getenv("PALLATTU_TTS_MODEL", "gpt-4o-mini-tts"),
        tts_voice=os.getenv("PALLATTU_TTS_VOICE", "coral"),
        system_prompt=os.getenv(
            "PALLATTU_SYSTEM_PROMPT",
            (
                "You are Pallattu AI Assistant, a concise and helpful voice assistant. "
                "Answer naturally for spoken playback. Prefer short answers unless the user asks for detail."
            ),
        ),
        metrics_path=Path(os.getenv("PALLATTU_METRICS_PATH", "data/usage.jsonl")),
    )


def validate_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    if not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required")
    if not settings.picovoice_access_key:
        errors.append("PICOVOICE_ACCESS_KEY is required")
    if settings.wake_word_model and not settings.wake_word_model.exists():
        errors.append(f"Wake-word model not found: {settings.wake_word_model}")
    if not 0.0 <= settings.vad_threshold <= 1.0:
        errors.append("PALLATTU_VAD_THRESHOLD must be between 0 and 1")
    return errors
