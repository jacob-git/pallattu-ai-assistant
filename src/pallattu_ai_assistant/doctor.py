from __future__ import annotations

from dataclasses import dataclass
import platform

import sounddevice as sd

from pallattu_ai_assistant.config import Settings


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def run_doctor(settings: Settings) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = [
        DoctorCheck("Platform", True, f"{platform.system()} {platform.machine()}"),
        DoctorCheck("OpenAI key", bool(settings.openai_api_key), "configured" if settings.openai_api_key else "missing"),
        DoctorCheck("Picovoice key", bool(settings.picovoice_access_key), "configured" if settings.picovoice_access_key else "missing"),
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
        checks.append(DoctorCheck("Wake word", True, f"built-in: {settings.wake_keyword}"))

    try:
        devices = sd.query_devices()
        default_input, default_output = sd.default.device

        input_detail = _device_name(devices, default_input)
        output_detail = _device_name(devices, default_output)

        checks.append(DoctorCheck("Microphone", default_input is not None and default_input >= 0, input_detail))
        checks.append(DoctorCheck("Speaker", default_output is not None and default_output >= 0, output_detail))
    except Exception as exc:
        checks.append(DoctorCheck("Audio devices", False, str(exc)))

    return checks


def _device_name(devices, index: int | None) -> str:
    if index is None or index < 0:
        return "no default device"
    try:
        return str(devices[index]["name"])
    except Exception:
        return f"device {index}"
