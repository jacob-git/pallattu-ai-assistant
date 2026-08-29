from __future__ import annotations

import base64
from typing import Any

from openai import OpenAI

from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.domain import ImageFrame
from pallattu_ai_assistant.ports import VisionAnalysisPort, VisionPort


class OpenAIVisionAnalysisAdapter:
    """Analyze a captured still frame without exposing camera control to the model."""

    def __init__(self, settings: Settings) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def analyze(self, frame: ImageFrame, prompt: str) -> str:
        encoded = base64.b64encode(frame.data).decode("ascii")
        image_url = f"data:{frame.media_type};base64,{encoded}"
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Analyze this current camera frame. Be concrete and concise. "
                                f"User request: {prompt}"
                            ),
                        },
                        {"type": "input_image", "image_url": image_url},
                    ],
                }
            ],
            max_output_tokens=220,
        )
        text = response.output_text.strip()
        return text or "I couldn't determine what is visible in the camera frame."


class VisionToolAdapter:
    """Typed, read-only camera tools for the assistant."""

    def __init__(self, camera: VisionPort, analyzer: VisionAnalysisPort) -> None:
        self.camera = camera
        self.analyzer = analyzer

    def definitions(self) -> list[dict[str, Any]]:
        definitions: list[dict[str, Any]] = [
            {
                "type": "function",
                "name": "camera_status",
                "description": "Report whether a supported camera is available on this device.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        ]
        if self.camera.available():
            definitions.append(
                {
                    "type": "function",
                    "name": "look_at_scene",
                    "description": (
                        "Capture one current camera frame and answer a question about what is visible. "
                        "This is read-only and does not continuously record video."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "What to determine from the current camera frame.",
                            }
                        },
                        "required": ["question"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            )
        return definitions

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "camera_status":
            return {
                "ok": True,
                "available": self.camera.available(),
                "source": self.camera.describe_source(),
            }
        if name == "look_at_scene" and self.camera.available():
            question = str(arguments.get("question", "What is visible?")).strip()
            try:
                frame = self.camera.capture()
                description = self.analyzer.analyze(frame, question)
            except (OSError, RuntimeError, ValueError) as exc:
                return {"ok": False, "error": f"Camera analysis failed: {exc}"}
            return {
                "ok": True,
                "source": frame.source,
                "description": description,
            }
        return {"ok": False, "error": f"Unknown or unavailable vision tool: {name}"}
