import json, subprocess
from pathlib import Path
from graphkit import agents
from graphkit.graphify_cli import GraphifyError
from graphkit.install import cmd_install, cmd_uninstall
from graphkit.verify import cmd_verify

def scratch(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("def helper():\n    return 1\n\ndef main():\n    return helper()\n")
    (tmp_path / "CLAUDE.md").write_text("# Rules\nNo emojis.\n")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(ls:*)"]}}, indent=2) + "\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], check=True)
    return tmp_path

def status(repo):
    return subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout

def test_claude_round_trip_restores_files(tmp_path, capsys):
    r = scratch(tmp_path)
    assert cmd_install(r, "claude-code", commit_graph=False, yes=True) == 0
    out = capsys.readouterr().out
    assert "--- CLAUDE.md" in out and "+## graphify" in out
    assert (r / ".claude" / "skills" / "graphify" / "SKILL.md").exists()
    claude = (r / "CLAUDE.md").read_text()
    assert claude.startswith("# Rules\nNo emojis.\n") and "## graphify" in claude
    settings = json.loads((r / ".claude" / "settings.json").read_text())
    assert settings["permissions"]["allow"] == ["Bash(ls:*)"] and "PreToolUse" in settings["hooks"]
    assert cmd_verify(r, "claude-code") == 0
    assert cmd_uninstall(r, "claude-code", purge=True) == 0
    assert status(r) == "", status(r)

def test_claude_install_records_removed_backup(tmp_path):
    r = scratch(tmp_path)
    assert cmd_install(r, "claude-code", commit_graph=False, yes=True) == 0
    stamp = json.loads((r / ".claude" / "skills" / "graphify" / ".graphkit").read_text())
    assert ".claude/settings.json" in stamp["graphify_bak_removed"]
    assert not list(r.rglob("*.graphify-bak"))

def test_claude_uninstall_keeps_user_edits(tmp_path, capsys):
    r = scratch(tmp_path)
    cmd_install(r, "claude-code", commit_graph=False, yes=True)
    (r / "CLAUDE.md").write_text((r / "CLAUDE.md").read_text() + "\nAdded by the user later.\n")
    cmd_uninstall(r, "claude-code", purge=True)
    out = capsys.readouterr().out
    assert "edited since install" in out
    assert "Added by the user later." in (r / "CLAUDE.md").read_text()
    assert not (r / ".claude" / "skills").exists()


def test_claude_leaves_foreign_skill_folder(tmp_path):
    r = scratch(tmp_path)
    skill = r / ".claude" / "skills" / "graphify"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("mine\n")
    claude_md = (r / "CLAUDE.md").read_text()
    cmd_install(r, "claude-code", commit_graph=False, yes=True)
    assert (skill / "SKILL.md").read_text() == "mine\n"
    assert not (skill / ".graphkit").exists()
    assert (r / "CLAUDE.md").read_text() == claude_md, "graphify's installer must not have run"
    cmd_uninstall(r, "claude-code", purge=True)
    assert skill.exists() and (skill / "SKILL.md").read_text() == "mine\n"


def test_install_reports_a_failing_graphify_installer_and_restores(tmp_path, monkeypatch, capsys):
    """graphify can edit files and then fail; the kit must undo that and exit 1, not traceback."""
    r = scratch(tmp_path)
    original = (r / "CLAUDE.md").read_text()

    def boom(repo, platform):
        (repo / "CLAUDE.md").write_text(original + "\njunk graphify wrote before failing\n")
        raise GraphifyError(["graphify"], "boom")

    monkeypatch.setattr(agents.claude_code, "install_platform", boom)
    assert cmd_install(r, "claude-code", commit_graph=False, yes=True) == 1
    assert "boom" in capsys.readouterr().out
    assert (r / "CLAUDE.md").read_text() == original
    assert not (r / ".claude" / "skills" / "graphify" / ".graphkit").exists()
