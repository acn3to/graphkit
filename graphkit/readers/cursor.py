"""Cursor dashboard usage CSV (Settings > Usage > export) -> Rows, one per request.

Columns seen 2026-09-13: Date, User, Kind, Model, Max Mode, Input (w/ Cache Write),
Input (w/o Cache Write), Cache Read, Output Tokens, Total Tokens, Cost.
cache_write is derived: Input (w/ Cache Write) minus Input (w/o Cache Write).
"""
from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from graphkit.rows import Row, parse_ts

_US = "%b %d, %Y, %I:%M %p"

def _int(s: str | None) -> int | None:
    s = (s or "").replace(",", "").strip()
    return int(float(s)) if s else None

def _date(s: str) -> datetime | None:
    dt = parse_ts(s.strip())
    if dt:
        return dt
    try:
        return datetime.strptime(s.strip(), _US).astimezone()
    except ValueError:
        return None

def read_cursor(path: Path) -> list[Row]:
    rows: list[Row] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f):
            with_cw = _int(rec.get("Input (w/ Cache Write)"))
            without = _int(rec.get("Input (w/o Cache Write)"))
            cw = (with_cw - without) if (with_cw is not None and without is not None) else None
            rows.append(Row(agent="cursor", ts=_date(rec.get("Date", "")), model=rec.get("Model") or None,
                            input=without, cache_read=_int(rec.get("Cache Read")), cache_write=cw,
                            output=_int(rec.get("Output Tokens")), total=_int(rec.get("Total Tokens")),
                            tool_calls=None))
    return rows
