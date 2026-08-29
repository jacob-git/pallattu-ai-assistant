from __future__ import annotations

import io
import json
import time

from openai import OpenAI

from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.domain import AssistantReply, AudioBuffer
from pallattu_ai_assistant.ports import MemoryPort, ToolPort


class OpenAIVoiceAdapter:
    """OpenAI STT -> reasoning/tool use -> TTS adapter with persistent memory."""

    def __init__(self, settings: Settings, tools: ToolPort, memory: MemoryPort) -> None:
        self.settings = settings
        self.tools = tools
        self.memory = memory
        self.client = OpenAI(api_key=settings.openai_api_key)

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
        tool_definitions = self.tools.definitions()
        recent_history = self.memory.recent_messages(limit=8)
        relevant_memories = self.memory.search(transcript, limit=5)

        input_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.settings.system_prompt}
        ]
        if relevant_memories:
            memory_context = "\n".join(f"- {memory}" for memory in relevant_memories)
            input_messages.append(
                {
                    "role": "system",
                    "content": (
                        "Relevant long-term memories from this user's local memory store:\n"
                        f"{memory_context}\n"
                        "Use them only when they help answer the current request."
                    ),
                }
            )
        input_messages.extend(recent_history)
        input_messages.append({"role": "user", "content": transcript})

        response = self.client.responses.create(
            model=self.settings.llm_model,
            input=input_messages,
            tools=tool_definitions,
            tool_choice="auto",
            reasoning={"effort": "none"},
            max_output_tokens=220,
        )

        input_tokens, output_tokens = _usage(response)
        tool_rounds = 0
        while tool_rounds < 4:
            calls = [item for item in response.output if getattr(item, "type", "") == "function_call"]
            if not calls:
                break

            tool_rounds += 1
            tool_outputs = []
            for call in calls:
                try:
                    arguments = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                result = self.tools.execute(call.name, arguments)
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result),
                    }
                )

            response = self.client.responses.create(
                model=self.settings.llm_model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tool_definitions,
                tool_choice="auto",
                reasoning={"effort": "none"},
                max_output_tokens=220,
            )
            turn_input, turn_output = _usage(response)
            input_tokens += turn_input
            output_tokens += turn_output

        text = response.output_text.strip()
        if not text:
            text = "I couldn't complete that request."

        self.memory.append_message("user", transcript)
        self.memory.append_message("assistant", text)
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


def _usage(response) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    return (
        int(getattr(usage, "input_tokens", 0) or 0),
        int(getattr(usage, "output_tokens", 0) or 0),
    )
