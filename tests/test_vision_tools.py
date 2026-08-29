from pallattu_ai_assistant.domain import ImageFrame
from pallattu_ai_assistant.vision_tools import VisionToolAdapter


class FakeCamera:
    def __init__(self, available=True):
        self._available = available

    def available(self):
        return self._available

    def describe_source(self):
        return "fake camera"

    def capture(self):
        return ImageFrame(data=b"jpeg", source="fake camera")


class FakeAnalyzer:
    def analyze(self, frame, prompt):
        assert frame.data == b"jpeg"
        return f"scene: {prompt}"


def test_scene_tool_is_exposed_only_when_camera_is_available():
    available = VisionToolAdapter(FakeCamera(True), FakeAnalyzer())
    unavailable = VisionToolAdapter(FakeCamera(False), FakeAnalyzer())

    assert {item["name"] for item in available.definitions()} == {
        "camera_status",
        "look_at_scene",
    }
    assert {item["name"] for item in unavailable.definitions()} == {"camera_status"}


def test_scene_tool_captures_and_analyzes_one_frame():
    tools = VisionToolAdapter(FakeCamera(True), FakeAnalyzer())

    result = tools.execute("look_at_scene", {"question": "What is on the table?"})

    assert result == {
        "ok": True,
        "source": "fake camera",
        "description": "scene: What is on the table?",
    }
