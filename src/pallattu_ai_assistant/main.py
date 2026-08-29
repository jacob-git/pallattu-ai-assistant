from __future__ import annotations

from pallattu_ai_assistant import __version__
from pallattu_ai_assistant.config import load_settings


def main() -> None:
    settings = load_settings()
    print(f"Pallattu AI Assistant v{__version__}")
    print("Current milestone: v0.1 Audio Foundation")
    print(f"Log level: {settings.log_level}")
    print(f"Wake word: {settings.wake_word}")
    print("Next: verify Raspberry Pi microphone and speaker devices.")


if __name__ == "__main__":
    main()
