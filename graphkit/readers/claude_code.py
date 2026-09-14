"""Claude Code transcripts (~/.claude/projects/<slug>/*.jsonl) -> Rows, one per assistant message."""
from __future__ import annotations
import json, os, re
from pathlib import Path
from graphkit.rows import Row, parse_ts

def transcripts_for(project: Path, since: str | None) -> list[Path]:
    """The transcripts Claude Code wrote for `project`, oldest first.

    Claude Code names the project directory after the absolute path with every character
    that is not a letter or a digit replaced by '-', not only the separators: verified
    2026-09-13, ~/some.tool/observer/sessions maps to
    -home-user--some-tool-observer-sessions. Replacing only '/' silently missed every
    repo path holding a dot, an underscore or a space. A directory that does not exist is
    an error, not an empty measurement.
    """
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(Path(project).resolve()))
    d = Path(os.path.expanduser("~")) / ".claude" / "projects" / slug
    if not d.is_dir():
        raise SystemExit(f"no transcripts at {d}")
    out = []
    for p in sorted(d.glob("*.jsonl"), key=lambda p: (p.stat().st_mtime, p.name)):
        if since and _first_ts(p) < since:
            continue
        out.append(p)
    return out

def _first_ts(p: Path) -> str:
    for line in open(p, errors="replace"):
        try:
            ts = json.loads(line).get("timestamp")
        except json.JSONDecodeError:
            continue
        if ts:
            return ts
    return ""

def read_claude_code(paths: list[Path]) -> list[Row]:
    rows: list[Row] = []
    for p in paths:
        for line in open(p, errors="replace"):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "assistant":
                continue
            m = d.get("message") or {}
            u = m.get("usage")
            content = m.get("content") if isinstance(m.get("content"), list) else []
            tools = sum(1 for c in content if isinstance(c, dict) and c.get("type") == "tool_use")
            if u is None:
                inp = cr = cw = out = total = None
            else:
                inp = u.get("input_tokens", 0); cr = u.get("cache_read_input_tokens", 0)
                cw = u.get("cache_creation_input_tokens", 0); out = u.get("output_tokens", 0)
                total = inp + cr + cw + out
            rows.append(Row(agent="claude-code", ts=parse_ts(d.get("timestamp")), model=m.get("model"),
                            input=inp, cache_read=cr, cache_write=cw, output=out,
                            total=total, tool_calls=tools, session=p.stem))
    return rows
