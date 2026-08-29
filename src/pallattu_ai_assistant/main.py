from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pallattu_ai_assistant import __version__
from pallattu_ai_assistant.bootstrap import build_app
from pallattu_ai_assistant.config import load_settings, validate_settings
from pallattu_ai_assistant.doctor import run_doctor
from pallattu_ai_assistant.memory import SQLiteMemoryAdapter

CONFIG_TEMPLATE = """# Pallattu AI Assistant - local configuration
# Keep this file private. Never commit it.
OPENAI_API_KEY=

# Local wake-word configuration. No vendor key is required.
# Built-in model for first run; later point PALLATTU_WAKE_WORD_MODEL to a custom model.
PALLATTU_WAKE_MODEL=hey jarvis
PALLATTU_WAKE_WORD_MODEL=
PALLATTU_WAKE_THRESHOLD=0.5

# Default wake acknowledgement: instant beep, then local device voice.
PALLATTU_WAKE_ACK=beep_and_voice
PALLATTU_WAKE_ACK_TEXT=I'm listening.

# Local voice activity detection: silero (default) or webrtc.
PALLATTU_VAD_ENGINE=silero
PALLATTU_VAD_THRESHOLD=0.5
PALLATTU_WEBRTC_VAD_MODE=2

# Audio playback follows the selected device/system volume.
# Leave this at 1.0 normally; increase only if TTS is still too quiet.
PALLATTU_OUTPUT_GAIN=1.0

# Persistent local memory defaults to ~/.pallattu-ai-assistant/memory.sqlite3.
# PALLATTU_MEMORY_PATH=/your/local/path/memory.sqlite3
PALLATTU_MEMORY_MAX_MESSAGES=500

PALLATTU_LLM_MODEL=gpt-5.6-luna
PALLATTU_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
PALLATTU_TTS_MODEL=gpt-4o-mini-tts
PALLATTU_TTS_VOICE=coral
PALLATTU_FOLLOW_UP_SECONDS=10
"""


def _init_config(path: Path) -> None:
    if path.exists():
        print(f"Configuration already exists: {path}")
        return
    path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    print(f"Created {path}")
    print("Add your OPENAI_API_KEY, then run:")
    print("  pallattu-ai-assistant doctor")
    print("  pallattu-ai-assistant run")


def _doctor() -> None:
    settings = load_settings()
    checks = run_doctor(settings)
    print(f"Pallattu AI Assistant v{__version__}")
    print()
    for check in checks:
        mark = "✓" if check.ok else "✗"
        print(f"{mark} {check.name:<18} {check.detail}")
    if sys.platform == "darwin":
        print()
        print("macOS: if microphone access is blocked, allow your terminal app in")
        print("System Settings > Privacy & Security > Microphone.")
    if not all(check.ok for check in checks):
        raise SystemExit(2)


def _run() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    errors = validate_settings(settings)
    if errors:
        print(f"Pallattu AI Assistant v{__version__} cannot start:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(2)
    build_app(settings).run_forever()


def _memory(args: argparse.Namespace) -> None:
    settings = load_settings()
    memory = SQLiteMemoryAdapter(
        settings.memory_path,
        max_conversation_messages=settings.memory_max_messages,
    )

    if args.memory_command == "list":
        memories = memory.list_memories(limit=args.limit)
        if not memories:
            print("No long-term memories stored.")
            return
        for index, item in enumerate(memories, start=1):
            print(f"{index}. {item}")
    elif args.memory_command == "stats":
        for key, value in memory.stats().items():
            print(f"{key}: {value}")
    elif args.memory_command == "forget":
        result = memory.forget(args.query)
        print(f"Deleted {result.get('deleted', 0)} matching memories.")
    elif args.memory_command == "clear":
        deleted = memory.clear_memories()
        print(f"Deleted {deleted} long-term memories.")
    elif args.memory_command == "clear-conversations":
        deleted = memory.clear_conversations()
        print(f"Deleted {deleted} conversation messages.")
    elif args.memory_command == "prune":
        deleted = memory.prune_conversations(args.keep)
        print(f"Pruned {deleted} old conversation messages.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pallattu-ai-assistant")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command")
    init_parser = subcommands.add_parser("init", help="create a local .env configuration")
    init_parser.add_argument("--path", type=Path, default=Path(".env"))
    subcommands.add_parser("doctor", help="check keys and local audio readiness")
    subcommands.add_parser("run", help="start the assistant")

    memory_parser = subcommands.add_parser("memory", help="inspect and manage local memory")
    memory_commands = memory_parser.add_subparsers(dest="memory_command", required=True)
    memory_list = memory_commands.add_parser("list", help="list long-term memories")
    memory_list.add_argument("--limit", type=int, default=20)
    memory_commands.add_parser("stats", help="show memory database statistics")
    memory_forget = memory_commands.add_parser("forget", help="forget matching long-term memories")
    memory_forget.add_argument("query")
    memory_commands.add_parser("clear", help="clear all long-term memories")
    memory_commands.add_parser("clear-conversations", help="clear persisted conversation history")
    memory_prune = memory_commands.add_parser("prune", help="prune old conversation messages")
    memory_prune.add_argument("--keep", type=int, default=500)

    args = parser.parse_args()

    if args.command == "init":
        _init_config(args.path)
    elif args.command == "doctor":
        _doctor()
    elif args.command == "run":
        _run()
    elif args.command == "memory":
        _memory(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
