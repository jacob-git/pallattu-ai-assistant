from __future__ import annotations

import io
import time

from openai import OpenAI

from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.domain import AssistantReply, AudioBuffer


class OpenAIVoiceAdapter:
    """OpenAI STT -> reasoning -> TTS adapter. No OS or filesystem dependency."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.history: list[dict[str, str]] = []

    def handle(self, audio: AudioBuffer) -> AssistantReply:
        transcript, transcription_seconds = self._transcribe(audio)
        if not transcript:
            return AssistantReply(transcript="", text="", audio=AudioBuffer(b"", 24000))

        text, input_tokens, output_tokens, reasoning_seconds = self._respond(transcript)
        speech, synthesis_seconds = self._synthesize(text)
        return AssistantReply(
            transcript=transcript,
            text=text,
            audio=speech,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            transcription_seconds=transcription_seconds,
            reasoning_seconds=reasoning_seconds,
            synthesis_seconds=synthesis_seconds,
        )

    def _transcribe(self, audio: AudioBuffer) -> tuple[str, float]:
        started = time.monotonic()
        audio_file = io.BytesIO(audio.data)
        audio_file.name = "utterance.wav"
        result = self.client.audio.transcriptions.create(
            model=self.settings.transcription_model,
            file=audio_file,
        )
        return result.text.strip(), time.monotonic() - started

    def _respond(self, transcript: str) -> tuple[str, int, int, float]:
        started = time.monotonic()
        response = self.client.responses.create(
            model=self.settings.llm_model,
            input=[
                {"role": "system", "content": self.settings.system_prompt},
                *self.history[-8:],
                {"role": "user", "content": transcript},
            ],
            reasoning={"effort": "none"},
            max_output_tokens=220,
        )
        text = response.output_text.strip()
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        self.history.extend(
            [
                {"role": "user", "content": transcript},
                {"role": "assistant", "content": text},
            ]
        )
        return text, input_tokens, output_tokens, time.monotonic() - started

    def _synthesize(self, text: str) -> tuple[AudioBuffer, float]:
        started = time.monotonic()
        response = self.client.audio.speech.create(
            model=self.settings.tts_model,
            voice=self.settings.tts_voice,
            input=text,
            response_format="wav",
        )
        data = response.read()
        return AudioBuffer(data=data, sample_rate=24000), time.monotonic() - started
