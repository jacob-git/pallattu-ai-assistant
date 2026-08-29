from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioBuffer:
    data: bytes
    sample_rate: int
    channels: int = 1
    sample_width: int = 2
    encoding: str = "wav"


@dataclass(frozen=True)
class ImageFrame:
    data: bytes
    media_type: str = "image/jpeg"
    width: int | None = None
    height: int | None = None
    source: str = "camera"


@dataclass(frozen=True)
class CapturedUtterance:
    audio: AudioBuffer
    duration_seconds: float


@dataclass(frozen=True)
class AssistantReply:
    transcript: str
    text: str
    audio: AudioBuffer
    input_tokens: int = 0
    output_tokens: int = 0
    transcription_seconds: float = 0.0
    reasoning_seconds: float = 0.0
    synthesis_seconds: float = 0.0
