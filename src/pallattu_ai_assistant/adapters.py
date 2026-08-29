from __future__ import annotations

import io
import json
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from pallattu_ai_assistant.audio_device import (
    AudioOutputSelection,
    prepare_audio_output,
    resample_audio,
    resolve_audio_output,
)
from pallattu_ai_assistant.domain import AssistantReply, AudioBuffer, CapturedUtterance


class SoundDeviceAudioOutputAdapter:
    """Play through a compatible output device; optional gain is applied before playback."""

    def __init__(
        self,
        gain: float = 1.0,
        selection: AudioOutputSelection | None = None,
    ) -> None:
        self.gain = gain
        self.selection = selection or resolve_audio_output()
        prepare_audio_output(self.selection)

    def play(self, audio: AudioBuffer) -> None:
        if not audio.data:
            return
        with wave.open(io.BytesIO(audio.data), "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            samples = np.frombuffer(frames, dtype=np.int16)
            if channels > 1:
                samples = samples.reshape(-1, channels)

            if self.gain != 1.0:
                amplified = samples.astype(np.float32) * self.gain
                samples = np.clip(amplified, -32768, 32767).astype(np.int16)

            playback_rate = self.selection.sample_rate
            samples = resample_audio(samples, sample_rate, playback_rate)
            sd.play(
                samples,
                samplerate=playback_rate,
                device=self.selection.device_index,
            )
            sd.wait()


class JsonlMetricsAdapter:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(
        self,
        reply: AssistantReply,
        captured: CapturedUtterance,
        elapsed_seconds: float,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.time(),
            "audio_seconds": round(captured.duration_seconds, 3),
            "input_tokens": reply.input_tokens,
            "output_tokens": reply.output_tokens,
            "interaction_seconds": round(elapsed_seconds, 3),
            "transcription_seconds": round(reply.transcription_seconds, 3),
            "reasoning_seconds": round(reply.reasoning_seconds, 3),
            "synthesis_seconds": round(reply.synthesis_seconds, 3),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
