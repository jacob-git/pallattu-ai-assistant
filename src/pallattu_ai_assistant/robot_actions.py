from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pallattu_ai_assistant.ports import ActuatorPort


@dataclass(frozen=True)
class RobotSafetyLimits:
    min_servo_angle: float = 0.0
    max_servo_angle: float = 180.0
    max_drive_speed: float = 0.5
    max_drive_duration_seconds: float = 2.0
    min_channel: int = 0
    max_channel: int = 15


class SafeRobotController:
    """Validate and bound every actuator request before it reaches hardware."""

    def __init__(
        self,
        actuator: ActuatorPort,
        limits: RobotSafetyLimits | None = None,
    ) -> None:
        self.actuator = actuator
        self.limits = limits or RobotSafetyLimits()

    def available(self) -> bool:
        return self.actuator.available()

    def describe(self) -> str:
        return self.actuator.describe()

    def move_servo(self, channel: int, angle_degrees: float) -> dict[str, object]:
        if not self.available():
            return {"ok": False, "error": "Robot actuators are not available."}
        if not self.limits.min_channel <= channel <= self.limits.max_channel:
            return {"ok": False, "error": "Servo channel is outside the allowed range."}
        if not self.limits.min_servo_angle <= angle_degrees <= self.limits.max_servo_angle:
            return {"ok": False, "error": "Servo angle is outside the safe configured range."}

        self.actuator.set_servo_angle(channel, angle_degrees)
        return {
            "ok": True,
            "action": "servo_move",
            "channel": channel,
            "angle_degrees": angle_degrees,
        }

    def drive(
        self,
        left_speed: float,
        right_speed: float,
        duration_seconds: float,
    ) -> dict[str, object]:
        if not self.available():
            return {"ok": False, "error": "Robot actuators are not available."}
        maximum = self.limits.max_drive_speed
        if not -maximum <= left_speed <= maximum or not -maximum <= right_speed <= maximum:
            return {"ok": False, "error": "Requested drive speed exceeds the configured safe limit."}
        if not 0.05 <= duration_seconds <= self.limits.max_drive_duration_seconds:
            return {"ok": False, "error": "Requested drive duration exceeds the configured safe limit."}

        try:
            self.actuator.drive(left_speed, right_speed, duration_seconds)
        finally:
            self.actuator.stop()
        return {
            "ok": True,
            "action": "drive",
            "left_speed": left_speed,
            "right_speed": right_speed,
            "duration_seconds": duration_seconds,
        }

    def stop(self) -> dict[str, object]:
        if not self.available():
            return {"ok": False, "error": "Robot actuators are not available."}
        self.actuator.stop()
        return {"ok": True, "action": "stop"}


class RobotActionToolAdapter:
    """Model-facing tools backed by the safety controller, never raw GPIO."""

    def __init__(
        self,
        controller: SafeRobotController,
        *,
        enabled: bool,
        servo_configured: bool,
        drive_configured: bool,
    ) -> None:
        self.controller = controller
        self.enabled = enabled
        self.servo_configured = servo_configured
        self.drive_configured = drive_configured

    def definitions(self) -> list[dict[str, Any]]:
        definitions: list[dict[str, Any]] = [
            {
                "type": "function",
                "name": "robot_status",
                "description": "Report whether bounded robot movement is configured and enabled.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        ]
        if not self.enabled or not self.controller.available():
            return definitions

        if self.servo_configured:
            definitions.append(
                {
                    "type": "function",
                    "name": "move_servo",
                    "description": (
                        "Move configured servo channel 0 to a bounded angle. Use only when the user "
                        "explicitly requests this physical movement in the current turn."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "channel": {"type": "integer", "minimum": 0, "maximum": 0},
                            "angle_degrees": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 180,
                            },
                        },
                        "required": ["channel", "angle_degrees"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            )

        if self.drive_configured:
            definitions.extend(
                [
                    {
                        "type": "function",
                        "name": "drive_robot",
                        "description": (
                            "Drive the robot for a short bounded interval. Use only for an explicit "
                            "movement request in the current turn. Speeds are limited to half power."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "left_speed": {
                                    "type": "number",
                                    "minimum": -0.5,
                                    "maximum": 0.5,
                                },
                                "right_speed": {
                                    "type": "number",
                                    "minimum": -0.5,
                                    "maximum": 0.5,
                                },
                                "duration_seconds": {
                                    "type": "number",
                                    "minimum": 0.05,
                                    "maximum": 2.0,
                                },
                            },
                            "required": ["left_speed", "right_speed", "duration_seconds"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                    {
                        "type": "function",
                        "name": "stop_robot",
                        "description": "Immediately stop configured drive motors.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                ]
            )
        return definitions

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, object]:
        if name == "robot_status":
            return {
                "ok": True,
                "enabled": self.enabled,
                "available": self.controller.available(),
                "servo_configured": self.servo_configured,
                "drive_configured": self.drive_configured,
                "adapter": self.controller.describe(),
                "limits": {
                    "max_drive_speed": self.controller.limits.max_drive_speed,
                    "max_drive_duration_seconds": (
                        self.controller.limits.max_drive_duration_seconds
                    ),
                },
            }
        if not self.enabled:
            return {"ok": False, "error": "Robot actions are disabled by configuration."}
        try:
            if name == "move_servo" and self.servo_configured:
                return self.controller.move_servo(
                    int(arguments.get("channel", 0)),
                    float(arguments.get("angle_degrees", 90)),
                )
            if name == "drive_robot" and self.drive_configured:
                return self.controller.drive(
                    float(arguments.get("left_speed", 0)),
                    float(arguments.get("right_speed", 0)),
                    float(arguments.get("duration_seconds", 0.5)),
                )
            if name == "stop_robot" and self.drive_configured:
                return self.controller.stop()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            return {"ok": False, "error": f"Robot action failed: {exc}"}
        return {"ok": False, "error": f"Unknown or unavailable robot action: {name}"}
