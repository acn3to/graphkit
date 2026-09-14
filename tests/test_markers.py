from graphkit.markers import append_block, block_note, strip_block, has_block, write_stamp, read_stamp, STAMP

def test_html_block_round_trip(tmp_path):
    f = tmp_path / "x.md"; f.write_text("# mine\nkeep me\n")
    assert append_block(f, "added line") is True
    assert has_block(f)
    assert append_block(f, "added line") is False
    assert f.read_text().count("<!-- graphkit:start sep=1 -->") == 1
    assert strip_block(f) is True
    assert f.read_text() == "# mine\nkeep me\n"
    assert strip_block(f) is False

def test_hash_style_for_gitignore(tmp_path):
    f = tmp_path / ".gitignore"; f.write_text("node_modules/\n")
    append_block(f, "graphify-out/", style="hash")
    assert "# graphkit:start sep=1\ngraphify-out/\n# graphkit:end" in f.read_text()
    strip_block(f, style="hash")
    assert f.read_text() == "node_modules/\n"

def test_round_trip_preserves_missing_trailing_newline(tmp_path):
    f = tmp_path / "x.md"; f.write_text("a")
    append_block(f, "added line")
    strip_block(f)
    assert f.read_text() == "a"

def test_round_trip_preserves_double_trailing_newline(tmp_path):
    f = tmp_path / "x.md"; f.write_text("a\n\n")
    append_block(f, "added line")
    strip_block(f)
    assert f.read_text() == "a\n\n"

def test_append_creates_missing_file(tmp_path):
    f = tmp_path / "new.md"
    append_block(f, "hello")
    assert f.exists() and has_block(f)

def test_stamp(tmp_path):
    write_stamp(tmp_path, {"kit": "0.1.0"})
    assert (tmp_path / STAMP).exists()
    assert read_stamp(tmp_path) == {"kit": "0.1.0"}
    assert read_stamp(tmp_path / "nope") is None


def test_prose_mentioning_marker_is_not_a_block(tmp_path):
    """The file is the user's: writing about graphkit:start must not read as an install."""
    f = tmp_path / "notes.md"
    original = "# Notes\nThe kit fences what it adds with graphkit:start and graphkit:end.\n"
    f.write_text(original)
    assert has_block(f) is False
    assert append_block(f, "added line") is True
    assert strip_block(f) is True
    assert f.read_text() == original

def test_near_miss_marker_is_ignored(tmp_path):
    """A line that only looks like the marker must not be parsed as one."""
    f = tmp_path / "notes.md"
    original = "# Notes\n<!-- graphkit:startup -->\nkeep me\n"
    f.write_text(original)
    assert has_block(f) is False
    assert strip_block(f) is False
    assert f.read_text() == original

def test_start_without_end_leaves_the_file_alone(tmp_path):
    f = tmp_path / "notes.md"
    original = "# Notes\n<!-- graphkit:start sep=1 -->\nhalf a block, no end marker\n"
    f.write_text(original)
    assert has_block(f) is False
    assert strip_block(f) is False
    assert f.read_text() == original

def test_extra_word_after_sep_is_parsed_and_read_back(tmp_path):
    f = tmp_path / ".gitignore"
    append_block(f, "graphify-out/", style="hash", note="created")
    assert "# graphkit:start sep=0 created\n" in f.read_text()
    assert has_block(f, "hash") and block_note(f, "hash") == "created"
    assert block_note(tmp_path / "nope", "hash") == ""
    assert strip_block(f, style="hash") is True
    assert f.read_text() == ""
