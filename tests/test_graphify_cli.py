import subprocess
from pathlib import Path
import pytest
from graphkit.graphify_cli import version, build, god_nodes, query, node_count, install_platform, GraphifyError, _run

def scratch(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("def helper():\n    return 1\n\ndef main():\n    return helper()\n")
    (tmp_path / "b.py").write_text("from a import main\n\ndef run():\n    return main()\n")
    return tmp_path

def test_version_is_string():
    assert version() and version()[0].isdigit()

def test_build_then_query(tmp_path):
    r = scratch(tmp_path)
    nodes, links = build(r)
    assert nodes >= 4 and links >= 2
    assert node_count(r) == nodes
    hubs = god_nodes(r, top=3)
    assert 1 <= len(hubs) <= 3 and any("main" in h for h in hubs)
    out = query(r, "what calls helper", budget=300)
    assert "helper" in out

def test_install_platform_copilot_writes_dot_copilot(tmp_path):
    r = scratch(tmp_path)
    out = install_platform(r, "copilot")
    assert (r / ".copilot" / "skills" / "graphify" / "SKILL.md").exists()

def test_error_on_bad_graph(tmp_path):
    with pytest.raises(GraphifyError):
        god_nodes(tmp_path, top=3)

def test_build_never_sends_no_viz_to_update(tmp_path):
    """e2e bug, found on a clone of a real TypeScript monorepo:
    `graphify update` has no --no-viz flag (that flag exists only on cluster-only
    and export html) and fails with 'error: unknown update option: --no-viz'.
    build() must not offer a way to send it, and the flag must still be rejected
    by graphify itself if anything ever adds it back."""
    r = scratch(tmp_path)
    with pytest.raises(TypeError):
        build(r, no_viz=True)
    with pytest.raises(GraphifyError, match="unknown update option"):
        _run(["update", ".", "--no-cluster", "--no-viz"], cwd=r)
