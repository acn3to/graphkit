"""Sum Rows, cut them by time window, and print one table a deck can paste."""
from __future__ import annotations
import json, sys
from datetime import datetime, time, date
from pathlib import Path
from graphkit.rows import Row, NUMERIC

SUM_KEYS = ("input", "cache_read", "cache_write", "output", "total", "tool_calls")
LABELS = {"requests": "requests", "input": "input tokens", "cache_read": "cache read", "cache_write": "cache write",
          "output": "output tokens", "total": "total tokens", "tool_calls": "tool calls"}

def parse_when(s: str | None, day: datetime | None = None) -> datetime | None:
    """'HH:MM' on the given day (default today), or an ISO datetime. Local, aware."""
    if not s:
        return None
    if len(s) == 5 and s[2] == ":":
        base = day or datetime.now().astimezone()
        hh, mm = s.split(":")
        return base.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    dt = datetime.fromisoformat(s)
    return dt.astimezone() if dt.tzinfo else dt.astimezone()

def in_window(rows: list[Row], start: datetime | None, end: datetime | None) -> list[Row]:
    """The rows inside [start, end). A row whose timestamp did not parse cannot be placed,
    so it is dropped; cmd_measure counts those first and says so on stderr, because a
    locale-sensitive Cursor date can otherwise window every row away and read as no usage."""
    out = []
    for r in rows:
        if r.ts is None:
            continue
        if start and r.ts < start:
            continue
        if end and r.ts >= end:
            continue
        out.append(r)
    return out

def apply_filters(rows: list[Row], exclude_sessions: list[str], model: str | None) -> list[Row]:
    """Drop the listed sessions, then keep only rows whose model contains `model`
    (case-insensitive). Runs after the window, so a driver session that spans both arms
    of an A/B can be taken out of each."""
    out = [r for r in rows if r.session not in set(exclude_sessions)]
    if model:
        needle = model.lower()
        out = [r for r in out if r.model and needle in r.model.lower()]
    return out

def breakdown(rows: list[Row]) -> str:
    """One line per session, descending total: id, model(s), rows, total tokens.
    A driver contaminating the window shows here without any flag."""
    per: dict[str, dict] = {}
    for r in rows:
        e = per.setdefault(r.session or "-", {"models": set(), "rows": 0, "total": 0})
        e["models"].add(r.model or "-"); e["rows"] += 1; e["total"] += r.total or 0
    lines = [f"sessions in window: {len(per)}"]
    for sid, e in sorted(per.items(), key=lambda kv: (-kv[1]["total"], kv[0])):
        lines.append(f"{sid}  {','.join(sorted(e['models']))}  {e['rows']}  {e['total']}")
    return "\n".join(lines)

def _filters_line(d: dict) -> str:
    f = d.get("filters") or {}
    ex = ",".join(f.get("exclude_session") or []) or "-"
    return f"exclude_session={ex} model={f.get('model') or '-'}"

def summarize(rows: list[Row]) -> dict:
    s: dict = {"requests": len(rows)}
    for k in SUM_KEYS:
        vals = [getattr(r, k) for r in rows if getattr(r, k) is not None]
        s[k] = sum(vals) if vals else None
    return s

def _fmt(v) -> str:
    return "-" if v is None else str(v)

def table_markdown(rows: list[Row]) -> str:
    head = "| time | model | input | cache read | cache write | output | total | tools |\n|---|---|---|---|---|---|---|---|"
    body = [f"| {r.ts.strftime('%H:%M:%S') if r.ts else '-'} | {r.model or '-'} | {_fmt(r.input)} | {_fmt(r.cache_read)} | {_fmt(r.cache_write)} | {_fmt(r.output)} | {_fmt(r.total)} | {_fmt(r.tool_calls)} |" for r in rows]
    s = summarize(rows)
    foot = f"| **sum** ({s['requests']} requests) | | {_fmt(s['input'])} | {_fmt(s['cache_read'])} | {_fmt(s['cache_write'])} | {_fmt(s['output'])} | {_fmt(s['total'])} | {_fmt(s['tool_calls'])} |"
    return "\n".join([head, *body, foot])

def _line(cells: list[str], widths: list[int], right: set[int]) -> str:
    return "  ".join(c.rjust(w) if i in right else c.ljust(w) for i, (c, w) in enumerate(zip(cells, widths))).rstrip()

