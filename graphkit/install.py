"""install and uninstall: detect, plan, graphify, build, plug, mark, ignore, verify."""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path
from graphkit import __version__, markers
from graphkit.detect import detect
from graphkit.graphify_cli import ensure_installed, build, node_count, GraphifyError
from graphkit.verify import common_checks, render_human, SELF_IGNORE_RULES

IGNORE_ALL = ("graphify-out/",)
IGNORE_SOME = ("graphify-out/graph.html", "graphify-out/cache/")

CREATED = "created"
ALREADY_IGNORED_NOTE = "# graphify output was already ignored before graphkit install"

def _missing_lines(path: Path, lines: tuple[str, ...]) -> list[str]:
    """The `lines` not already present anywhere in `path` (outside any graphkit block)."""
    if not path.exists():
        return list(lines)
    existing = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    return [line for line in lines if line not in existing]

def _block_text(missing: list[str]) -> str:
    """The text to fence: the still-missing lines, or a note when every wanted line was already there.

    Writing the block even when nothing is missing keeps install/uninstall symmetric (the
    marker note still tracks whether the kit created the file) without duplicating a line
    the repo already had outside the kit's block.
    """
    return "\n".join(missing) if missing else ALREADY_IGNORED_NOTE

def _append_ignore_block(path: Path, lines: tuple[str, ...]) -> bool:
    note = "" if path.exists() else CREATED
    return markers.append_block(path, _block_text(_missing_lines(path, lines)), style="hash", note=note)

def _remove_ignore_block(path: Path) -> bool:
    """Remove the block, and the file itself only if the kit created it.

    Deleting whenever the leftover is whitespace-only also deleted an empty file the
    repo already had, which is a file the user committed on purpose. The start marker
    carries the word `created` instead, so the decision does not depend on the leftover.
    """
    created = markers.block_note(path, "hash") == CREATED
    removed = markers.strip_block(path, style="hash")
    if removed and created and path.exists():
        path.unlink()
    return removed

def ignore_graph(repo: Path, commit_graph: bool) -> bool:
    """Append the ignore rule, recording in the marker whether the kit created .gitignore."""
    return _append_ignore_block(repo / ".gitignore", IGNORE_SOME if commit_graph else IGNORE_ALL)

def unignore_graph(repo: Path) -> bool:
    """Remove the ignore rule, and .gitignore itself only if the kit created it."""
    return _remove_ignore_block(repo / ".gitignore")

def ignore_graph_inputs(repo: Path) -> bool:
    """Write graphify's own self-ignore rules to .graphifyignore, so graphify does not index
    its own output (graphify-out/) or the skills/rules the kit just installed."""
    return _append_ignore_block(repo / ".graphifyignore", SELF_IGNORE_RULES)

def unignore_graph_inputs(repo: Path) -> bool:
    """Remove the graphkit block from .graphifyignore, and the file itself only if the kit created it."""
    return _remove_ignore_block(repo / ".graphifyignore")

def cmd_install(repo: Path, agent: str, commit_graph: bool = False, yes: bool = False) -> int:
    from graphkit.agents import MODULES
    mod = MODULES[agent]
    d = detect(repo)
    print(f"graphkit {__version__} install --agent {agent} in {repo}\n\nfound:\n{d.describe()}\n\nwill:")
    for line in mod.PLAN(repo, d):
        print(f"  {line}")
    print("  append graphify-out ignore rule to .gitignore" if not markers.has_block(repo / ".gitignore", "hash") else "  .gitignore: already installed")
    print("  build graphify-out/graph.json (code only, no LLM)" if not d.graph else "  graph: present, not rebuilt")
    if not yes:
        input("\nEnter to continue, Ctrl-C to stop. ")
    print("\n1. graphify")
    try:
        print(f"  graphify {ensure_installed()}")
        print("2. graph")
        print("  " + (".graphifyignore: appended" if ignore_graph_inputs(repo) else ".graphifyignore: already installed"))
        if not d.graph:
            nodes, links = build(repo)
            print(f"  {nodes} nodes, {links} edges")
        else:
            print(f"  {node_count(repo)} nodes, kept")
    except (GraphifyError, subprocess.CalledProcessError) as e:
        print(f"  {e}")
        return 1
    print("3. plug in")
    try:
        meta = {"kit": __version__, "graphify": ensure_installed(), "agent": agent}
        for line in mod.plug(repo, meta):
            print(f"  {line}")
    except (GraphifyError, subprocess.CalledProcessError) as e:
        print(f"  {e}")
        return 1
    print("4. ignore")
    print("  " + (".gitignore: appended" if ignore_graph(repo, commit_graph) else ".gitignore: already installed"))
    print("5. verify")
    checks = common_checks(repo, commit_graph) + mod.checks(repo)
    print(render_human(checks))
    return 0 if all(c.ok for c in checks) else 1

def cmd_uninstall(repo: Path, agent: str, purge: bool = False) -> int:
    from graphkit.agents import MODULES
    for line in MODULES[agent].unplug(repo):
        print(f"  {line}")
    print("  " + (".gitignore: graphkit block removed" if unignore_graph(repo) else ".gitignore: no graphkit block"))
    print("  " + (".graphifyignore: graphkit block removed" if unignore_graph_inputs(repo) else ".graphifyignore: no graphkit block"))
    if purge and (repo / "graphify-out").exists():
        shutil.rmtree(repo / "graphify-out")
        print("  graphify-out/: deleted")
    return 0
