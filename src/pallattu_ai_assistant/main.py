from __future__ import annotations

import logging
import sys

from pallattu_ai_assistant import __version__
from pallattu_ai_assistant.config import load_settings, validate_settings
from pallattu_ai_assistant.runtime import AssistantRuntime


def main() -> None:
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

    logging.getLogger(__name__).info("Pallattu AI Assistant v%s starting", __version__)
    AssistantRuntime(settings).run_forever()


if __name__ == "__main__":
    main()
