"""The pass/fail table. The step graphify itself does not have."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from graphkit import markers
from graphkit.graphify_cli import version, node_count, god_nodes, query, GraphifyError

SMOKE = "what are the main entry points"

@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str = ""

def render(checks: list[Check]) -> str:
    lines = ["| check | result | detail |", "|---|---|---|"]
    lines += [f"| {c.name} | {'pass' if c.ok else 'fail'} | {c.detail} |" for c in checks]
    return "\n".join(lines)

def common_checks(repo: Path, commit_graph: bool | None = None) -> list[Check]:
    out = []
    v = version()
    out.append(Check("graphify on PATH", v is not None, v or "not found"))
    n = node_count(repo)
    out.append(Check("graph built", n > 0, f"{n} nodes" if n else "graphify-out/graph.json missing or empty"))
    if n > 0:
        try:
            hubs = god_nodes(repo, top=10)
            out.append(Check("hubs look right", len(hubs) > 0, ", ".join(hubs[:3])))
        except GraphifyError as e:
            out.append(Check("hubs look right", False, str(e).splitlines()[-1]))
        try:
            q = query(repo, SMOKE, budget=500)
            out.append(Check("query answers", "NODE" in q, f"{q.count('NODE')} nodes for the smoke question"))
        except GraphifyError as e:
            out.append(Check("query answers", False, str(e).splitlines()[-1]))
    else:
        out.append(Check("hubs look right", False, "no graph"))
        out.append(Check("query answers", False, "no graph"))
    gi = repo / ".gitignore"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if commit_graph is None:
        commit_graph = "graphify-out/graph.html" in text and "graphify-out/\n" not in text
    want = "graphify-out/graph.html" if commit_graph else "graphify-out/"
    out.append(Check("ignore rule", markers.has_block(gi, "hash") and want in text, want if want in text else "missing"))
    return out

def cmd_verify(repo: Path, agent: str) -> int:
    from graphkit.agents import MODULES
    checks = common_checks(repo) + MODULES[agent].checks(repo)
    print(render(checks))
    return 0 if all(c.ok for c in checks) else 1
