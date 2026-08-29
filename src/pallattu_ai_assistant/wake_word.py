from __future__ import annotations

import shutil
from pathlib import Path

DEFAULT_WAKE_PHRASE = "Hey Pal"
DEFAULT_CUSTOM_WAKE_MODEL_ONNX = (
    Path.home() / ".pallattu-ai-assistant" / "models" / "hey-pal.onnx"
)
DEFAULT_CUSTOM_WAKE_MODEL_TFLITE = (
    Path.home() / ".pallattu-ai-assistant" / "models" / "hey-pal.tflite"
)
SUPPORTED_WAKE_MODEL_SUFFIXES = {".onnx", ".tflite"}


def resolve_custom_wake_model(explicit: Path | None) -> Path | None:
    """Use an explicit model first, otherwise prefer Hey Pal ONNX then TFLite."""
    if explicit is not None:
        return explicit.expanduser()
    if DEFAULT_CUSTOM_WAKE_MODEL_ONNX.exists():
        return DEFAULT_CUSTOM_WAKE_MODEL_ONNX
    if DEFAULT_CUSTOM_WAKE_MODEL_TFLITE.exists():
        return DEFAULT_CUSTOM_WAKE_MODEL_TFLITE
    return None


def install_custom_wake_model(source: Path) -> Path:
    source = source.expanduser()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Wake-word model not found: {source}")

    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_WAKE_MODEL_SUFFIXES:
        raise ValueError("Wake-word model must be a .onnx or .tflite file")

    destination = (
        DEFAULT_CUSTOM_WAKE_MODEL_ONNX
        if suffix == ".onnx"
        else DEFAULT_CUSTOM_WAKE_MODEL_TFLITE
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def wake_status(explicit: Path | None, fallback_model: str) -> dict[str, str | bool]:
    custom = resolve_custom_wake_model(explicit)
    ready = custom is not None and custom.exists()
    return {
        "target_phrase": DEFAULT_WAKE_PHRASE,
        "custom_model_ready": ready,
        "custom_model_path": str(custom or DEFAULT_CUSTOM_WAKE_MODEL_ONNX),
        "active_mode": "custom" if ready else "fallback",
        "active_wake": DEFAULT_WAKE_PHRASE if ready else fallback_model,
        "preferred_format": "onnx",
    }
