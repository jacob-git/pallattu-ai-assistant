# Robotics foundation

Version 0.7.0 extends Pallattu AI Assistant from voice + tools + memory into a portable robotics foundation.

## Architecture

```text
Wake word / speech
       |
       v
      STT
       |
       v
      LLM
       |
       +---- ToolPort -----------------------------+
       |                                           |
       |  portable tools                           |
       |  memory tools                             |
       |  camera / scene tools                     |
       |  guarded robot-action tools               |
       |                                           |
       +-------------------------------------------+
                           |
                    safety controller
                           |
                      ActuatorPort
                           |
              Raspberry Pi adapter only
```

The LLM never receives direct access to GPIO, camera drivers, shell commands, or motor libraries.

## Memory management

Conversation history is automatically retained up to `PALLATTU_MEMORY_MAX_MESSAGES` (default 500). Long-term memories remain separate.

Local commands:

```bash
pallattu-ai-assistant memory list
pallattu-ai-assistant memory stats
pallattu-ai-assistant memory forget "wake phrase"
pallattu-ai-assistant memory prune --keep 200
pallattu-ai-assistant memory clear-conversations
pallattu-ai-assistant memory clear
```

## Camera and scene understanding

`VisionPort` represents a still-image source. The Raspberry Pi implementation uses Picamera2 only when the library and camera are present. Other devices can provide different adapters without changing the application core.

Available voice tools include:

- `camera_status` on every device
- `look_at_scene` only when a supported camera is available

`look_at_scene` captures one still frame for the current request. The application does not continuously record video.

On Raspberry Pi OS, Picamera2 is normally installed through the operating-system package set. Run `pallattu-ai-assistant doctor` after installation to confirm discovery.

## Robot actions

Physical movement is disabled by default:

```text
PALLATTU_ROBOT_ACTIONS_ENABLED=false
```

The direct GPIO prototype supports one servo and an optional dual-motor drive through `gpiozero`. Pins must be configured explicitly before movement can be enabled.

Example only — use the BCM pins that match the hardware you actually wire:

```text
PALLATTU_ROBOT_ACTIONS_ENABLED=true
PALLATTU_SERVO_PIN=18
PALLATTU_LEFT_MOTOR_FORWARD_PIN=17
PALLATTU_LEFT_MOTOR_BACKWARD_PIN=27
PALLATTU_RIGHT_MOTOR_FORWARD_PIN=22
PALLATTU_RIGHT_MOTOR_BACKWARD_PIN=23
```

Do not enable these settings until a proper motor driver / servo power arrangement is connected. Motors and servos must not be powered directly from Raspberry Pi GPIO pins.

### Built-in limits

The safety controller currently enforces:

- servo angles: 0–180 degrees
- direct GPIO servo channel: channel 0 only
- drive speed: at most 50% in either direction
- drive duration: at most 2 seconds per request
- drive motors are stopped in a `finally` path after each movement
- movement tools are hidden unless movement is explicitly enabled and hardware is configured
- the system prompt instructs the model to move only after an explicit current-turn user request

These limits are application safeguards, not a replacement for physical safety mechanisms. A future mobile/humanoid build should also have a hardware emergency stop and independent motor power cutoff.

## Local validation

GitHub Actions are intentionally disabled for now. Run checks locally instead:

```bash
pip install -e ".[dev]"
bash scripts/check-local.sh
```

This runs Ruff, pytest, and a distribution build without consuming GitHub Actions minutes.
