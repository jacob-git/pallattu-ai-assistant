from __future__ import annotations

import logging
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

_ALSA_HW_PATTERN = re.compile(r"\(hw:(\d+),(\d+)\)")
_PERCENT_PATTERN = re.compile(r"\[(\d+)%\]")


@dataclass(frozen=True)
class AudioOutputSelection:
    device_index: int | None
    sample_rate: int
    device_name: str
    alsa_card: int | None = None


def resolve_audio_output() -> AudioOutputSelection:
    """Prefer the output side of the active/default microphone device when available."""
    devices = sd.query_devices()
    default_input, default_output = sd.default.device

    input_index = _valid_index(default_input, len(devices))
    output_index = _valid_index(default_output, len(devices))

    if input_index is not None:
        input_name = str(devices[input_index]["name"])
        input_identity = _device_identity(input_name)
        for index, device in enumerate(devices):
            if int(device.get("max_output_channels", 0)) <= 0:
                continue
            candidate_name = str(device.get("name", ""))
            if _device_identity(candidate_name) == input_identity:
                output_index = index
                break

    if output_index is None:
        return AudioOutputSelection(None, 48_000, "default")

    selected = devices[output_index]
    name = str(selected["name"])
    sample_rate = int(round(float(selected.get("default_samplerate") or 48_000)))
    return AudioOutputSelection(
        device_index=output_index,
        sample_rate=sample_rate,
        device_name=name,
        alsa_card=_alsa_card(name),
    )


def prepare_audio_output(selection: AudioOutputSelection, zero_volume_percent: int = 80) -> None:
    """Repair a zero ALSA PCM playback mixer without changing healthy user volume settings."""
    if platform.system() != "Linux" or selection.alsa_card is None or not shutil.which("amixer"):
        return

    try:
        status = subprocess.run(
            ["amixer", "-c", str(selection.alsa_card), "get", "PCM"],
            check=False,
            timeout=3,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not inspect ALSA playback volume: %s", exc)
        return

    if status.returncode != 0:
        return

    percentages = [int(value) for value in _PERCENT_PATTERN.findall(status.stdout)]
    if not percentages or max(percentages) > 0:
        return

    target = max(1, min(100, zero_volume_percent))
    try:
        result = subprocess.run(
            ["amixer", "-c", str(selection.alsa_card), "set", "PCM", f"{target}%"],
            check=False,
            timeout=3,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            logger.info(
                "ALSA playback volume was 0%%; set card %s PCM to %s%%",
                selection.alsa_card,
                target,
            )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not repair ALSA playback volume: %s", exc)


def resample_audio(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Small dependency-free linear resampler for device compatibility."""
    if source_rate == target_rate or samples.size == 0:
        return samples

    frame_count = samples.shape[0]
    target_frames = max(1, int(round(frame_count * target_rate / source_rate)))
    source_positions = np.linspace(0.0, 1.0, num=frame_count, endpoint=False)
    target_positions = np.linspace(0.0, 1.0, num=target_frames, endpoint=False)

    if samples.ndim == 1:
        converted = np.interp(target_positions, source_positions, samples.astype(np.float32))
    else:
        channels = [
            np.interp(target_positions, source_positions, samples[:, channel].astype(np.float32))
            for channel in range(samples.shape[1])
        ]
        converted = np.column_stack(channels)

    if np.issubdtype(samples.dtype, np.integer):
        info = np.iinfo(samples.dtype)
        return np.clip(converted, info.min, info.max).astype(samples.dtype)
    return converted.astype(samples.dtype)


def _alsa_card(name: str) -> int | None:
    match = _ALSA_HW_PATTERN.search(name)
    return int(match.group(1)) if match else None


def _device_identity(name: str) -> str:
    return name.split("(hw:", 1)[0].strip().casefold()


def _valid_index(value: object, device_count: int) -> int | None:
    try:
        index = int(value)
    except (TypeError, ValueError):
        return None
    return index if 0 <= index < device_count else None
