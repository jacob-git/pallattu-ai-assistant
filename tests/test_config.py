from pallattu_ai_assistant.config import load_settings, validate_settings


def test_default_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PALLATTU_WAKE_WORD_MODEL", raising=False)
    monkeypatch.delenv("PALLATTU_WAKE_MODEL", raising=False)
    monkeypatch.delenv("PALLATTU_VAD_ENGINE", raising=False)

    settings = load_settings()

    assert settings.wake_model == "hey jarvis"
    assert settings.wake_word_model is None
    assert settings.vad_engine == "silero"
    assert settings.llm_model == "gpt-5.6-luna"
    assert settings.transcription_model == "gpt-4o-mini-transcribe"
    assert settings.tts_model == "gpt-4o-mini-tts"
    assert validate_settings(settings) == ["OPENAI_API_KEY is required"]


def test_webrtc_vad_can_be_selected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("PALLATTU_VAD_ENGINE", "webrtc")
    monkeypatch.setenv("PALLATTU_WEBRTC_VAD_MODE", "3")

    settings = load_settings()

    assert settings.vad_engine == "webrtc"
    assert settings.webrtc_vad_mode == 3
    assert validate_settings(settings) == []
