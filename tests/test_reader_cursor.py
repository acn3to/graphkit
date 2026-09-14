from pathlib import Path
from graphkit.readers.cursor import read_cursor

FIX = Path(__file__).parent / "fixtures" / "cursor.csv"

def test_row_count_and_fields():
    rows = read_cursor(FIX)
    assert len(rows) == 3
    r = rows[0]
    assert r.agent == "cursor" and r.model == "claude-sonnet-5"
    assert (r.input, r.cache_read, r.cache_write, r.output, r.total) == (900, 45000, 300, 350, 46550)
    assert r.tool_calls is None
    assert r.ts is not None and r.ts.hour is not None

def test_blank_numbers_stay_none_and_us_date_parses():
    r = read_cursor(FIX)[2]
    assert r.input is None and r.total is None and r.cache_write is None
    assert r.ts is not None and (r.ts.month, r.ts.day, r.ts.year) == (9, 13, 2026)
