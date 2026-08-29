from __future__ import annotations

from pallattu_ai_assistant.adapters import JsonlMetricsAdapter, SoundDeviceAudioOutputAdapter
from pallattu_ai_assistant.app import AssistantApp
from pallattu_ai_assistant.audio_runtime import OpenWakeWordPerceptionAdapter
from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.openai_pipeline import OpenAIVoiceAdapter
from pallattu_ai_assistant.tools import PortableToolRegistry


def build_app(settings: Settings) -> AssistantApp:
    tools = PortableToolRegistry()
    return AssistantApp(
        perception=OpenWakeWordPerceptionAdapter(settings),
        voice_ai=OpenAIVoiceAdapter(settings, tools),
        audio_output=SoundDeviceAudioOutputAdapter(gain=settings.output_gain),
        metrics=JsonlMetricsAdapter(settings.metrics_path),
        follow_up_seconds=settings.follow_up_seconds,
    )
