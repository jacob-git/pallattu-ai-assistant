from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from pallattu_ai_assistant import __version__
from pallattu_ai_assistant.bootstrap import build_app
from pallattu_ai_assistant.config import load_settings, validate_settings

CONFIG_TEMPLATE = """# Pallattu AI Assistant - local configuration
# Keep this file private. Never commit it.
OPENAI_API_KEY=
PICOVOICE_ACCESS_KEY=

# Built-in Porcupine keyword for first run. Set PALLATTU_WAKE_WORD_MODEL
# to a local .ppn file when you create a custom 'Hey Pallattu' model.
PALLATTU_WAKE_KEYWORD=porcupine
PALLATTU_WAKE_WORD_MODEL=

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
    print("Add your OPENAI_API_KEY and PICOVOICE_ACCESS_KEY, then run:")
    print("  pallattu-ai-assistant run")


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="pallattu-ai-assistant")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command")
    init_parser = subcommands.add_parser("init", help="create a local .env configuration")
    init_parser.add_argument("--path", type=Path, default=Path(".env"))
    subcommands.add_parser("run", help="start the assistant")
    args = parser.parse_args()

    if args.command == "init":
        _init_config(args.path)
    elif args.command == "run":
        _run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
