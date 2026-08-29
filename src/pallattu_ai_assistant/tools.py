from __future__ import annotations

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psutil

from pallattu_ai_assistant.device import (
    DeviceCapabilities,
    discover_device_capabilities,
    read_temperature_celsius,
)


class PortableToolRegistry:
    """Safe capabilities; device-specific tools are exposed only when supported."""

    def __init__(self, capabilities: DeviceCapabilities | None = None) -> None:
        self.capabilities = capabilities or discover_device_capabilities()

    def definitions(self) -> list[dict[str, Any]]:
        definitions = [
            {
                "type": "function",
                "name": "current_time",
                "description": (
                    "Get the current local date, time, and timezone of the device running "
                    "the assistant."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "weather",
                "description": (
                    "Get current weather for a city or named location. Use this for current "
                    "weather questions."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": (
                                "City and region, for example Sunnyvale, Texas or Dallas, TX"
                            ),
                        }
                    },
                    "required": ["location"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "system_status",
                "description": (
                    "Get safe health and status information about the computer running the assistant."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "device_capabilities",
                "description": (
                    "List safe hardware capabilities detected on the device running the assistant."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        ]

        if self.capabilities.is_raspberry_pi and self.capabilities.has_temperature:
            definitions.append(
                {
                    "type": "function",
                    "name": "device_temperature",
                    "description": "Read the Raspberry Pi processor temperature in Celsius.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            )

        if self.capabilities.is_raspberry_pi and self.capabilities.has_gpio:
            definitions.append(
                {
                    "type": "function",
                    "name": "gpio_status",
                    "description": (
                        "Read-only Raspberry Pi GPIO capability status. This never changes pin state."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            )

        return definitions

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "current_time":
                return self._current_time()
            if name == "weather":
                return self._weather(str(arguments.get("location", "")).strip())
            if name == "system_status":
                return self._system_status()
            if name == "device_capabilities":
                return self._device_capabilities()
            if name == "device_temperature" and self.capabilities.has_temperature:
                return self._device_temperature()
            if name == "gpio_status" and self.capabilities.has_gpio:
                return self._gpio_status()
            return {"ok": False, "error": f"Unknown or unavailable tool: {name}"}
        except (OSError, ValueError, TypeError, KeyError, psutil.Error) as exc:
            return {"ok": False, "error": f"{name} failed: {exc}"}

    @staticmethod
    def _current_time() -> dict[str, Any]:
        now = datetime.now().astimezone()
        display_time = (
            now.strftime("%-I:%M %p")
            if os.name != "nt"
            else now.strftime("%I:%M %p").lstrip("0")
        )
        return {
            "ok": True,
            "iso": now.isoformat(timespec="seconds"),
            "date": now.strftime("%A, %B %d, %Y"),
            "time": display_time,
            "timezone": now.tzname() or str(now.tzinfo),
        }

    def _weather(self, location: str) -> dict[str, Any]:
        if not location:
            return {"ok": False, "error": "A location is required for weather."}

        geocode = self._get_json(
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urlencode({"name": location, "count": 1, "language": "en", "format": "json"})
        )
        matches = geocode.get("results") or []
        if not matches:
            return {"ok": False, "error": f"Could not find weather location '{location}'."}

        place = matches[0]
        params = {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": (
                "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,"
                "weather_code,wind_speed_10m"
            ),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "auto",
        }
        forecast = self._get_json(
            "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
        )
        current = forecast.get("current") or {}
        resolved_name = ", ".join(
            part
            for part in [place.get("name"), place.get("admin1"), place.get("country")]
            if part
        )
        return {
            "ok": True,
            "location": resolved_name,
            "observed_at": current.get("time"),
            "temperature_f": current.get("temperature_2m"),
            "feels_like_f": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_in": current.get("precipitation"),
            "wind_mph": current.get("wind_speed_10m"),
            "condition": _weather_description(current.get("weather_code")),
            "source": "Open-Meteo",
        }

    @staticmethod
    def _system_status() -> dict[str, Any]:
        memory = psutil.virtual_memory()
        root = Path.home().anchor or "/"
        disk = psutil.disk_usage(root)
        battery = psutil.sensors_battery()
        result: dict[str, Any] = {
            "ok": True,
            "platform": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
        }
        if battery is not None:
            result["battery_percent"] = battery.percent
            result["power_plugged"] = battery.power_plugged
        return result

    def _device_capabilities(self) -> dict[str, Any]:
        return {
            "ok": True,
            "platform": self.capabilities.platform_name,
            "architecture": self.capabilities.architecture,
            "model": self.capabilities.model,
            "raspberry_pi": self.capabilities.is_raspberry_pi,
            "temperature_available": self.capabilities.has_temperature,
            "gpio_available": self.capabilities.has_gpio,
            "gpio_chip_count": len(self.capabilities.gpio_chips),
        }

    def _device_temperature(self) -> dict[str, Any]:
        if self.capabilities.thermal_zone is None:
            return {"ok": False, "error": "Temperature capability is unavailable."}
        temperature_c = read_temperature_celsius(self.capabilities.thermal_zone)
        return {
            "ok": True,
            "temperature_c": temperature_c,
            "temperature_f": round((temperature_c * 9 / 5) + 32, 1),
        }

    def _gpio_status(self) -> dict[str, Any]:
        chips = [
            {
                "path": str(path),
                "readable": os.access(path, os.R_OK),
                "writable": os.access(path, os.W_OK),
            }
            for path in self.capabilities.gpio_chips
        ]
        return {
            "ok": True,
            "mode": "read-only",
            "gpio_chip_count": len(chips),
            "gpio_chips": chips,
            "note": "No pin values are changed by this tool.",
        }

    @staticmethod
    def _get_json(url: str) -> dict[str, Any]:
        request = Request(url, headers={"User-Agent": "Pallattu-AI-Assistant/0.5"})
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))


def _weather_description(code: Any) -> str:
    descriptions = {
        0: "clear",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "fog",
        48: "rime fog",
        51: "light drizzle",
        53: "drizzle",
        55: "heavy drizzle",
        56: "light freezing drizzle",
        57: "freezing drizzle",
        61: "light rain",
        63: "rain",
        65: "heavy rain",
        66: "light freezing rain",
        67: "freezing rain",
        71: "light snow",
        73: "snow",
        75: "heavy snow",
        77: "snow grains",
        80: "light rain showers",
        81: "rain showers",
        82: "heavy rain showers",
        85: "light snow showers",
        86: "heavy snow showers",
        95: "thunderstorm",
        96: "thunderstorm with hail",
        99: "severe thunderstorm with hail",
    }
    try:
        return descriptions.get(int(code), "unknown")
    except (TypeError, ValueError):
        return "unknown"