def table_human(rows: list[Row]) -> str:
    headers = ["time", "model", "input", "cache read", "cache write", "output", "total", "tools"]
    right = {2, 3, 4, 5, 6, 7}
    body = [[r.ts.strftime('%H:%M:%S') if r.ts else '-', r.model or '-',
              _fmt(r.input), _fmt(r.cache_read), _fmt(r.cache_write), _fmt(r.output), _fmt(r.total), _fmt(r.tool_calls)]
             for r in rows]
    s = summarize(rows)
    foot = [f"sum ({s['requests']} requests)", "",
             _fmt(s['input']), _fmt(s['cache_read']), _fmt(s['cache_write']), _fmt(s['output']), _fmt(s['total']), _fmt(s['tool_calls'])]
    widths = [max(len(headers[i]), *(len(r[i]) for r in body), len(foot[i])) for i in range(len(headers))]
    lines = [_line(headers, widths, right)]
    lines += [_line(r, widths, right) for r in body]
    lines.append(_line(foot, widths, right))
    return "\n".join(lines)

def ab_table_markdown(a: dict, b: dict) -> str:
    lines = ["| | A | B | B/A |", "|---|---|---|---|"]
    for k in ("total", "requests", "tool_calls", "input", "cache_read", "cache_write", "output"):
        av, bv = a.get(k), b.get(k)
        ratio = f"{bv / av:.2f}" if (av not in (None, 0) and bv is not None) else "-"
        lines.append(f"| {LABELS[k]} | {_fmt(av)} | {_fmt(bv)} | {ratio} |")
    return "\n".join(lines)

def ab_table_human(a: dict, b: dict) -> str:
    rows = []
    for k in ("total", "requests", "tool_calls", "input", "cache_read", "cache_write", "output"):
        av, bv = a.get(k), b.get(k)
        ratio = f"{bv / av:.2f}" if (av not in (None, 0) and bv is not None) else "-"
        rows.append([LABELS[k], _fmt(av), _fmt(bv), ratio])
    headers = ["metric", "A", "B", "B/A"]
    right = {1, 2, 3}
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))]
    lines = [_line(headers, widths, right)]
    lines += [_line(r, widths, right) for r in rows]
    return "\n".join(lines)

def _read(args) -> list[Row]:
    if args.agent == "claude-code":
        if args.since:
            try:
                date.fromisoformat(args.since)
            except ValueError:
                sys.exit(f"--since must be a valid ISO date, got {args.since}")
        from graphkit.readers.claude_code import read_claude_code, transcripts_for
        if not args.project:
            sys.exit("measure --agent claude-code needs --project <repo>")
        return read_claude_code(transcripts_for(Path(args.project), args.since))
    if not args.file:
        sys.exit(f"measure --agent {args.agent} needs --file <export>")
    if args.agent == "copilot":
        from graphkit.readers.copilot import read_copilot
        return read_copilot(Path(args.file))
    from graphkit.readers.cursor import read_cursor
    return read_cursor(Path(args.file))

def _ab_load(path: str) -> dict:
    """One arm of an A/B: the object `measure --json` writes, with its summary."""
    try:
        d = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        sys.exit(f"--ab: cannot read {path}: {e}")
    if not isinstance(d, dict) or not isinstance(d.get("summary"), dict):
        sys.exit(f"--ab: {path} is not a `measure --json` output (no summary object)")
    return d

def cmd_measure(args) -> int:
    if args.ab:
        a, b = _ab_load(args.ab[0]), _ab_load(args.ab[1])
        if a.get("agent") and b.get("agent") and a["agent"] != b["agent"]:
            print(f"warning: A was measured on {a['agent']} and B on {b['agent']}; "
                  "the arms are not comparable", file=sys.stderr)
        print(ab_table_markdown(a["summary"], b["summary"]) if args.markdown else ab_table_human(a["summary"], b["summary"]))
        print(f"A: {_filters_line(a)}")
        print(f"B: {_filters_line(b)}")
        return 0
    if not args.agent:
        sys.exit("measure needs --agent or --ab")
    rows = _read(args)
    if args.from_ or args.to:
        undated = sum(1 for r in rows if r.ts is None)
        rows = in_window(rows, parse_when(args.from_), parse_when(args.to))
        if undated:
            print(f"{undated} rows had no parsable timestamp and were excluded from the window",
                  file=sys.stderr)
    filters = {"exclude_session": list(args.exclude_session or []), "model": args.model or None}
    rows = apply_filters(rows, filters["exclude_session"], filters["model"])
    if args.json:
        print(json.dumps({"agent": args.agent, "filters": filters, "summary": summarize(rows),
                          "rows": [r.to_dict() for r in rows]}, indent=1))
    else:
        print(table_markdown(rows) if args.markdown else table_human(rows))
        print()
        print(breakdown(rows))
    return 0
