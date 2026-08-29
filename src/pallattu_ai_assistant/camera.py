from __future__ import annotations

import importlib.util
import tempfile
import time
from pathlib import Path

from pallattu_ai_assistant.device import discover_device_capabilities
from pallattu_ai_assistant.domain import ImageFrame


class UnavailableVisionAdapter:
    def available(self) -> bool:
        return False

    def describe_source(self) -> str:
        return "no supported camera detected"

    def capture(self) -> ImageFrame:
        raise RuntimeError("No supported camera is available on this device.")


class RaspberryPiCameraAdapter:
    """Picamera2-backed still-image adapter, loaded only on Raspberry Pi."""

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self.width = width
        self.height = height

    def available(self) -> bool:
        capabilities = discover_device_capabilities()
        return capabilities.is_raspberry_pi and importlib.util.find_spec("picamera2") is not None

    def describe_source(self) -> str:
        return "Raspberry Pi camera via Picamera2"

    def capture(self) -> ImageFrame:
        if not self.available():
            raise RuntimeError(
                "Raspberry Pi camera support requires a detected Pi camera and Picamera2."
            )

        from picamera2 import Picamera2  # type: ignore[import-not-found]

        camera = Picamera2()
        try:
            configuration = camera.create_still_configuration(
                main={"size": (self.width, self.height)}
            )
            camera.configure(configuration)
            camera.start()
            time.sleep(0.5)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temporary:
                image_path = Path(temporary.name)
            try:
                camera.capture_file(str(image_path))
                data = image_path.read_bytes()
            finally:
                image_path.unlink(missing_ok=True)
        finally:
            camera.stop()
            camera.close()

        if not data:
            raise RuntimeError("Camera returned an empty image.")
        return ImageFrame(
            data=data,
            media_type="image/jpeg",
            width=self.width,
            height=self.height,
            source=self.describe_source(),
        )


def build_vision_adapter():
    raspberry_pi = RaspberryPiCameraAdapter()
    if raspberry_pi.available():
        return raspberry_pi
    return UnavailableVisionAdapter()
