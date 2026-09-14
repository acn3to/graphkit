"""Every line graphkit adds is fenced, so uninstall removes exactly that and nothing else.

The start marker records how many newline characters append_block inserted between the
old content and the marker (0, 1 or 2), as `sep=N`, so strip_block can remove exactly that
many and restore the original file byte-for-byte, whether it ended in no newline, one, or
two. A marker written before `sep` existed is read as sep=1. Extra words after `sep=N`
(the caller's own note, such as `created`) are parsed and ignored here; read them with
`block_note`.

A block is a full start marker alone on its line AND a matching end marker after it.
Nothing less counts, because the file belongs to the user: prose that happens to mention
graphkit:start mid-sentence is not a block (matching the bare prefix made install report
"already installed" and uninstall cut the user's text), and a near miss such as
`<!-- graphkit:startup -->` is not a block either (it used to reach strip_block and raise
AttributeError). When a start marker has no end after it the structure is broken, so
strip_block removes nothing, returns False and leaves the file exactly as it is.
"""
from __future__ import annotations
import json, re
from pathlib import Path

STAMP = ".graphkit"
_WORDS = r"(?: [A-Za-z0-9_.-]+)*"
_START_RE = {
    "html": re.compile(r"^<!-- graphkit:start(?: sep=(\d+))?" + _WORDS + r" -->$", re.M),
    "hash": re.compile(r"^# graphkit:start(?: sep=(\d+))?" + _WORDS + r"$", re.M),
}
_END = {"html": "<!-- graphkit:end -->", "hash": "# graphkit:end"}
_END_RE = {
    "html": re.compile(r"^<!-- graphkit:end -->$", re.M),
    "hash": re.compile(r"^# graphkit:end$", re.M),
}

def _start_marker(style: str, sep_n: int, note: str = "") -> str:
    extra = f" {note}" if note else ""
    return f"<!-- graphkit:start sep={sep_n}{extra} -->" if style == "html" else f"# graphkit:start sep={sep_n}{extra}"

def _find_block(text: str, style: str):
    """The first start marker that has an end marker after it, as (start, end) matches."""
    for m in _START_RE[style].finditer(text):
        e = _END_RE[style].search(text, m.end())
        if e:
            return m, e
    return None

def has_block(path: Path, style: str = "html") -> bool:
    """True only for a complete block: a full start marker line with an end marker after it."""
    return path.exists() and _find_block(path.read_text(encoding="utf-8"), style) is not None

def block_note(path: Path, style: str = "html") -> str:
    """The extra words the caller wrote after `sep=N` in the start marker, or ''."""
    if not path.exists():
        return ""
    s = path.read_text(encoding="utf-8")
    found = _find_block(s, style)
    if not found:
        return ""
    line = s[found[0].start():found[0].end()]
    line = line.removeprefix("<!-- ").removesuffix(" -->").removeprefix("# ")
    return line.split(" ", 2)[2] if len(line.split(" ")) > 2 else ""

def append_block(path: Path, text: str, style: str = "html", note: str = "") -> bool:
    """Append a fenced block. `note` is written into the start marker for the caller to read back."""
    if has_block(path, style):
        return False
    end = _END[style]
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    sep = "" if (old == "" or old.endswith("\n\n")) else ("\n" if old.endswith("\n") else "\n\n")
    start = _start_marker(style, len(sep), note)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{old}{sep}{start}\n{text.rstrip()}\n{end}\n", encoding="utf-8")
    return True

def strip_block(path: Path, style: str = "html") -> bool:
    """Remove the first complete block and the newlines append_block added. False if there is none."""
    if not path.exists():
        return False
    s = path.read_text(encoding="utf-8")
    found = _find_block(s, style)
    if not found:
        return False
    m, e = found
    i = m.start()
    sep_n = int(m.group(1)) if m.group(1) is not None else 1
    j = e.end()
    if j < len(s) and s[j] == "\n":
        j += 1
    before = s[:i]
    for _ in range(sep_n):
        if before.endswith("\n"):
            before = before[:-1]
    path.write_text(before + s[j:], encoding="utf-8")
    return True

def write_stamp(folder: Path, meta: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / STAMP).write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")

def read_stamp(folder: Path) -> dict | None:
    p = folder / STAMP
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
