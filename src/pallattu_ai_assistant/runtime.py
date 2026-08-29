from __future__ import annotations

from dataclasses import asdict
import json
import logging
from pathlib import Path
import subprocess
import time

from pallattu_ai_assistant.audio_runtime import LocalAudioRuntime
from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.openai_pipeline import OpenAIVoicePipeline, PipelineResult

logger = logging.getLogger(__name__)


class AssistantRuntime:
    """Wake -> listen -> think -> speak -> follow-up -> sleep."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.audio = LocalAudioRuntime(settings)
        self.pipeline = OpenAIVoicePipeline(settings)

    def run_forever(self) -> None:
        self.audio.start()
        logger.info("Assistant ready; waiting for wake word")
        try:
            while True:
                self.audio.wait_for_wake_word()
                logger.info("Wake word detected")
                self._conversation()
        except KeyboardInterrupt:
            logger.info("Stopping assistant")
        finally:
            self.audio.close()

    def _conversation(self) -> None:
        start_timeout = 5.0
        while True:
            captured = self.audio.capture_utterance(start_timeout_seconds=start_timeout)
            if captured is None:
                logger.info("No follow-up speech; returning to wake-word mode")
                return

            interaction_started = time.monotonic()
            try:
                result, speech_path = self.pipeline.run(captured.wav_bytes)
                if not result.transcript:
                    logger.info("Empty transcription; waiting for follow-up")
                    start_timeout = self.settings.follow_up_seconds
                    continue

                logger.info("User: %s", result.transcript)
                logger.info("Assistant: %s", result.response_text)
                self._play(speech_path)
                self._record_usage(result, captured.duration_seconds, interaction_started)
            except Exception:
                logger.exception("Interaction failed; returning to wake-word mode")
                return

            start_timeout = self.settings.follow_up_seconds

    def _play(self, path: Path) -> None:
        subprocess.run(["aplay", "-q", str(path)], check=True)

    def _record_usage(
        self,
        result: PipelineResult,
        audio_seconds: float,
        interaction_started: float,
    ) -> None:
        path = self.settings.metrics_path
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.time(),
            "audio_seconds": round(audio_seconds, 3),
            "transcription_model": self.settings.transcription_model,
            "llm_model": self.settings.llm_model,
            "tts_model": self.settings.tts_model,
            "llm_input_tokens": result.llm_input_tokens,
            "llm_output_tokens": result.llm_output_tokens,
            "response_characters": len(result.response_text),
            "interaction_seconds": round(time.monotonic() - interaction_started, 3),
            **{
                key: round(value, 3) if isinstance(value, float) else value
                for key, value in asdict(result).items()
                if key.endswith("_seconds")
            },
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
