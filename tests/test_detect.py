from graphkit.detect import detect

def test_detect_empty(tmp_path):
    d = detect(tmp_path)
    assert d.copilot_instructions is None and d.cursor_rules is None and d.claude_md is None and d.graph is None

def test_detect_finds_each(tmp_path):
    (tmp_path / ".github").mkdir(); (tmp_path / ".github" / "copilot-instructions.md").write_text("x")
    (tmp_path / ".github" / "skills").mkdir()
    (tmp_path / ".cursor" / "rules").mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text("x")
    (tmp_path / ".claude").mkdir(); (tmp_path / ".claude" / "settings.json").write_text("{}")
    (tmp_path / "graphify-out").mkdir(); (tmp_path / "graphify-out" / "graph.json").write_text("{}")
    d = detect(tmp_path)
    assert d.copilot_instructions and d.copilot_skills and d.cursor_rules and d.claude_md and d.claude_settings and d.graph
    assert d.claude_skills is None and d.gitignore is None
    text = d.describe()
    assert "copilot-instructions.md: present" in text and ".cursor/rules: present" in text and "graph: present" in text
