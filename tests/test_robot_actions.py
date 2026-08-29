from pallattu_ai_assistant.robot_actions import RobotActionToolAdapter, SafeRobotController


class FakeActuator:
    def __init__(self):
        self.servo_calls = []
        self.drive_calls = []
        self.stop_calls = 0

    def available(self):
        return True

    def describe(self):
        return "fake actuator"

    def set_servo_angle(self, channel, angle_degrees):
        self.servo_calls.append((channel, angle_degrees))

    def drive(self, left_speed, right_speed, duration_seconds):
        self.drive_calls.append((left_speed, right_speed, duration_seconds))

    def stop(self):
        self.stop_calls += 1


def test_controller_rejects_out_of_bounds_motion():
    actuator = FakeActuator()
    controller = SafeRobotController(actuator)

    servo = controller.move_servo(0, 181)
    drive = controller.drive(0.8, 0.1, 1.0)

    assert servo["ok"] is False
    assert drive["ok"] is False
    assert actuator.servo_calls == []
    assert actuator.drive_calls == []


def test_drive_is_bounded_and_always_stops():
    actuator = FakeActuator()
    controller = SafeRobotController(actuator)

    result = controller.drive(0.25, 0.25, 0.5)

    assert result["ok"] is True
    assert actuator.drive_calls == [(0.25, 0.25, 0.5)]
    assert actuator.stop_calls == 1


def test_movement_tools_are_hidden_until_enabled():
    controller = SafeRobotController(FakeActuator())
    disabled = RobotActionToolAdapter(
        controller,
        enabled=False,
        servo_configured=True,
        drive_configured=True,
    )
    enabled = RobotActionToolAdapter(
        controller,
        enabled=True,
        servo_configured=True,
        drive_configured=True,
    )

    assert {item["name"] for item in disabled.definitions()} == {"robot_status"}
    assert {item["name"] for item in enabled.definitions()} == {
        "robot_status",
        "move_servo",
        "drive_robot",
        "stop_robot",
    }
