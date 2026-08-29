from __future__ import annotations

from collections import deque
import io
import math
import struct
import time
import wave

import pvcobra
import pvporcupine
from pvrecorder import PvRecorder

from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.domain import AudioBuffer, CapturedUtterance


class PicovoicePerceptionAdapter:
    """Portable wake-word + VAD adapter backed by Picovoice."""

    def __init__(self, settings: Settings) -> None:
        if settings.wake_word_model:
            self.porcupine = pvporcupine.create(
                access_key=settings.picovoice_access_key,
                keyword_paths=[str(settings.wake_word_model)],
            )
        else:
            self.porcupine = pvporcupine.create(
                access_key=settings.picovoice_access_key,
                keywords=[settings.wake_keyword],
            )

        self.cobra = pvcobra.create(access_key=settings.picovoice_access_key)
        if self.porcupine.sample_rate != self.cobra.sample_rate:
            raise RuntimeError("Wake-word and VAD engines use different sample rates")
        if self.porcupine.frame_length != self.cobra.frame_length:
            raise RuntimeError("Wake-word and VAD engines use different frame lengths")

        self.settings = settings
        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length
        self.frame_seconds = self.frame_length / self.sample_rate
        self.recorder = PvRecorder(
            frame_length=self.frame_length,
            device_index=settings.audio_input_device_index,
        )

    def start(self) -> None:
        self.recorder.start()

    def close(self) -> None:
        try:
            self.recorder.stop()
        finally:
            self.recorder.delete()
            self.porcupine.delete()
            self.cobra.delete()

    def wait_for_wake_word(self) -> None:
        while True:
            if self.porcupine.process(self.recorder.read()) >= 0:
                return

    def capture_utterance(self, start_timeout_seconds: float) -> CapturedUtterance | None:
        pre_roll_frames = max(1, math.ceil(0.25 / self.frame_seconds))
        pre_roll: deque[list[int]] = deque(maxlen=pre_roll_frames)
        frames: list[list[int]] = []
        heard_speech = False
        silence_frames = 0
        end_silence_frames = max(
            1, math.ceil(self.settings.end_silence_seconds / self.frame_seconds)
        )
        start_deadline = time.monotonic() + start_timeout_seconds
        max_frames = max(
            1, math.ceil(self.settings.max_utterance_seconds / self.frame_seconds)
        )

        while len(frames) < max_frames:
            frame = self.recorder.read()
            probability = self.cobra.process(frame)
            if not heard_speech:
                pre_roll.append(frame)
                if probability >= self.settings.vad_threshold:
                    heard_speech = True
                    frames.extend(pre_roll)
                elif time.monotonic() >= start_deadline:
                    return None
                continue

            frames.append(frame)
            if probability >= self.settings.vad_threshold:
                silence_frames = 0
            else:
                silence_frames += 1
                if silence_frames >= end_silence_frames:
                    break

        if not frames:
            return None

        samples = [sample for frame in frames for sample in frame]
        wav_bytes = self._pcm_to_wav(samples)
        return CapturedUtterance(
            audio=AudioBuffer(data=wav_bytes, sample_rate=self.sample_rate),
            duration_seconds=len(samples) / self.sample_rate,
        )

    def _pcm_to_wav(self, samples: list[int]) -> bytes:
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        return output.getvalue()
