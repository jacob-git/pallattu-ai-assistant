from pallattu_ai_assistant.app import AssistantApp
from pallattu_ai_assistant.domain import AssistantReply, AudioBuffer, CapturedUtterance


class FakePerception:
    def __init__(self):
        self.started = False
        self.closed = False
        self.capture_calls = 0

    def start(self):
        self.started = True

    def close(self):
        self.closed = True

    def wait_for_wake_word(self):
        raise KeyboardInterrupt

    def capture_utterance(self, start_timeout_seconds):
        self.capture_calls += 1
        if self.capture_calls == 1:
            return CapturedUtterance(AudioBuffer(b"wav", 16000), 1.0)
        return None


class FakeVoiceAI:
    def handle(self, audio):
        return AssistantReply(
            transcript="hello",
            text="Hi there.",
            audio=AudioBuffer(b"reply", 24000),
        )


class FakeOutput:
    def __init__(self):
        self.played = []

    def play(self, audio):
        self.played.append(audio)


class FakeMetrics:
    def __init__(self):
        self.records = []

    def record(self, reply, captured, elapsed_seconds):
        self.records.append((reply, captured, elapsed_seconds))


def test_core_conversation_uses_only_ports():
    perception = FakePerception()
    output = FakeOutput()
    metrics = FakeMetrics()
    app = AssistantApp(perception, FakeVoiceAI(), output, metrics, follow_up_seconds=10)

    app._run_conversation()

    assert len(output.played) == 1
    assert len(metrics.records) == 1
