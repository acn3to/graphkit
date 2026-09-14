"""The .gitignore rule: added inside markers, and the file removed only if the kit made it."""
from pathlib import Path

from graphkit.install import ignore_graph, unignore_graph


def test_pre_existing_empty_gitignore_survives(tmp_path):
    gi = tmp_path / ".gitignore"
    gi.write_text("")
    assert ignore_graph(tmp_path, commit_graph=False) is True
    assert "graphify-out/" in gi.read_text()
    assert unignore_graph(tmp_path) is True
    assert gi.exists(), "an empty .gitignore the repo already had is the user's file"
    assert gi.read_text() == ""


def test_absent_gitignore_is_removed_again(tmp_path):
    gi = tmp_path / ".gitignore"
    assert ignore_graph(tmp_path, commit_graph=False) is True
    assert "created" in gi.read_text().splitlines()[0]
    assert unignore_graph(tmp_path) is True
    assert not gi.exists()


def test_existing_rules_are_kept_byte_for_byte(tmp_path):
    gi = tmp_path / ".gitignore"
    gi.write_text("node_modules/\n")
    ignore_graph(tmp_path, commit_graph=True)
    assert "graphify-out/graph.html" in gi.read_text()
    unignore_graph(tmp_path)
    assert gi.read_text() == "node_modules/\n"


def test_unignore_without_a_block_does_nothing(tmp_path):
    gi = tmp_path / ".gitignore"
    gi.write_text("node_modules/\n")
    assert unignore_graph(tmp_path) is False
    assert gi.read_text() == "node_modules/\n"
