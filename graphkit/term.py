"""Whether the human-friendly renderers may use color: a real terminal, and NO_COLOR unset."""
import os, sys

GREEN, RED, RESET = "\033[32m", "\033[31m", "\033[0m"

def color_enabled() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")

# A legacy Windows console (cp1252, cp437, ...) raises UnicodeEncodeError on print()
# for glyphs outside its codepage, crashing the whole command over a display detail
# after real work (install's file changes) already happened.
_ASCII_FALLBACK = {"✓": "+", "✗": "x", "—": "--", "…": "..."}

def safe(s: str, encoding: str | None = None) -> str:
    enc = encoding if encoding is not None else (getattr(sys.stdout, "encoding", None) or "utf-8")
    try:
        s.encode(enc)
        return s
    except (UnicodeEncodeError, LookupError):
        for u, a in _ASCII_FALLBACK.items():
            s = s.replace(u, a)
        return s
