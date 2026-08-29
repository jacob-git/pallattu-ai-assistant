from __future__ import annotations

import io
import math
import struct
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import openwakeword
import sounddevice as sd
import webrtcvad
from openwakeword.model import Model
from pysilero_vad import SileroVoiceActivityDetector

from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.domain import AudioBuffer, CapturedUtterance


SAMPLE_RATE = 16_000
WAKE_FRAME_SAMPLES = 1_280  # 80 ms; recommended by openWakeWord for streaming.


class _SileroVad:
    def __init__(self, threshold: float) -> None:
        self.detector = SileroVoiceActivityDetector()
        self.threshold = threshold
        self.frame_samples = self.detector.chunk_samples()

    def is_speech(self, samples: np.ndarray) -> bool:
        return float(self.detector(samples.astype(np.int16).tobytes())) >= self.threshold


class _WebRtcVad:
    def __init__(self, mode: int) -> None:
        self.detector = webrtcvad.Vad(mode)
        self.frame_samples = 480  # 30 ms at 16 kHz.

    def is_speech(self, samples: np.ndarray) -> bool:
        return bool(self.detector.is_speech(samples.astype(np.int16).tobytes(), SAMPLE_RATE))


class OpenWakeWordPerceptionAdapter:
    """Portable local microphone, openWakeWord activation, and selectable VAD."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = self._create_wake_model()
        self.target_model = self._resolve_target_model()
        self.vad = self._create_vad()
        device = None if settings.audio_input_device_index < 0 else settings.audio_input_device_index
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            device=device,
        )

    def _create_wake_model(self) -> Model:
        if self.settings.wake_word_model:
            model_path = self.settings.wake_word_model
            framework = "tflite" if model_path.suffix.lower() == ".tflite" else "onnx"
            return Model(wakeword_models=[str(model_path)], inference_framework=framework)

        model_key = _model_key(self.settings.wake_model)
        model_info = openwakeword.MODELS.get(model_key)
        if model_info is None:
            available = ", ".join(sorted(openwakeword.MODELS.keys()))
            raise RuntimeError(
                f"Wake model '{self.settings.wake_model}' is not available. "
                f"Choose one of: {available}"
            )

        model_path = Path(model_info["model_path"])
        if not model_path.exists():
            openwakeword.utils.download_models([model_path.stem])

        if not model_path.exists():
            raise RuntimeError(
                f"openWakeWord model download completed but the model is still missing: {model_path}"
            )

        return Model(wakeword_models=[str(model_path)], inference_framework="tflite")

    def _resolve_target_model(self) -> str:
        names = list(self.model.models.keys())
        if len(names) == 1:
            return names[0]
        normalized_target = _normalize(self.settings.wake_model)
        for name in names:
            if normalized_target in _normalize(name):
                return name
        raise RuntimeError(f"Could not resolve wake model '{self.settings.wake_model}'")

    def _create_vad(self):
        if self.settings.vad_engine == "webrtc":
            return _WebRtcVad(self.settings.webrtc_vad_mode)
        return _SileroVad(self.settings.vad_threshold)

    def start(self) -> None:
        self.stream.start()

    def close(self) -> None:
        try:
            self.stream.stop()
        finally:
            self.stream.close()

    def wait_for_wake_word(self) -> None:
        self.model.reset()
        while True:
            frame = self._read(WAKE_FRAME_SAMPLES)
            prediction = self.model.predict(frame)
            if float(prediction.get(self.target_model, 0.0)) >= self.settings.wake_threshold:
                return

    def capture_utterance(self, start_timeout_seconds: float) -> CapturedUtterance | None:
        frame_samples = self.vad.frame_samples
        frame_seconds = frame_samples / SAMPLE_RATE
        pre_roll_frames = max(1, math.ceil(0.3 / frame_seconds))
        pre_roll: deque[np.ndarray] = deque(maxlen=pre_roll_frames)
        frames: list[np.ndarray] = []
        heard_speech = False
        silence_frames = 0
        end_silence_frames = max(
            1, math.ceil(self.settings.end_silence_seconds / frame_seconds)
        )
        start_deadline = time.monotonic() + start_timeout_seconds
        max_frames = max(
            1, math.ceil(self.settings.max_utterance_seconds / frame_seconds)
        )

        while len(frames) < max_frames:
            frame = self._read(frame_samples)
            speech = self.vad.is_speech(frame)

            if not heard_speech:
                pre_roll.append(frame)
                if speech:
                    heard_speech = True
                    frames.extend(pre_roll)
                elif time.monotonic() >= start_deadline:
                    return None
                continue

            frames.append(frame)
            if speech:
                silence_frames = 0
            else:
                silence_frames += 1
                if silence_frames >= end_silence_frames:
                    break

        if not frames:
            return None

        samples = np.concatenate(frames).astype(np.int16)
        wav_bytes = _pcm_to_wav(samples)
        return CapturedUtterance(
            audio=AudioBuffer(data=wav_bytes, sample_rate=SAMPLE_RATE, channels=1, sample_width=2),
            duration_seconds=len(samples) / SAMPLE_RATE,
        )

    def _read(self, sample_count: int) -> np.ndarray:
        data, overflowed = self.stream.read(sample_count)
        if overflowed:
            pass
        return np.asarray(data, dtype=np.int16).reshape(-1)


def _pcm_to_wav(samples: np.ndarray) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples.tolist()))
    return output.getvalue()


def _normalize(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _model_key(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "jarvis": "hey_jarvis",
        "mycroft": "hey_mycroft",
        "rhasspy": "hey_rhasspy",
    }
    return aliases.get(normalized, normalized)
