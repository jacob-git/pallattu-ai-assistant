from __future__ import annotations

from pallattu_ai_assistant.adapters import JsonlMetricsAdapter, SoundDeviceAudioOutputAdapter
from pallattu_ai_assistant.app import AssistantApp
from pallattu_ai_assistant.audio_runtime import OpenWakeWordPerceptionAdapter
from pallattu_ai_assistant.camera import build_vision_adapter
from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.memory import (
    CompositeToolRegistry,
    MemoryToolAdapter,
    SQLiteMemoryAdapter,
)
from pallattu_ai_assistant.openai_pipeline import OpenAIVoiceAdapter
from pallattu_ai_assistant.robot_actions import RobotActionToolAdapter, SafeRobotController
from pallattu_ai_assistant.robot_gpio import (
    RaspberryPiGpioZeroActuatorAdapter,
    build_actuator_adapter,
)
from pallattu_ai_assistant.tools import PortableToolRegistry
from pallattu_ai_assistant.vision_tools import OpenAIVisionAnalysisAdapter, VisionToolAdapter
from pallattu_ai_assistant.wake_ack import LocalWakeAcknowledgementAdapter


def build_app(settings: Settings) -> AssistantApp:
    memory = SQLiteMemoryAdapter(
        settings.memory_path,
        max_conversation_messages=settings.memory_max_messages,
    )
    camera = build_vision_adapter()
    actuator = build_actuator_adapter(settings)
    controller = SafeRobotController(actuator)
    gpio_adapter = RaspberryPiGpioZeroActuatorAdapter(settings)
    tools = CompositeToolRegistry(
        PortableToolRegistry(),
        MemoryToolAdapter(memory),
        VisionToolAdapter(camera, OpenAIVisionAnalysisAdapter(settings)),
        RobotActionToolAdapter(
            controller,
            enabled=settings.robot_actions_enabled,
            servo_configured=gpio_adapter.servo_configured,
            drive_configured=gpio_adapter.drive_configured,
        ),
    )
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
