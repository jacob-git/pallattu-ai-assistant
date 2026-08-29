# Roadmap

The roadmap is organized around small, testable releases. Each milestone should leave the assistant in a working state and avoid introducing the next layer before the current one is reliable.

## v0.1 — Audio Foundation

Goal: establish a dependable Raspberry Pi 5 microphone and speaker path before adding AI.

Deliverables:

- enumerate available input/output audio devices
- configurable microphone and speaker selection
- record speech to WAV from Python
- play recorded audio through the selected output
- diagnostic command for Raspberry Pi audio setup
- hardware-focused tests runnable on the Pi
- setup documentation for supported audio hardware

Acceptance criteria:

- [ ] Raspberry Pi detects the intended USB microphone
- [ ] Raspberry Pi detects the intended speaker/output device
- [ ] application records a clear 5-second WAV file
- [ ] recorded audio plays through the intended speaker
- [ ] device selection survives application restart
- [ ] failures produce actionable diagnostics

## v0.2 — Push-to-Talk AI

Goal: complete the first cost-controlled end-to-end AI conversation.

Flow:

```text
user starts capture -> record -> STT -> LLM -> TTS -> speaker
```

Deliverables:

- speech-to-text provider interface
- language-model provider interface
- text-to-speech provider interface
- initial OpenAI implementations
- push-to-talk conversation loop
- request latency logging
- initial API cost accounting

Acceptance criteria:

- [ ] user can ask a spoken question and hear a spoken answer
- [ ] API keys remain outside the repository
- [ ] each cloud request records model, latency, and estimated cost
- [ ] provider failures do not crash the process

## v0.3 — Hands-Free Voice

Goal: eliminate manual push-to-talk while keeping idle cloud cost near zero.

Deliverables:

- local voice activity detection
- automatic speech start/end detection
- configurable silence threshold
- interruption/cancellation behavior

Acceptance criteria:

- [ ] silence is not sent to cloud APIs
- [ ] normal speech reliably starts capture
- [ ] end-of-speech detection feels natural in a quiet room
- [ ] accidental short noises are filtered where practical

## v0.4 — Wake Word

Goal: allow passive local listening without continuous cloud usage.

Deliverables:

- local wake-word engine
- activation sound/state
- configurable active-conversation timeout
- clean return to idle state

Acceptance criteria:

- [ ] no cloud request occurs before activation
- [ ] wake word works consistently at normal room distance
- [ ] assistant returns to idle after timeout or explicit dismissal

## v0.5 — Conversation Memory

Goal: support useful multi-turn conversations without uncontrolled context growth.

Deliverables:

- session model
- recent-message window
- older-context summarization
- explicit reset/new conversation behavior
- local persistence strategy for non-sensitive state

Acceptance criteria:

- [ ] follow-up questions resolve recent context correctly
- [ ] old conversation history does not grow indefinitely
- [ ] user can clear conversation state

## v0.6 — Safe Tool Execution

Goal: let the AI request useful physical or local actions without directly controlling hardware.

Deliverables:

- typed tool contracts
- tool registry/router
- deterministic robot controller
- action validation layer
- emergency stop mechanism
- simulated hardware adapter for development

Acceptance criteria:

- [ ] LLM output cannot write directly to GPIO/motor interfaces
- [ ] invalid or unsafe actions are rejected deterministically
- [ ] robot actions can be tested without physical hardware
- [ ] emergency stop overrides active motion

## v0.7 — Sensors

Goal: make the assistant aware of its immediate environment.

Possible capabilities:

- distance/proximity
- temperature/environmental sensing
- IMU/orientation
- battery/power state

## v0.8 — Vision

Goal: add camera perception behind a dedicated vision interface.

Possible capabilities:

- camera capture
- person/object detection
- visual question answering when explicitly requested
- local lightweight detection where practical
- privacy-aware capture and retention rules

## v0.9 — Mobility

Goal: integrate safe physical movement.

Possible capabilities:

- motor control
- obstacle detection
- orientation/turning
- bounded movement commands
- supervised navigation experiments

## v1.0 — Integrated Home Assistant

Goal: combine reliable voice, contextual conversation, perception, tools, and safe physical actions into one coherent Raspberry Pi-based assistant platform.

Success is not defined by maximum autonomy. It is defined by usefulness, predictable behavior, measurable cost, privacy, and safe failure modes.
