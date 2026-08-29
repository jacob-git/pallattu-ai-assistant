from pathlib import Path

from pallattu_ai_assistant.device import DeviceCapabilities
from pallattu_ai_assistant.tools import PortableToolRegistry, _weather_description


def _desktop_capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        platform_name="Darwin",
        architecture="arm64",
        model=None,
        is_raspberry_pi=False,
        thermal_zone=None,
        gpio_chips=(),
    )


def _pi_capabilities(tmp_path: Path) -> DeviceCapabilities:
    thermal = tmp_path / "temp"
    thermal.write_text("52000\n", encoding="utf-8")
    gpio0 = tmp_path / "gpiochip0"
    gpio0.write_text("", encoding="utf-8")
    gpio4 = tmp_path / "gpiochip4"
    gpio4.write_text("", encoding="utf-8")
    return DeviceCapabilities(
        platform_name="Linux",
        architecture="aarch64",
        model="Raspberry Pi 5 Model B Rev 1.0",
        is_raspberry_pi=True,
        thermal_zone=thermal,
        gpio_chips=(gpio0, gpio4),
    )


def test_desktop_tool_definitions_are_safe_function_tools():
    registry = PortableToolRegistry(_desktop_capabilities())
    definitions = registry.definitions()

    assert {tool["name"] for tool in definitions} == {
        "current_time",
        "weather",
        "system_status",
        "device_capabilities",
    }
    assert all(tool["type"] == "function" for tool in definitions)
    assert all(tool["strict"] is True for tool in definitions)
    assert all(tool["parameters"]["additionalProperties"] is False for tool in definitions)


def test_pi_registers_read_only_hardware_tools(tmp_path):
    registry = PortableToolRegistry(_pi_capabilities(tmp_path))
    names = {tool["name"] for tool in registry.definitions()}

    assert "device_temperature" in names
    assert "gpio_status" in names


def test_current_time_returns_local_time():
    result = PortableToolRegistry(_desktop_capabilities()).execute("current_time", {})

    assert result["ok"] is True
    assert result["time"]
    assert result["date"]
    assert result["timezone"]
    assert "T" in result["iso"]


def test_device_capabilities_describe_desktop():
    result = PortableToolRegistry(_desktop_capabilities()).execute("device_capabilities", {})

    assert result["ok"] is True
    assert result["platform"] == "Darwin"
    assert result["raspberry_pi"] is False
    assert result["temperature_available"] is False
    assert result["gpio_available"] is False


def test_pi_temperature_is_read_only(tmp_path):
    registry = PortableToolRegistry(_pi_capabilities(tmp_path))
    result = registry.execute("device_temperature", {})

    assert result == {"ok": True, "temperature_c": 52.0, "temperature_f": 125.6}


def test_pi_gpio_status_only_reports_capabilities(tmp_path):
    registry = PortableToolRegistry(_pi_capabilities(tmp_path))
    result = registry.execute("gpio_status", {})

    assert result["ok"] is True
    assert result["mode"] == "read-only"
    assert result["gpio_chip_count"] == 2
    assert len(result["gpio_chips"]) == 2


def test_unavailable_pi_tool_is_rejected_on_desktop():
    result = PortableToolRegistry(_desktop_capabilities()).execute("gpio_status", {})

    assert result == {"ok": False, "error": "Unknown or unavailable tool: gpio_status"}


def test_weather_uses_geocoding_and_current_conditions(monkeypatch):
    registry = PortableToolRegistry(_desktop_capabilities())
    responses = iter(
        [
            {
                "results": [
                    {
                        "name": "Sunnyvale",
                        "admin1": "Texas",
                        "country": "United States",
                        "latitude": 32.80,
                        "longitude": -96.56,
                    }
                ]
            },
            {
                "current": {
                    "time": "2026-08-29T09:00",
                    "temperature_2m": 84.2,
                    "apparent_temperature": 87.1,
                    "relative_humidity_2m": 61,
                    "precipitation": 0.0,
                    "weather_code": 1,
                    "wind_speed_10m": 7.4,
                }
            },
        ]
    )
    monkeypatch.setattr(registry, "_get_json", lambda _url: next(responses))

    result = registry.execute("weather", {"location": "Sunnyvale, Texas"})

    assert result["ok"] is True
    assert result["location"] == "Sunnyvale, Texas, United States"
    assert result["temperature_f"] == 84.2
    assert result["condition"] == "mainly clear"
    assert result["source"] == "Open-Meteo"


def test_weather_requires_location():
    result = PortableToolRegistry(_desktop_capabilities()).execute("weather", {"location": ""})

    assert result["ok"] is False
    assert "location" in result["error"].lower()


def test_unknown_tool_is_rejected():
    result = PortableToolRegistry(_desktop_capabilities()).execute("delete_everything", {})

    assert result == {"ok": False, "error": "Unknown or unavailable tool: delete_everything"}


def test_weather_code_mapping():
    assert _weather_description(0) == "clear"
    assert _weather_description(95) == "thunderstorm"
    assert _weather_description(None) == "unknown"
