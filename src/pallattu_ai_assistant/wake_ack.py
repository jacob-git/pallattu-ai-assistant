from __future__ import annotations

import logging
import platform
import shutil
import subprocess

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class LocalWakeAcknowledgementAdapter:
    """Instant local beep plus optional device-native speech acknowledgement."""

    def __init__(self, mode: str, text: str, gain: float = 1.0) -> None:
        self.mode = mode
        self.text = text
        self.gain = gain

    def acknowledge(self) -> None:
        if self.mode == "none":
            return
        if self.mode in {"beep", "beep_and_voice"}:
            self._beep()
        if self.mode in {"voice", "beep_and_voice"} and self.text:
            self._speak_local(self.text)

    def _beep(self) -> None:
        sample_rate = 24_000
        duration_seconds = 0.09
        frequency_hz = 880.0
        samples = np.arange(int(sample_rate * duration_seconds), dtype=np.float32)
        wave = np.sin(2.0 * np.pi * frequency_hz * samples / sample_rate)
        amplitude = min(0.35 * self.gain, 0.9)
        sd.play((wave * amplitude).astype(np.float32), samplerate=sample_rate)
        sd.wait()

    @staticmethod
    def _speak_local(text: str) -> None:
        command = _local_tts_command(text)
        if command is None:
            logger.warning("No local speech engine found; wake acknowledgement will use beep only")
            return
        try:
            subprocess.run(
                command,
                check=False,
                timeout=8,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Local wake acknowledgement speech failed: %s", exc)


def _local_tts_command(text: str) -> list[str] | None:
    system = platform.system()
    if system == "Darwin" and shutil.which("say"):
        return ["say", text]
    if system == "Linux":
        engine = shutil.which("espeak-ng") or shutil.which("espeak")
        if engine:
            return [engine, text]
    if system == "Windows":
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell:
            escaped = text.replace("'", "''")
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Speak('{escaped}')"
            )
            return [powershell, "-NoProfile", "-Command", script]
    return None
