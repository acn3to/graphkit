"""The pass/fail table. The step graphify itself does not have."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from graphkit import markers
from graphkit.term import GREEN, RED, RESET, color_enabled, safe
from graphkit.graphify_cli import version, node_count, god_nodes, explain, graph_path, GraphifyError

_MAX_DETAIL = 60

# The rules graphkit writes to .graphifyignore so graphify never indexes its own
# output or the skills/rules the kit installed. Kept here so verify can confirm what
# install.py wrote without importing install (which imports verify).
SELF_IGNORE_RULES = (
    "graphify-out*/",
    ".github/skills/graphify/",
    ".copilot/skills/graphify/",
    ".agents/skills/graphify/",
    ".claude/skills/graphify/",
    ".cursor/rules/graphify.mdc",
)

@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str = ""

def render_markdown(checks: list[Check]) -> str:
    lines = ["| check | result | detail |", "|---|---|---|"]
    lines += [f"| {c.name} | {'pass' if c.ok else 'fail'} | {c.detail} |" for c in checks]
    return "\n".join(lines)

def _truncate(detail: str) -> str:
    if len(detail) <= _MAX_DETAIL:
        return detail
    return detail[:_MAX_DETAIL - 1].rstrip() + "…"

def render_human(checks: list[Check]) -> str:
    green, red, reset = (GREEN, RED, RESET) if color_enabled() else ("", "", "")
    width = max((len(c.name) for c in checks), default=0)
    lines = []
    for c in checks:
        mark = f"{green}✓{reset}" if c.ok else f"{red}✗{reset}"
        lines.append(f"{mark} {c.name.ljust(width)}  {_truncate(c.detail)}")
    passed = sum(1 for c in checks if c.ok)
    total = len(checks)
    if passed == total:
        lines.append(f"\n{passed}/{total} checks passed")
    else:
        failed = ", ".join(c.name for c in checks if not c.ok)
        lines.append(f"\n{passed}/{total} passed — failed: {failed}")
    return safe("\n".join(lines))

def _candidate_node_ids(repo: Path, label: str) -> list[str]:
    """Node ids sharing `label`, real source files sorted before tests/agent config folders."""
    g = json.loads(graph_path(repo).read_text(encoding="utf-8"))
    matches = [n for n in g.get("nodes", []) if n.get("label") == label and n.get("id")]
    noise = ("test", ".claude/", ".github/", ".cursor/", ".copilot/", ".agents/")
    def score(n: dict) -> int:
        sf = (n.get("source_file") or "").replace("\\", "/").lower()
        return sum(1 for m in noise if m in sf)
    matches.sort(key=score)
    return [n["id"] for n in matches]

def _explain_check(repo: Path, hubs: list[str]) -> Check:
    if not hubs:
        return Check("explain answers", False, "no hubs")
    label = hubs[0]
    try:
        explain(repo, label)
        return Check("explain answers", True, label)
    except GraphifyError as e:
        msg = str(e)
        if "Ambiguous" not in msg:
            return Check("explain answers", False, msg.splitlines()[-1])
        for node_id in _candidate_node_ids(repo, label):
            try:
                explain(repo, node_id)
                return Check("explain answers", True, node_id)
            except GraphifyError:
                continue
        return Check("explain answers", False, f"ambiguous label {label!r}, no candidate id resolved")

def _self_ignore_check(repo: Path) -> Check:
    gi = repo / ".graphifyignore"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    missing = [line for line in SELF_IGNORE_RULES if line not in text]
    return Check("graph self-ignore rule", not missing, "complete" if not missing else f"missing {', '.join(missing)}")

def common_checks(repo: Path, commit_graph: bool | None = None) -> list[Check]:
    out = []
    v = version()
    out.append(Check("graphify on PATH", v is not None, v or "not found"))
    n = node_count(repo)
    out.append(Check("graph built", n > 0, f"{n} nodes" if n else "graphify-out/graph.json missing or empty"))
    if n > 0:
        hubs: list[str] = []
        try:
            hubs = god_nodes(repo, top=10)
            out.append(Check("hubs look right", len(hubs) > 0, ", ".join(hubs[:3])))
        except GraphifyError as e:
            out.append(Check("hubs look right", False, str(e).splitlines()[-1]))
        out.append(_explain_check(repo, hubs))
    else:
        out.append(Check("hubs look right", False, "no graph"))
        out.append(Check("explain answers", False, "no graph"))
    gi = repo / ".gitignore"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if commit_graph is None:
        commit_graph = "graphify-out/graph.html" in text and "graphify-out/\n" not in text
    want = "graphify-out/graph.html" if commit_graph else "graphify-out/"
    out.append(Check("ignore rule", markers.has_block(gi, "hash") and want in text, want if want in text else "missing"))
    out.append(_self_ignore_check(repo))
    return out

def cmd_verify(repo: Path, agent: str, markdown: bool = False) -> int:
    from graphkit.agents import MODULES
    checks = common_checks(repo) + MODULES[agent].checks(repo)
    print(render_markdown(checks) if markdown else render_human(checks))
    return 0 if all(c.ok for c in checks) else 1
