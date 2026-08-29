from pallattu_ai_assistant import wake_ack


def test_macos_uses_local_say(monkeypatch):
    monkeypatch.setattr(wake_ack.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(wake_ack.shutil, "which", lambda name: "/usr/bin/say" if name == "say" else None)

    assert wake_ack._local_tts_command("I'm listening.") == ["say", "I'm listening."]


def test_linux_prefers_espeak_ng(monkeypatch):
    monkeypatch.setattr(wake_ack.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        wake_ack.shutil,
        "which",
        lambda name: "/usr/bin/espeak-ng" if name == "espeak-ng" else None,
    )

    assert wake_ack._local_tts_command("I'm listening.") == [
        "/usr/bin/espeak-ng",
        "I'm listening.",
    ]


def test_missing_local_tts_returns_none(monkeypatch):
    monkeypatch.setattr(wake_ack.platform, "system", lambda: "Linux")
    monkeypatch.setattr(wake_ack.shutil, "which", lambda _name: None)

    assert wake_ack._local_tts_command("I'm listening.") is None
