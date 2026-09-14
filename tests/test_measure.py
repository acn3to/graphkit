import json, subprocess, sys
from argparse import Namespace
from datetime import datetime
from pathlib import Path

import pytest

from graphkit import measure
from graphkit.rows import Row
from graphkit.measure import cmd_measure, in_window, summarize, ab_table, parse_when

KIT = Path(__file__).resolve().parents[1] / "kit.py"
FIX = Path(__file__).parent / "fixtures"

def row(h, m, total=100, tools=None):
    ts = datetime(2026, 9, 13, h, m).astimezone()
    return Row("x", ts, "m", 10, 80, 0, 10, total, tools)

def test_window_is_inclusive_start_exclusive_end():
    rows = [row(14, 0), row(14, 10), row(14, 20)]
    day = datetime(2026, 9, 13).astimezone()
    got = in_window(rows, parse_when("14:00", day), parse_when("14:20", day))
    assert [r.ts.minute for r in got] == [0, 10]

def test_summarize_keeps_none_when_all_none():
    s = summarize([row(1, 0, tools=None), row(1, 1, tools=None)])
    assert s["requests"] == 2 and s["total"] == 200 and s["tool_calls"] is None
    s2 = summarize([row(1, 0, tools=3), row(1, 1, tools=None)])
    assert s2["tool_calls"] == 3

def test_ab_table_ratio_and_dash():
    a = summarize([row(1, 0, 1000, 5)]); b = summarize([row(1, 0, 400, None)])
    out = ab_table(a, b)
    assert "| total tokens | 1000 | 400 | 0.40 |" in out
    assert "| tool calls | 5 | - | - |" in out

def test_cli_json_then_ab(tmp_path):
    a = tmp_path / "a.json"; b = tmp_path / "b.json"
    r = subprocess.run([sys.executable, str(KIT), "measure", "--agent", "cursor", "--file", str(FIX / "cursor.csv"), "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    a.write_text(r.stdout); b.write_text(r.stdout)
    r2 = subprocess.run([sys.executable, str(KIT), "measure", "--ab", str(a), str(b)], capture_output=True, text=True)
    assert r2.returncode == 0 and "| B/A |" in r2.stdout and "| 1.00 |" in r2.stdout


def args(**kw) -> Namespace:
    base = dict(agent=None, project=None, file=None, since=None, from_=None, to=None, ab=None, json=False,
                exclude_session=None, model=None)
    return Namespace(**{**base, **kw})


def test_rows_without_a_timestamp_are_reported_not_silently_dropped(monkeypatch, capsys):
    """A locale-sensitive Cursor date can window every row away; say so, do not print zero."""
    now = datetime.now().astimezone()
    dated = Row("cursor", now, "m", 10, 0, 0, 10, 20, None)
    undated = Row("cursor", None, "m", 10, 0, 0, 10, 20, None)
    monkeypatch.setattr(measure, "_read", lambda a: [dated, undated])
    assert cmd_measure(args(agent="cursor", file="usage.csv", from_="00:00")) == 0
    out = capsys.readouterr()
    assert "1 rows had no parsable timestamp and were excluded from the window" in out.err
    assert "(1 requests)" in out.out


def test_ab_warns_when_the_two_arms_are_different_agents(tmp_path, capsys):
    s = summarize([row(1, 0)])
    a = tmp_path / "a.json"; a.write_text(json.dumps({"agent": "copilot", "summary": s}))
    b = tmp_path / "b.json"; b.write_text(json.dumps({"agent": "cursor", "summary": s}))
    assert cmd_measure(args(ab=[str(a), str(b)])) == 0
    err = capsys.readouterr().err
    assert "copilot" in err and "cursor" in err and "not comparable" in err


def test_ab_exits_with_one_line_on_a_file_that_is_not_measure_json(tmp_path, capsys):
    bad = tmp_path / "bad.json"; bad.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(SystemExit) as e:
        cmd_measure(args(ab=[str(bad), str(bad)]))
    assert "not a `measure --json` output" in str(e.value)


def srow(session, model="claude-sonnet-5", total=100, minute=0):
    ts = datetime(2026, 9, 13, 14, minute).astimezone()
    return Row("claude-code", ts, model, 10, 80, 0, 10, total, 1, session=session)


def test_exclude_session_drops_that_session_after_the_window(monkeypatch, capsys):
    """The driver session lands in the window; --exclude-session takes it out of the arm."""
    day = datetime(2026, 9, 13).astimezone()
    monkeypatch.setattr(measure, "parse_when", lambda s, d=None: parse_when(s, day))
    rows = [srow("run-1", total=100, minute=5), srow("driver", "claude-opus-5", total=5000, minute=6),
            srow("run-1", total=100, minute=30)]
    monkeypatch.setattr(measure, "_read", lambda a: rows)
    assert cmd_measure(args(agent="claude-code", project=".", from_="14:00", to="14:20",
                            exclude_session=["driver"], json=True)) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["summary"]["requests"] == 1 and d["summary"]["total"] == 100
    assert d["filters"] == {"exclude_session": ["driver"], "model": None}


def test_model_filter_is_a_case_insensitive_substring(monkeypatch, capsys):
    rows = [srow("run-1", "claude-sonnet-5", total=100), srow("driver", "claude-opus-5", total=5000)]
    monkeypatch.setattr(measure, "_read", lambda a: rows)
    assert cmd_measure(args(agent="claude-code", project=".", model="SONNET", json=True)) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["summary"]["total"] == 100
    assert d["filters"] == {"exclude_session": [], "model": "SONNET"}
    assert d["rows"][0]["session"] == "run-1"


def test_measure_output_ends_with_a_per_session_breakdown(monkeypatch, capsys):
    """A driver contaminating the window must be visible without any flag."""
    rows = [srow("run-1", total=100), srow("run-1", total=100), srow("driver", "claude-opus-5", total=5000)]
    monkeypatch.setattr(measure, "_read", lambda a: rows)
    assert cmd_measure(args(agent="claude-code", project=".")) == 0
    out = capsys.readouterr().out.rstrip().splitlines()
    assert out[-3].startswith("sessions in window")
    assert out[-2].split() == ["driver", "claude-opus-5", "1", "5000"]
    assert out[-1].split() == ["run-1", "claude-sonnet-5", "2", "200"]


def test_ab_output_carries_the_filters_of_each_arm(tmp_path, capsys):
    s = summarize([srow("run-1")])
    a = tmp_path / "a.json"; a.write_text(json.dumps({"agent": "claude-code", "summary": s,
                                                       "filters": {"exclude_session": ["driver"], "model": None}}))
    b = tmp_path / "b.json"; b.write_text(json.dumps({"agent": "claude-code", "summary": s,
                                                       "filters": {"exclude_session": [], "model": "sonnet"}}))
    assert cmd_measure(args(ab=[str(a), str(b)])) == 0
    out = capsys.readouterr().out
    assert "A: exclude_session=driver model=-" in out
    assert "B: exclude_session=- model=sonnet" in out


def test_cli_accepts_the_repeatable_filter_flags():
    r = subprocess.run([sys.executable, str(KIT), "measure", "--agent", "cursor", "--file", str(FIX / "cursor.csv"),
                        "--exclude-session", "x", "--exclude-session", "y", "--model", "gpt", "--json"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["filters"]["exclude_session"] == ["x", "y"]
