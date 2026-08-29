from __future__ import annotations

import shutil
from pathlib import Path

DEFAULT_WAKE_PHRASE = "Hey Pal"
DEFAULT_CUSTOM_WAKE_MODEL = (
    Path.home() / ".pallattu-ai-assistant" / "models" / "hey-pal.tflite"
)


def resolve_custom_wake_model(explicit: Path | None) -> Path | None:
    """Use an explicit custom model first, otherwise auto-enable the standard Hey Pal model."""
    if explicit is not None:
        return explicit.expanduser()
    if DEFAULT_CUSTOM_WAKE_MODEL.exists():
        return DEFAULT_CUSTOM_WAKE_MODEL
    return None


def install_custom_wake_model(source: Path) -> Path:
    source = source.expanduser()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Wake-word model not found: {source}")
    if source.suffix.lower() != ".tflite":
        raise ValueError("The standard Hey Pal wake-word model must be a .tflite file")

    DEFAULT_CUSTOM_WAKE_MODEL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, DEFAULT_CUSTOM_WAKE_MODEL)
    return DEFAULT_CUSTOM_WAKE_MODEL


def wake_status(explicit: Path | None, fallback_model: str) -> dict[str, str | bool]:
    custom = resolve_custom_wake_model(explicit)
    ready = custom is not None and custom.exists()
    return {
        "target_phrase": DEFAULT_WAKE_PHRASE,
        "custom_model_ready": ready,
        "custom_model_path": str(custom or DEFAULT_CUSTOM_WAKE_MODEL),
        "active_mode": "custom" if ready else "fallback",
        "active_wake": DEFAULT_WAKE_PHRASE if ready else fallback_model,
    }
