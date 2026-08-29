from __future__ import annotations

import logging
import time

from pallattu_ai_assistant.ports import (
    AudioOutputPort,
    MetricsPort,
    PerceptionPort,
    VoiceAIPort,
    WakeAcknowledgementPort,
)

logger = logging.getLogger(__name__)


class AssistantApp:
    """Portable application core: wake -> acknowledge -> listen -> think -> speak."""

    def __init__(
        self,
        perception: PerceptionPort,
        voice_ai: VoiceAIPort,
        audio_output: AudioOutputPort,
        metrics: MetricsPort,
        follow_up_seconds: float,
        wake_acknowledgement: WakeAcknowledgementPort | None = None,
    ) -> None:
        self.perception = perception
        self.voice_ai = voice_ai
        self.audio_output = audio_output
        self.metrics = metrics
        self.follow_up_seconds = follow_up_seconds
        self.wake_acknowledgement = wake_acknowledgement

    def run_forever(self) -> None:
        self.perception.start()
        logger.info("Assistant ready; waiting for wake word")
        try:
            while True:
                self.perception.wait_for_wake_word()
                logger.info("Wake word detected")
                if self.wake_acknowledgement is not None:
                    self.wake_acknowledgement.acknowledge()
                self._run_conversation()
        except KeyboardInterrupt:
            logger.info("Stopping assistant")
        finally:
            self.perception.close()

    def _run_conversation(self) -> None:
        start_timeout = 5.0
        while True:
            captured = self.perception.capture_utterance(start_timeout)
            if captured is None:
                logger.info("No follow-up speech; returning to wake-word mode")
                return

            started = time.monotonic()
            try:
                reply = self.voice_ai.handle(captured.audio)
                if not reply.transcript:
                    start_timeout = self.follow_up_seconds
                    continue

                logger.info("User: %s", reply.transcript)
                logger.info("Assistant: %s", reply.text)
                self.audio_output.play(reply.audio)
                self.metrics.record(reply, captured, time.monotonic() - started)
            except Exception:
                logger.exception("Interaction failed; returning to wake-word mode")
                return

            start_timeout = self.follow_up_seconds
