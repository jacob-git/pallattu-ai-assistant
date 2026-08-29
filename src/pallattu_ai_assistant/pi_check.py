from __future__ import annotations

import importlib.util
import platform
from dataclasses import dataclass

import sounddevice as sd

from pallattu_ai_assistant.camera import build_vision_adapter
from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.device import discover_device_capabilities
from pallattu_ai_assistant.memory import SQLiteMemoryAdapter


@dataclass(frozen=True)
class PiCheck:
    name: str
    ok: bool
    detail: str


def run_pi_check(settings: Settings) -> list[PiCheck]:
    capabilities = discover_device_capabilities()
    checks: list[PiCheck] = [
        PiCheck("Platform", capabilities.is_raspberry_pi, capabilities.model or platform.platform()),
        PiCheck("Architecture", True, capabilities.architecture),
        PiCheck("OpenAI key", bool(settings.openai_api_key), "configured" if settings.openai_api_key else "missing"),
        PiCheck("Wake stack", importlib.util.find_spec("openwakeword") is not None, settings.wake_model),
        PiCheck("VAD", True, settings.vad_engine),
    ]

    try:
        devices = sd.query_devices()
        default_input, default_output = sd.default.device
        checks.append(PiCheck("Microphone", default_input is not None and default_input >= 0, _device_name(devices, default_input)))
        checks.append(PiCheck("Speaker", default_output is not None and default_output >= 0, _device_name(devices, default_output)))
    except (sd.PortAudioError, OSError, TypeError, ValueError) as exc:
        checks.append(PiCheck("Audio devices", False, str(exc)))

    camera = build_vision_adapter()
    checks.append(PiCheck("Camera adapter", camera.available(), camera.describe_source()))
    checks.append(PiCheck("Picamera2", importlib.util.find_spec("picamera2") is not None, "installed" if importlib.util.find_spec("picamera2") is not None else "not installed"))

    checks.append(PiCheck("Temperature", capabilities.has_temperature, "available" if capabilities.has_temperature else "unavailable"))
    checks.append(PiCheck("GPIO", capabilities.has_gpio, f"{len(capabilities.gpio_chips)} gpiochip device(s)" if capabilities.has_gpio else "unavailable"))

    try:
        memory = SQLiteMemoryAdapter(settings.memory_path, max_conversation_messages=settings.memory_max_messages)
        stats = memory.stats()
        checks.append(PiCheck("Memory", True, f"{settings.memory_path} ({stats.get('conversation_messages', 0)} messages, {stats.get('long_term_memories', 0)} memories)"))
    except (OSError, ValueError) as exc:
        checks.append(PiCheck("Memory", False, str(exc)))

    robot_detail = "enabled" if settings.robot_actions_enabled else "disabled (safe default)"
    checks.append(PiCheck("Robot actions", True, robot_detail))
    return checks


def _device_name(devices, index: int | None) -> str:
    if index is None or index < 0:
        return "no default device"
    try:
        return str(devices[index]["name"])
    except (IndexError, KeyError, TypeError):
        return f"device {index}"
