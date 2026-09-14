import json
from pathlib import Path
from graphkit.readers.copilot import read_copilot

FIX = Path(__file__).parent / "fixtures" / "copilot_otlp.json"

def test_one_row_per_model_request():
    rows = read_copilot(FIX)
    assert len(rows) == 4
    assert all(r.agent == "copilot" for r in rows)

def test_genai_keys_and_tool_spans():
    r = read_copilot(FIX)[0]
    assert r.model == "gpt-5"
    assert (r.input, r.output, r.total) == (18000, 400, 18400)
    assert r.cache_read is None and r.cache_write is None
    assert r.tool_calls == 2
    assert r.ts is not None and r.ts.year == 2026

def test_legacy_keys_and_no_tools():
    r = read_copilot(FIX)[1]
    assert (r.input, r.output, r.total) == (2500, 150, 2650)
    assert r.tool_calls == 0

def test_no_tool_spans_anywhere_means_none(tmp_path):
    doc = {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "copilot"}, "spans": [
        {"traceId": "t1", "spanId": "s1", "name": "request", "startTimeUnixNano": "1789394400000000000",
         "attributes": [{"key": "gen_ai.usage.input_tokens", "value": {"intValue": "100"}},
                        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "50"}}]}
    ]}]}]}
    f = tmp_path / "no_tools.json"
    f.write_text(json.dumps(doc))
    r = read_copilot(f)[0]
    assert r.tool_calls is None


def test_tool_spans_go_to_the_nearest_preceding_request():
    """Trace t3: two requests, two tool spans after the first and one after the second."""
    rows = read_copilot(FIX)
    assert [r.input for r in rows[2:]] == [3000, 3500]
    assert [r.tool_calls for r in rows[2:]] == [2, 1]

def test_tool_span_before_any_request_goes_to_the_first(tmp_path):
    doc = {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "copilot"}, "spans": [
        {"traceId": "t1", "spanId": "s0", "name": "tool/read_file", "startTimeUnixNano": "1789394399000000000", "attributes": []},
        {"traceId": "t1", "spanId": "s1", "name": "request", "startTimeUnixNano": "1789394400000000000",
         "attributes": [{"key": "gen_ai.usage.input_tokens", "value": {"intValue": "100"}},
                        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "50"}}]},
        {"traceId": "t1", "spanId": "s2", "name": "request", "startTimeUnixNano": "1789394500000000000",
         "attributes": [{"key": "gen_ai.usage.input_tokens", "value": {"intValue": "200"}},
                        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "60"}}]},
    ]}]}]}
    f = tmp_path / "early_tool.json"
    f.write_text(json.dumps(doc))
    rows = read_copilot(f)
    assert [r.tool_calls for r in rows] == [1, 0]
