from __future__ import annotations

from pallattu_ai_assistant.adapters import JsonlMetricsAdapter, SoundDeviceAudioOutputAdapter
from pallattu_ai_assistant.app import AssistantApp
from pallattu_ai_assistant.audio_runtime import OpenWakeWordPerceptionAdapter
from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.memory import (
    CompositeToolRegistry,
    MemoryToolAdapter,
    SQLiteMemoryAdapter,
)
from pallattu_ai_assistant.openai_pipeline import OpenAIVoiceAdapter
from pallattu_ai_assistant.tools import PortableToolRegistry
from pallattu_ai_assistant.wake_ack import LocalWakeAcknowledgementAdapter


def build_app(settings: Settings) -> AssistantApp:
    memory = SQLiteMemoryAdapter(
        settings.memory_path,
        max_conversation_messages=settings.memory_max_messages,
    )
    tools = CompositeToolRegistry(PortableToolRegistry(), MemoryToolAdapter(memory))
    return AssistantApp(
        perception=OpenWakeWordPerceptionAdapter(settings),
        voice_ai=OpenAIVoiceAdapter(settings, tools, memory),
        audio_output=SoundDeviceAudioOutputAdapter(gain=settings.output_gain),
        metrics=JsonlMetricsAdapter(settings.metrics_path),
        follow_up_seconds=settings.follow_up_seconds,
        wake_acknowledgement=LocalWakeAcknowledgementAdapter(
            mode=settings.wake_ack,
            text=settings.wake_ack_text,
            gain=settings.output_gain,
        ),
    )
