from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    log_level: str = "INFO"
    audio_input_device: str | None = None
    audio_output_device: str | None = None
    wake_word: str = "pallattu"


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        log_level=os.getenv("PALLATTU_LOG_LEVEL", "INFO"),
        audio_input_device=os.getenv("PALLATTU_AUDIO_INPUT_DEVICE") or None,
        audio_output_device=os.getenv("PALLATTU_AUDIO_OUTPUT_DEVICE") or None,
        wake_word=os.getenv("PALLATTU_WAKE_WORD", "pallattu"),
    )
