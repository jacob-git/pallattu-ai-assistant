from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeviceCapabilities:
    platform_name: str
    architecture: str
    model: str | None
    is_raspberry_pi: bool
    thermal_zone: Path | None
    gpio_chips: tuple[Path, ...]

    @property
    def has_temperature(self) -> bool:
        return self.thermal_zone is not None

    @property
    def has_gpio(self) -> bool:
        return bool(self.gpio_chips)


def discover_device_capabilities() -> DeviceCapabilities:
    model = _read_first_existing(
        [
            Path("/proc/device-tree/model"),
            Path("/sys/firmware/devicetree/base/model"),
        ]
    )
    normalized_model = (model or "").lower()
    is_raspberry_pi = "raspberry pi" in normalized_model

    thermal_zone = _first_existing(
        [
            Path("/sys/class/thermal/thermal_zone0/temp"),
        ]
    )
    gpio_chips = tuple(sorted(Path("/dev").glob("gpiochip*"))) if is_raspberry_pi else ()

    return DeviceCapabilities(
        platform_name=platform.system(),
        architecture=platform.machine(),
        model=model,
        is_raspberry_pi=is_raspberry_pi,
        thermal_zone=thermal_zone if is_raspberry_pi else None,
        gpio_chips=gpio_chips,
    )


def read_temperature_celsius(path: Path) -> float:
    raw = path.read_text(encoding="utf-8").strip()
    value = float(raw)
    if value > 1_000:
        value /= 1_000
    return round(value, 1)


def _first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _read_first_existing(paths: list[Path]) -> str | None:
    for path in paths:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8", errors="ignore").strip("\x00\n ")
        except OSError:
            continue
    return None
