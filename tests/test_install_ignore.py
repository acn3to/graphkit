"""The .gitignore rule: added inside markers, and the file removed only if the kit made it."""
from pathlib import Path

from graphkit.install import ignore_graph, unignore_graph, ignore_graph_inputs, unignore_graph_inputs
from graphkit.verify import SELF_IGNORE_RULES


def test_pre_existing_rule_outside_the_block_is_not_duplicated(tmp_path):
    """The repo's own .gitignore already ignoring graphify-out/ must not gain a second copy."""
    gi = tmp_path / ".gitignore"
    gi.write_text("node_modules/\ngraphify-out/\n")
    ignore_graph(tmp_path, commit_graph=False)
    text = gi.read_text()
    assert text.count("graphify-out/\n") == 1
    unignore_graph(tmp_path)
    assert gi.read_text() == "node_modules/\ngraphify-out/\n"


def test_all_wanted_lines_already_present_still_writes_a_marker_block(tmp_path):
    """Uninstall/idempotency stay symmetric even when there is nothing new to add."""
    gi = tmp_path / ".gitignore"
    gi.write_text("graphify-out/\n")
    assert ignore_graph(tmp_path, commit_graph=False) is True
    assert "already ignored before graphkit install" in gi.read_text()
    assert unignore_graph(tmp_path) is True
    assert gi.read_text() == "graphify-out/\n"


def test_graphifyignore_round_trips_on_install_and_uninstall(tmp_path):
    assert ignore_graph_inputs(tmp_path) is True
    gi = tmp_path / ".graphifyignore"
    text = gi.read_text()
    assert all(line in text for line in SELF_IGNORE_RULES)
    assert "created" in text.splitlines()[0]
    assert unignore_graph_inputs(tmp_path) is True
    assert not gi.exists()


def test_graphifyignore_pre_existing_rule_is_not_duplicated(tmp_path):
    gi = tmp_path / ".graphifyignore"
    gi.write_text("graphify-out*/\n")
    ignore_graph_inputs(tmp_path)
    assert gi.read_text().count("graphify-out*/\n") == 1
    unignore_graph_inputs(tmp_path)
    assert gi.read_text() == "graphify-out*/\n"


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
