from __future__ import annotations

from typing import Any, Protocol

from pallattu_ai_assistant.domain import AssistantReply, AudioBuffer, CapturedUtterance


class PerceptionPort(Protocol):
    def start(self) -> None: ...
    def close(self) -> None: ...
    def wait_for_wake_word(self) -> None: ...
    def capture_utterance(self, start_timeout_seconds: float) -> CapturedUtterance | None: ...


class VoiceAIPort(Protocol):
    def handle(self, audio: AudioBuffer) -> AssistantReply: ...


class ToolPort(Protocol):
    """Application-facing capability boundary for safe local/external tools."""

    def definitions(self) -> list[dict[str, Any]]: ...
    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class AudioOutputPort(Protocol):
    def play(self, audio: AudioBuffer) -> None: ...


class MetricsPort(Protocol):
    def record(self, reply: AssistantReply, captured: CapturedUtterance, elapsed_seconds: float) -> None: ...
