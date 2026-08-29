from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import tempfile
import time

from openai import OpenAI

from pallattu_ai_assistant.config import Settings


@dataclass(frozen=True)
class PipelineResult:
    transcript: str
    response_text: str
    llm_input_tokens: int
    llm_output_tokens: int
    transcription_seconds: float
    reasoning_seconds: float
    tts_seconds: float


class OpenAIVoicePipeline:
    """Speech-to-text -> low-cost reasoning -> text-to-speech."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.history: list[dict[str, str]] = []

    def transcribe(self, wav_bytes: bytes) -> tuple[str, float]:
        started = time.monotonic()
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "utterance.wav"
        result = self.client.audio.transcriptions.create(
            model=self.settings.transcription_model,
            file=audio_file,
        )
        return result.text.strip(), time.monotonic() - started

    def respond(self, transcript: str) -> tuple[str, int, int, float]:
        started = time.monotonic()
        messages = [
            {"role": "system", "content": self.settings.system_prompt},
            *self.history[-8:],
            {"role": "user", "content": transcript},
        ]
        response = self.client.responses.create(
            model=self.settings.llm_model,
            input=messages,
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

    def synthesize_to_file(self, text: str, output_path: Path) -> float:
        started = time.monotonic()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.client.audio.speech.with_streaming_response.create(
            model=self.settings.tts_model,
            voice=self.settings.tts_voice,
            input=text,
            response_format="wav",
        ) as response:
            response.stream_to_file(output_path)
        return time.monotonic() - started

    def run(self, wav_bytes: bytes) -> tuple[PipelineResult, Path]:
        transcript, transcription_seconds = self.transcribe(wav_bytes)
        response_text, input_tokens, output_tokens, reasoning_seconds = self.respond(transcript)

        temp_dir = Path(tempfile.gettempdir()) / "pallattu-ai-assistant"
        output_path = temp_dir / "response.wav"
        tts_seconds = self.synthesize_to_file(response_text, output_path)

        return (
            PipelineResult(
                transcript=transcript,
                response_text=response_text,
                llm_input_tokens=input_tokens,
                llm_output_tokens=output_tokens,
                transcription_seconds=transcription_seconds,
                reasoning_seconds=reasoning_seconds,
                tts_seconds=tts_seconds,
            ),
            output_path,
        )
