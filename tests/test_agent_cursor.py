import subprocess
from pathlib import Path
from graphkit.install import cmd_install, cmd_uninstall
from graphkit.verify import cmd_verify

def scratch(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("def helper():\n    return 1\n\ndef main():\n    return helper()\n")
    (tmp_path / ".cursor" / "rules").mkdir(parents=True)
    (tmp_path / ".cursor" / "rules" / "team.mdc").write_text("---\nalwaysApply: true\n---\nUse pt_BR.\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], check=True)
    return tmp_path

def status(repo):
    return subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout

def test_cursor_round_trip(tmp_path, capsys):
    r = scratch(tmp_path)
    assert cmd_install(r, "cursor", commit_graph=True, yes=True) == 0
    rule = r / ".cursor" / "rules" / "graphify.mdc"
    txt = rule.read_text()
    assert txt.startswith("---\n") and "alwaysApply: true" in txt and "<!-- graphkit:start -->" in txt
    assert "Read, Grep, Glob" not in txt
    assert (r / ".cursor" / "rules" / "team.mdc").read_text().endswith("Use pt_BR.\n")
    gi = (r / ".gitignore").read_text()
    assert "graphify-out/graph.html" in gi and "graphify-out/\n" not in gi
    assert cmd_verify(r, "cursor") == 0
    assert cmd_uninstall(r, "cursor", purge=True) == 0
    assert not rule.exists()
    assert status(r) == "", status(r)

def test_cursor_rule_places_path_before_query(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "cursor", commit_graph=False, yes=True)
    rule = (r / ".cursor" / "rules" / "graphify.mdc").read_text()
    assert rule.index("graphify path") < rule.index("graphify query")

def test_cursor_rule_mentions_truncated(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "cursor", commit_graph=False, yes=True)
    rule = (r / ".cursor" / "rules" / "graphify.mdc").read_text()
    assert "[!] TRUNCATED" in rule

def test_cursor_leaves_foreign_rule(tmp_path):
    r = scratch(tmp_path)
    foreign = r / ".cursor" / "rules" / "graphify.mdc"
    foreign.write_text("---\nalwaysApply: true\n---\nsomeone else's rule\n")
    cmd_install(r, "cursor", commit_graph=False, yes=True)
    assert foreign.read_text().endswith("someone else's rule\n")
    cmd_uninstall(r, "cursor", purge=True)
    assert foreign.exists()

def test_cursor_uninstall_keeps_other_cursor_files(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("def helper():\n    return 1\n\ndef main():\n    return helper()\n")
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text("{}")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], check=True)
    r = tmp_path
    assert cmd_install(r, "cursor", commit_graph=False, yes=True) == 0
    assert cmd_uninstall(r, "cursor", purge=True) == 0
    assert (r / ".cursor" / "mcp.json").exists()
    assert not (r / ".cursor" / "rules").exists()
    assert status(r) == "", status(r)
