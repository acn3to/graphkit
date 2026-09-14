"""The only place graphkit shells out to graphify.

Observed with graphify 0.9.59 (2026-09-13): running any read
command (e.g. `graphify god-nodes --top 3`) against a repo with no
graphify-out/graph.json exits 1 and prints
`error: graph file not found: <path>/graphify-out/graph.json` on stderr.
Since graphify already signals failure via a non-zero exit code in this
case, `_run` does not need the output-scanning fallback described for the
case where a tool exits 0 while reporting an error.

Also observed: `graphify update <path>` has no `--no-viz` flag (that flag
exists only on `cluster-only` and `export html`) and `update` never writes
graphify-out/graph.html regardless of graph size, so there is nothing for
`build` to skip on a large repo. Passing `--no-viz` to `update` is a hard
CLI error (`error: unknown update option: --no-viz`), reproduced on a
clone of a real TypeScript monorepo during e2e testing.
"""
from __future__ import annotations
import json, re, shutil, subprocess, sys
from pathlib import Path
from graphkit import GRAPHIFY_PINNED

class GraphifyError(RuntimeError):
    def __init__(self, cmd: list[str], stderr: str):
        super().__init__(f"{' '.join(cmd)} failed:\n{stderr.strip()}")
        self.cmd, self.stderr = cmd, stderr

def _run(args: list[str], cwd: Path | None = None) -> str:
    cmd = ["graphify", *args]
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if r.returncode != 0:
        raise GraphifyError(cmd, r.stderr or r.stdout)
    return r.stdout

def version() -> str | None:
    if not shutil.which("graphify"):
        return None
    m = re.search(r"(\d+\.\d+\.\d+)", _run(["--version"]))
    return m.group(1) if m else None

def ensure_installed() -> str:
    v = version()
    if v is None:
        print(f"  graphify not found; installing graphifyy=={GRAPHIFY_PINNED} with uv")
        subprocess.run(["uv", "tool", "install", f"graphifyy=={GRAPHIFY_PINNED}"], check=True)
        v = version() or GRAPHIFY_PINNED
    if v != GRAPHIFY_PINNED:
        print(f"  warning: graphify {v} on PATH, kit validated with {GRAPHIFY_PINNED}", file=sys.stderr)
    return v

def graph_path(repo: Path) -> Path:
    return Path(repo) / "graphify-out" / "graph.json"

def node_count(repo: Path) -> int:
    p = graph_path(repo)
    if not p.exists():
        return 0
    g = json.loads(p.read_text(encoding="utf-8"))
    return len(g.get("nodes", []))

def build(repo: Path) -> tuple[int, int]:
    out = _run(["update", ".", "--no-cluster"], cwd=repo)
    m = re.search(r"(\d+) nodes, (\d+) edges", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    g = json.loads(graph_path(repo).read_text(encoding="utf-8"))
    return len(g.get("nodes", [])), len(g.get("links", []))

def god_nodes(repo: Path, top: int = 10) -> list[str]:
    out = _run(["god-nodes", "--top", str(top)], cwd=repo)
    return [m.group(1) for m in re.finditer(r"^\s*\d+\.\s+(.+?)\s+-\s+\d+ edges", out, re.M)]

def query(repo: Path, question: str, budget: int = 500) -> str:
    return _run(["query", question, "--budget", str(budget)], cwd=repo)

def explain(repo: Path, node: str) -> str:
    return _run(["explain", node], cwd=repo)

def install_platform(repo: Path, platform: str) -> str:
    return _run(["install", "--project", "--platform", platform], cwd=repo)

def uninstall_all(repo: Path) -> str:
    return _run(["uninstall"], cwd=repo)
