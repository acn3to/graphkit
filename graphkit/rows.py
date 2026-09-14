"""One row shape for every agent log. Unknown numbers are None, never 0."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass(frozen=True)
class Row:
    agent: str
    ts: datetime | None
    model: str | None
    input: int | None
    cache_read: int | None
    cache_write: int | None
    output: int | None
    total: int | None
    tool_calls: int | None
    session: str | None = None  # claude-code: transcript file stem; other agents: None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = self.ts.isoformat() if self.ts else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Row":
        ts = datetime.fromisoformat(d["ts"]) if d.get("ts") else None
        return cls(**{**d, "ts": ts})

NUMERIC = ("input", "cache_read", "cache_write", "output", "total", "tool_calls")

def parse_ts(s: str | None) -> datetime | None:
    """ISO 8601 with or without Z; returns an aware datetime in local time, or None."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone()
