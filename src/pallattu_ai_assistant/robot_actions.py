from __future__ import annotations

from dataclasses import dataclass

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
