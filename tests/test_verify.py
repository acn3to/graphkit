import subprocess
from pathlib import Path
from graphkit.graphify_cli import build
from graphkit.verify import common_checks, render_human, Check

def scratch_ambiguous_hub(tmp_path: Path) -> Path:
    """Two classes named `Ok`, in different files, each wired up enough to tie for top hub."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text(
        "class Ok:\n"
        "    def run(self):\n"
        "        return self.helper()\n\n"
        "    def helper(self):\n"
        "        return True\n\n"
        "def make_ok():\n"
        "    return Ok().run()\n"
    )
    (tmp_path / "b.py").write_text(
        "class Ok:\n"
        "    def go(self):\n"
        "        return self.step()\n\n"
        "    def step(self):\n"
        "        return 1\n\n"
        "def make_ok2():\n"
        "    return Ok().go()\n"
    )
    return tmp_path

def test_common_checks_explains_ambiguous_hub_by_node_id(tmp_path):
    r = scratch_ambiguous_hub(tmp_path)
    build(r)
    checks = common_checks(r)
    explain_check = next(c for c in checks if c.name == "explain answers")
    assert explain_check.ok, explain_check.detail
    assert explain_check.detail in ("a_ok", "b_ok")

def test_common_checks_reports_missing_self_ignore_rule(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    build(tmp_path)
    checks = common_checks(tmp_path)
    ignore_check = next(c for c in checks if c.name == "graph self-ignore rule")
    assert ignore_check.ok is False

def test_common_checks_passes_self_ignore_rule_once_written(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    from graphkit.install import ignore_graph_inputs
    ignore_graph_inputs(tmp_path)
    build(tmp_path)
    checks = common_checks(tmp_path)
    ignore_check = next(c for c in checks if c.name == "graph self-ignore rule")
    assert ignore_check.ok is True

def test_render_human_marks_pass_and_fail_and_summarizes():
    out = render_human([Check("a", True, "fine"), Check("b", False, "broken")])
    assert "✓ a" in out
    assert "✗ b" in out
    assert "1/2 passed — failed: b" in out

def test_render_human_reports_all_passed():
    out = render_human([Check("a", True, "fine"), Check("b", True, "also fine")])
    assert "2/2 checks passed" in out

def test_render_human_truncates_long_detail():
    out = render_human([Check("explain answers", True, "x" * 200)])
    lines = out.splitlines()
    detail_line = next(l for l in lines if l.startswith(("✓", "✗")))
    assert len(detail_line) < 200
    assert detail_line.endswith("…")
