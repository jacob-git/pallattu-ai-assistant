from __future__ import annotations

import importlib.util
import time

from pallattu_ai_assistant.config import Settings
from pallattu_ai_assistant.device import discover_device_capabilities


class UnavailableActuatorAdapter:
    def available(self) -> bool:
        return False

    def describe(self) -> str:
        return "no configured robot actuators"

    def set_servo_angle(self, channel: int, angle_degrees: float) -> None:
        raise RuntimeError("Robot actuators are unavailable.")

    def drive(self, left_speed: float, right_speed: float, duration_seconds: float) -> None:
        raise RuntimeError("Robot actuators are unavailable.")

    def stop(self) -> None:
        return


class RaspberryPiGpioZeroActuatorAdapter:
    """Optional gpiozero adapter; hardware pin configuration is always explicit."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._active_motors = None

    @property
    def servo_configured(self) -> bool:
        return self.settings.servo_pin is not None

    @property
    def drive_configured(self) -> bool:
        return all(
            pin is not None
            for pin in (
                self.settings.left_motor_forward_pin,
                self.settings.left_motor_backward_pin,
                self.settings.right_motor_forward_pin,
                self.settings.right_motor_backward_pin,
            )
        )

    def available(self) -> bool:
        capabilities = discover_device_capabilities()
        return (
            self.settings.robot_actions_enabled
            and capabilities.is_raspberry_pi
            and importlib.util.find_spec("gpiozero") is not None
            and (self.servo_configured or self.drive_configured)
        )

    def describe(self) -> str:
        modes = []
        if self.servo_configured:
            modes.append("servo")
        if self.drive_configured:
            modes.append("dual-motor drive")
        configured = ", ".join(modes) if modes else "no pins configured"
        return f"Raspberry Pi gpiozero actuators ({configured})"

    def set_servo_angle(self, channel: int, angle_degrees: float) -> None:
        if not self.available() or not self.servo_configured:
            raise RuntimeError("Servo control is not configured.")
        if channel != 0:
            raise ValueError("The direct GPIO adapter currently exposes only servo channel 0.")

        from gpiozero import AngularServo  # type: ignore[import-not-found]

        servo = AngularServo(
            self.settings.servo_pin,
            min_angle=0,
            max_angle=180,
        )
        try:
            servo.angle = angle_degrees
            time.sleep(0.35)
            servo.detach()
        finally:
            servo.close()

    def drive(self, left_speed: float, right_speed: float, duration_seconds: float) -> None:
        if not self.available() or not self.drive_configured:
            raise RuntimeError("Motor drive is not configured.")

        from gpiozero import Motor  # type: ignore[import-not-found]

        left = Motor(
            forward=self.settings.left_motor_forward_pin,
            backward=self.settings.left_motor_backward_pin,
        )
        right = Motor(
            forward=self.settings.right_motor_forward_pin,
            backward=self.settings.right_motor_backward_pin,
        )
        self._active_motors = (left, right)
        try:
            left.value = left_speed
            right.value = right_speed
            time.sleep(duration_seconds)
        finally:
            left.stop()
            right.stop()
            left.close()
            right.close()
            self._active_motors = None

    def stop(self) -> None:
        if self._active_motors is None:
            return
        left, right = self._active_motors
        left.stop()
        right.stop()


def build_actuator_adapter(settings: Settings):
    adapter = RaspberryPiGpioZeroActuatorAdapter(settings)
    if adapter.available():
        return adapter
    return UnavailableActuatorAdapter()
