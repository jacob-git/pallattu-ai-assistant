# Architecture

## Purpose

Pallattu AI Assistant is a local-first AI assistant and robotics platform intended to run primarily on Raspberry Pi 5. The architecture favors low idle cost, clear safety boundaries, replaceable AI providers, and incremental delivery.

## Design principles

### 1. Local first

Keep always-on work local whenever practical:

- microphone device management
- voice activity detection
- wake-word detection
- conversation/session state
- hardware state
- robot safety rules
- GPIO, motor, and sensor control

Cloud AI should be invoked only when it adds enough value to justify latency and cost.

### 2. AI does not directly control hardware

The language model may request a tool or robot action, but a deterministic controller validates and executes it.

```text
User speech
   |
   v
AI orchestrator
   |
   | tool request
   v
Robot controller
   |
   | validate limits / state / safety
   v
Hardware adapter
   |
   v
Physical device
```

The controller owns constraints such as maximum speed, distance, actuator range, obstacle handling, battery thresholds, and emergency stop behavior.

### 3. Provider abstraction

Speech-to-text, language-model, and text-to-speech capabilities should be accessed through small internal interfaces. Initial implementations may use OpenAI, while later implementations can add local or alternate providers without changing the conversation or robot layers.

### 4. Cost is an observable

Cloud requests should eventually record:

- provider and model
- input/output usage
- audio duration where applicable
- estimated cost
- latency
- success/failure

Cost optimization should be driven by measured usage rather than assumptions.

### 5. Build only the next abstraction needed

The repository starts intentionally small. Audio, AI, conversation, robotics, vision, and observability packages should be added as their milestones begin rather than as empty placeholder modules.

## Target logical components

```text
                    +-------------------+
                    |    Microphone     |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    |  Local audio path |
                    | VAD / wake / rec  |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Speech-to-Text    |
                    +---------+---------+
                              |
                              v
        +---------+  +-------------------+  +-------------+
        | Memory  |<-|   Orchestrator    |->| Tool router |
        +---------+  +---------+---------+  +------+------+
                              |                   |
                              v                   v
                    +-------------------+  +-------------+
                    | Language Model    |  | Robot ctrl  |
                    +---------+---------+  +------+------+
                              |                   |
                              v                   v
                    +-------------------+   Hardware / IO
                    | Text-to-Speech    |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    |      Speaker      |
                    +-------------------+
```

## Initial deployment model

For early releases, the application runs directly on the Raspberry Pi as a Python process. A cloud backend is not required for the first voice-assistant milestones.

A future service manager such as `systemd` can run the assistant at boot once the audio path and restart behavior are reliable.

## Security and privacy baseline

Never commit:

- API keys or access tokens
- `.env`
- Wi-Fi credentials
- private network configuration
- camera/audio recordings
- conversation transcripts containing personal information
- device-specific secrets

Public source code should contain only safe examples and defaults.
