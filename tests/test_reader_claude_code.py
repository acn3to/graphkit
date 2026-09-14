import os
import re
from datetime import datetime
from pathlib import Path
from graphkit.readers.claude_code import read_claude_code, transcripts_for
from graphkit.rows import Row

import pytest

FIX = Path(__file__).parent / "fixtures" / "claude_code.jsonl"

def test_one_row_per_assistant_message():
    rows = read_claude_code([FIX])
    assert len(rows) == 3
    assert all(isinstance(r, Row) and r.agent == "claude-code" for r in rows)

def test_known_row_fields():
    r = read_claude_code([FIX])[1]
    assert r.model == "claude-opus-5"
    assert (r.input, r.cache_read, r.cache_write, r.output) == (10, 30600, 0, 90)
    assert r.total == 10 + 30600 + 0 + 90
    assert r.tool_calls == 2
    assert r.ts is not None and r.ts.tzinfo is not None

def test_missing_usage_block_is_none():
    r = read_claude_code([FIX])[2]
    assert r.model == "claude-opus-5"
    assert (r.input, r.cache_read, r.cache_write, r.output, r.total) == (None, None, None, None, None)
    assert r.tool_calls == 1

def test_round_trip_dict_keeps_none():
    r = Row(agent="x", ts=None, model=None, input=None, cache_read=None, cache_write=None, output=None, total=None, tool_calls=None)
    assert Row.from_dict(r.to_dict()) == r

def test_transcripts_for_maps_project_to_slug(tmp_path, monkeypatch):
    home = tmp_path / "home"; monkeypatch.setenv("HOME", str(home))
    proj = tmp_path / "work" / "my_repo.v2"; proj.mkdir(parents=True)
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(proj.resolve()))
    d = home / ".claude" / "projects" / slug; d.mkdir(parents=True)
    (d / "a.jsonl").write_text('{"type":"user","timestamp":"2026-09-01T00:00:00Z","message":{"content":"hi"}}\n')
    (d / "b.jsonl").write_text('{"type":"user","timestamp":"2026-09-13T00:00:00Z","message":{"content":"hi"}}\n')
    assert [p.name for p in transcripts_for(proj, since=None)] == ["a.jsonl", "b.jsonl"]
    assert [p.name for p in transcripts_for(proj, since="2026-09-10")] == ["b.jsonl"]


def test_transcripts_for_honors_home_even_if_expanduser_ignores_it(tmp_path, monkeypatch):
    """Native Windows: os.path.expanduser('~') can ignore a patched HOME (it resolves via
    USERPROFILE/other logic instead), which silently dropped a test's HOME there. The reader
    must read HOME directly and not depend on expanduser at all."""
    home = tmp_path / "home"; monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path / "wrong"))
    proj = tmp_path / "work" / "my_repo"; proj.mkdir(parents=True)
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(proj.resolve()))
    d = home / ".claude" / "projects" / slug; d.mkdir(parents=True)
    (d / "a.jsonl").write_text('{"type":"user","timestamp":"2026-09-01T00:00:00Z","message":{"content":"hi"}}\n')
    assert [p.name for p in transcripts_for(proj, since=None)] == ["a.jsonl"]


def test_transcripts_for_missing_directory_exits(tmp_path, monkeypatch):
    """measure must say so, not report an empty window as zero usage."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    proj = tmp_path / "never" / "measured"; proj.mkdir(parents=True)
    with pytest.raises(SystemExit) as e:
        transcripts_for(proj, since=None)
    assert "no transcripts at" in str(e.value)


def test_each_row_carries_its_session_id_from_the_transcript_stem():
    """A driver session that spans both A/B arms can only be excluded by its id."""
    rows = read_claude_code([FIX])
    assert all(r.session == "claude_code" for r in rows)


def test_from_dict_without_session_defaults_to_none():
    """measure --json files written before the field existed still load for --ab."""
    d = Row(agent="x", ts=None, model=None, input=None, cache_read=None, cache_write=None,
            output=None, total=None, tool_calls=None).to_dict()
    del d["session"]
    assert Row.from_dict(d).session is None
