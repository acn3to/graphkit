import shutil, subprocess, sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1] / "kit.py"

def run(*args):
    return subprocess.run([sys.executable, str(KIT), *args], capture_output=True, text=True)

def test_help_lists_commands():
    r = run("--help")
    assert r.returncode == 0
    for cmd in ("install", "verify", "uninstall", "measure"):
        assert cmd in r.stdout

def test_install_requires_agent():
    r = run("install")
    assert r.returncode == 2
    assert "--agent" in r.stderr


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH")
def test_uv_run_no_project_ignores_the_target_repos_pyproject(tmp_path):
    """uv run --no-project must not sync the repo the kit is run from.

    Without --no-project, uv syncs the project it finds in the cwd first: it creates a
    .venv/ there and fails outright when a dependency cannot be resolved.
    """
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "target"\nversion = "0.0.0"\nrequires-python = ">=3.11"\n'
        'dependencies = ["this-package-does-not-exist-graphkit==99.0"]\n'
    )
    r = subprocess.run(["uv", "run", "--no-project", str(KIT), "--version"],
                       cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "graphkit" in r.stdout
    assert not (tmp_path / ".venv").exists()
