"""install and uninstall: detect, plan, graphify, build, plug, mark, ignore, verify."""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path
from graphkit import __version__, markers
from graphkit.detect import detect
from graphkit.graphify_cli import ensure_installed, build, node_count, GraphifyError
from graphkit.verify import common_checks, render

IGNORE_ALL = "graphify-out/"
IGNORE_SOME = "graphify-out/graph.html\ngraphify-out/cache/"

CREATED = "created"

def ignore_graph(repo: Path, commit_graph: bool) -> bool:
    """Append the ignore rule, recording in the marker whether the kit created .gitignore."""
    gi = repo / ".gitignore"
    note = "" if gi.exists() else CREATED
    return markers.append_block(gi, IGNORE_SOME if commit_graph else IGNORE_ALL, style="hash", note=note)

def unignore_graph(repo: Path) -> bool:
    """Remove the ignore rule, and the file itself only if the kit created it.

    Deleting whenever the leftover is whitespace-only also deleted an empty .gitignore the
    repo already had, which is a file the user committed on purpose. The start marker
    carries the word `created` instead, so the decision does not depend on the leftover.
    """
    gi = repo / ".gitignore"
    created = markers.block_note(gi, "hash") == CREATED
    removed = markers.strip_block(gi, style="hash")
    if removed and created and gi.exists():
        gi.unlink()
    return removed

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
    print(render(checks))
    return 0 if all(c.ok for c in checks) else 1

def cmd_uninstall(repo: Path, agent: str, purge: bool = False) -> int:
    from graphkit.agents import MODULES
    for line in MODULES[agent].unplug(repo):
        print(f"  {line}")
    print("  " + (".gitignore: graphkit block removed" if unignore_graph(repo) else ".gitignore: no graphkit block"))
    if purge and (repo / "graphify-out").exists():
        shutil.rmtree(repo / "graphify-out")
        print("  graphify-out/: deleted")
    return 0
