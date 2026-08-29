from pallattu_ai_assistant.config import load_settings


def test_default_settings(monkeypatch):
    monkeypatch.delenv("PALLATTU_LOG_LEVEL", raising=False)
    monkeypatch.delenv("PALLATTU_AUDIO_INPUT_DEVICE", raising=False)
    monkeypatch.delenv("PALLATTU_AUDIO_OUTPUT_DEVICE", raising=False)
    monkeypatch.delenv("PALLATTU_WAKE_WORD", raising=False)

    settings = load_settings()

    assert settings.log_level == "INFO"
    assert settings.audio_input_device is None
    assert settings.audio_output_device is None
    assert settings.wake_word == "pallattu"
