from pallattu_ai_assistant.config import load_settings, validate_settings


def test_default_settings(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PICOVOICE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("PALLATTU_WAKE_WORD_MODEL", raising=False)
    monkeypatch.delenv("PALLATTU_WAKE_KEYWORD", raising=False)

    settings = load_settings()

    assert settings.wake_keyword == "porcupine"
    assert settings.wake_word_model is None
    assert settings.llm_model == "gpt-5.6-luna"
    assert settings.transcription_model == "gpt-4o-mini-transcribe"
    assert settings.tts_model == "gpt-4o-mini-tts"
    assert validate_settings(settings) == [
        "OPENAI_API_KEY is required",
        "PICOVOICE_ACCESS_KEY is required",
    ]
