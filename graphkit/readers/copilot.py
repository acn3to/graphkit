"""VS Code Copilot Chat Debug View export (OTLP/JSON) -> Rows, one per model request span.

Open: Command Palette > "Developer: Show Chat Debug View" > download icon. Or set
github.copilot.chat.agentDebugLog.fileLogging.enabled and read the file it writes.

Attribute keys matched by regex, checked against a synthetic OTLP fixture on 2026-09-13.
Conventions: input tokens (gen_ai.usage.input_tokens, prompt_tokens); output tokens
(gen_ai.usage.output_tokens, completion_tokens); total tokens (*total_tokens); cache read
(*cache_read*tokens, *cache_hit*tokens); model (any key ending in 'model'); tool spans
(any span whose name contains 'tool'), each counted against the nearest preceding model
request in the same trace. No VS Code version yet. The first real export
replaces the fixture and may require regex adjustments.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path
from graphkit.rows import Row

_IN = re.compile(r"(input|prompt)[_.]?tokens$", re.I)
_OUT = re.compile(r"(output|completion)[_.]?tokens$", re.I)
_TOTAL = re.compile(r"total[_.]?tokens$", re.I)
_CACHE = re.compile(r"cache[_.]?(read|hit)([_.]?input)?[_.]?tokens$", re.I)
_MODEL = re.compile(r"(^|[._])model$", re.I)
_TOOL = re.compile(r"tool", re.I)

def _attrs(span: dict) -> dict:
    out = {}
    for a in span.get("attributes", []):
        v = a.get("value", {})
        if "intValue" in v:
            out[a["key"]] = int(v["intValue"])
        elif "doubleValue" in v:
            out[a["key"]] = int(v["doubleValue"])
        elif "stringValue" in v:
            out[a["key"]] = v["stringValue"]
    return out

def _find(attrs: dict, rx: re.Pattern):
    for k, v in attrs.items():
        if rx.search(k):
            return v
    return None

def _spans(doc: dict):
    for rs in doc.get("resourceSpans", []):
        for ss in rs.get("scopeSpans", []):
            yield from ss.get("spans", [])

def _start_ns(span: dict) -> int:
    try:
        return int(span.get("startTimeUnixNano") or 0)
    except (TypeError, ValueError):
        return 0

def _is_request(span: dict) -> bool:
    a = _attrs(span)
    return _find(a, _IN) is not None or _find(a, _OUT) is not None

def _tools_per_request(spans: list[dict]) -> dict[int, int] | None:
    """Tool spans counted against the request that made them, by span index.

    A trace holds one or more model requests and the tool spans they trigger. Each tool
    span belongs to the request in the same trace with the greatest start time not after
    the tool's own start, that is the nearest preceding request; a tool span that starts
    before any request in its trace is counted against the first one. Returns None when
    the export has no tool spans at all, so a Copilot build that does not emit them reads
    as unknown rather than as zero.
    """
    tool_spans = [s for s in spans if _TOOL.search(s.get("name", ""))]
    if not tool_spans:
        return None
    by_trace: dict[str, list[tuple[int, int]]] = {}
    counts: dict[int, int] = {}
    for i, s in enumerate(spans):
        if _TOOL.search(s.get("name", "")) or not _is_request(s):
            continue
        by_trace.setdefault(s.get("traceId", ""), []).append((_start_ns(s), i))
        counts[i] = 0
    for tr in by_trace.values():
        tr.sort()
    for t in tool_spans:
        reqs = by_trace.get(t.get("traceId", ""))
        if not reqs:
            continue
        start = _start_ns(t)
        owner = reqs[0][1]
        for ns, i in reqs:
            if ns <= start:
                owner = i
            else:
                break
        counts[owner] += 1
    return counts

def read_copilot(path: Path) -> list[Row]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    spans = list(_spans(doc))
    tools = _tools_per_request(spans)
    rows: list[Row] = []
    for idx, s in enumerate(spans):
        a = _attrs(s)
        inp, out = _find(a, _IN), _find(a, _OUT)
        if inp is None and out is None:
            continue
        total = _find(a, _TOTAL)
        if total is None and inp is not None and out is not None:
            total = inp + out
        ns = s.get("startTimeUnixNano")
        ts = datetime.fromtimestamp(int(ns) / 1e9, tz=timezone.utc).astimezone() if ns else None
        model = _find(a, _MODEL)
        rows.append(Row(agent="copilot", ts=ts, model=str(model) if model else None,
                        input=inp, cache_read=_find(a, _CACHE), cache_write=None, output=out, total=total,
                        tool_calls=(tools.get(idx, 0) if tools is not None else None)))
    rows.sort(key=lambda r: (r.ts is None, r.ts))
    return rows
