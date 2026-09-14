import subprocess
from pathlib import Path
from graphkit.install import cmd_install, cmd_uninstall
from graphkit.verify import cmd_verify
from graphkit.agents import copilot as copilot_agent

def scratch(tmp_path: Path, gitignore_text: str = "node_modules/\n") -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("def helper():\n    return 1\n\ndef main():\n    return helper()\n")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("# Team rules\nUse pt_BR in UI copy.\n")
    (tmp_path / ".gitignore").write_text(gitignore_text)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], check=True)
    return tmp_path

def status(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout

def test_install_verify_uninstall_clean(tmp_path, capsys):
    r = scratch(tmp_path)
    assert cmd_install(r, "copilot", commit_graph=False, yes=True) == 0
    assert (r / ".github" / "skills" / "graphify" / "SKILL.md").exists()
    assert (r / ".github" / "skills" / "graphify" / ".graphkit").exists()
    ins = (r / ".github" / "copilot-instructions.md").read_text()
    assert ins.startswith("# Team rules\nUse pt_BR in UI copy.\n") and "<!-- graphkit:start" in ins
    assert "graphify-out/" in (r / ".gitignore").read_text()
    assert not (r / ".copilot").exists()
    assert cmd_verify(r, "copilot") == 0
    out = capsys.readouterr().out
    assert "| skill where the agent reads | pass |" in out
    assert cmd_uninstall(r, "copilot", purge=True) == 0
    assert status(r) == "", status(r)

def test_install_is_idempotent(tmp_path, capsys):
    r = scratch(tmp_path)
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    before = (r / ".github" / "copilot-instructions.md").read_text()
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    assert (r / ".github" / "copilot-instructions.md").read_text() == before
    assert "already installed" in capsys.readouterr().out

def test_verify_fails_on_untouched_repo(tmp_path, capsys):
    r = scratch(tmp_path)
    assert cmd_verify(r, "copilot") == 1
    assert "| graph built | fail |" in capsys.readouterr().out

def test_uninstall_clean_when_gitignore_has_no_trailing_newline(tmp_path, capsys):
    r = scratch(tmp_path, gitignore_text="node_modules/")
    assert cmd_install(r, "copilot", commit_graph=False, yes=True) == 0
    assert cmd_uninstall(r, "copilot", purge=True) == 0
    assert status(r) == "", status(r)


def test_copilot_install_includes_graphkit_default_section(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    skill = (r / ".github" / "skills" / "graphify" / "SKILL.md").read_text()
    assert copilot_agent.GRAPHKIT_DEFAULT_HEADING in skill

def test_copilot_installed_skill_drops_query_first_wording(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    skill = (r / ".github" / "skills" / "graphify" / "SKILL.md").read_text()
    assert "graphify query first" not in skill
    assert "Run `graphify query" not in skill

def test_copilot_instructions_place_path_before_query(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    ins = (r / ".github" / "copilot-instructions.md").read_text()
    assert ins.index("graphify path") < ins.index("graphify query")

def test_copilot_instructions_mention_truncated(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    ins = (r / ".github" / "copilot-instructions.md").read_text()
    assert "[!] TRUNCATED" in ins

def test_copilot_instructions_are_smallest_command_first(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    ins = (r / ".github" / "copilot-instructions.md").read_text()
    assert "graphify path" in ins and "graphify explain" in ins and "graphify affected" in ins
    assert "only when you do not yet have a concrete symbol/file pair" in ins
    assert "query first" not in ins

def test_copilot_skill_patch_is_idempotent_across_reinstall(tmp_path):
    r = scratch(tmp_path)
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    skill_path = r / ".github" / "skills" / "graphify" / "SKILL.md"
    before = skill_path.read_text()
    assert before.count(copilot_agent.GRAPHKIT_DEFAULT_HEADING) == 1
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    after = skill_path.read_text()
    assert after == before
    assert after.count(copilot_agent.GRAPHKIT_DEFAULT_HEADING) == 1

def test_copilot_leaves_foreign_skill_folder(tmp_path):
    r = scratch(tmp_path)
    skill = r / ".github" / "skills" / "graphify"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("mine\n")
    cmd_install(r, "copilot", commit_graph=False, yes=True)
    assert (skill / "SKILL.md").read_text() == "mine\n"
    assert not (skill / ".graphkit").exists()
    cmd_uninstall(r, "copilot", purge=True)
    assert skill.exists() and (skill / "SKILL.md").read_text() == "mine\n"
