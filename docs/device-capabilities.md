# Device capability discovery

Pallattu AI Assistant keeps device-specific hardware outside the portable application core.

At startup, the device adapter discovers available capabilities and the tool registry exposes only tools that the current machine can actually support.

## Portable devices

On macOS, Windows, generic Linux, and other supported desktops/servers, the assistant exposes:

- `current_time`
- `weather`
- `system_status`
- `device_capabilities`

## Raspberry Pi

When `/proc/device-tree/model` or `/sys/firmware/devicetree/base/model` identifies a Raspberry Pi, the runtime also checks for:

- processor temperature through `/sys/class/thermal/thermal_zone0/temp`
- GPIO controllers through `/dev/gpiochip*`

If present, these additional read-only tools are registered:

- `device_temperature` — reads processor temperature
- `gpio_status` — reports available GPIO chips and access state; it never changes a pin

No Raspberry Pi package is imported by the assistant core, and a Mac install does not expose Pi-only tools.

## Verify on a Raspberry Pi

After installing the same distribution used on desktop, run:

```bash
pallattu-ai-assistant doctor
```

A Pi with the expected kernel interfaces should show a capability summary similar to:

```text
Capabilities       portable tools, Raspberry Pi, temperature, GPIO read-only
```

Then start the assistant:

```bash
pallattu-ai-assistant run
```

Example voice requests:

```text
Hey Jarvis
What capabilities does this device have?

Hey Jarvis
What is the processor temperature?

Hey Jarvis
What GPIO hardware is available?
```

## Safety boundary

The GPIO tool in this iteration is intentionally status-only. It does not set direction, drive high/low, toggle a pin, execute shell commands, or control motors.

Future write-capable hardware actions must pass through a separate validated action layer with explicit allowed operations and safety checks.
