from __future__ import annotations

import platform
from dataclasses import dataclass

import sounddevice as sd

from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.device import discover_device_capabilities


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def run_doctor(settings: Settings) -> list[DoctorCheck]:
    capabilities = discover_device_capabilities()
    capability_detail = _capability_summary(
        capabilities.is_raspberry_pi,
        capabilities.has_temperature,
        capabilities.has_gpio,
    )
    checks: list[DoctorCheck] = [
        DoctorCheck("Platform", True, f"{platform.system()} {platform.machine()}"),
        DoctorCheck(
            "Device model",
            True,
            capabilities.model or "generic desktop/server",
        ),
        DoctorCheck("Capabilities", True, capability_detail),
        DoctorCheck(
            "OpenAI key",
            bool(settings.openai_api_key),
            "configured" if settings.openai_api_key else "missing",
        ),
        DoctorCheck("VAD engine", True, settings.vad_engine),
    ]

    if settings.wake_word_model:
        checks.append(
            DoctorCheck(
                "Wake-word model",
                settings.wake_word_model.exists(),
                str(settings.wake_word_model),
            )
        )
    else:
        checks.append(DoctorCheck("Wake word", True, f"openWakeWord: {settings.wake_model}"))

    try:
        devices = sd.query_devices()
        default_input, default_output = sd.default.device
        checks.append(
            DoctorCheck(
                "Microphone",
                default_input is not None and default_input >= 0,
                _device_name(devices, default_input),
            )
        )
        checks.append(
            DoctorCheck(
                "Speaker",
                default_output is not None and default_output >= 0,
                _device_name(devices, default_output),
            )
        )
    except (sd.PortAudioError, OSError, TypeError, ValueError) as exc:
        checks.append(DoctorCheck("Audio devices", False, str(exc)))

    return checks


def _capability_summary(is_pi: bool, has_temperature: bool, has_gpio: bool) -> str:
    capabilities = ["portable tools"]
    if is_pi:
        capabilities.append("Raspberry Pi")
    if has_temperature:
        capabilities.append("temperature")
    if has_gpio:
        capabilities.append("GPIO read-only")
    return ", ".join(capabilities)


def _device_name(devices, index: int | None) -> str:
    if index is None or index < 0:
        return "no default device"
    try:
        return str(devices[index]["name"])
    except (IndexError, KeyError, TypeError):
        return f"device {index}"
