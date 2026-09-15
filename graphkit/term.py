"""Whether the human-friendly renderers may use color: a real terminal, and NO_COLOR unset."""
import os, sys

GREEN, RED, RESET = "\033[32m", "\033[31m", "\033[0m"

def color_enabled() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")
