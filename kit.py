#!/usr/bin/env python3
"""graphkit: install, plug in, verify and measure graphify on a coding-agent repo.

    uv run --no-project <graphkit>/kit.py install   --agent copilot|cursor|claude-code [--commit-graph] [--yes] [--repo PATH]
    uv run --no-project <graphkit>/kit.py verify    --agent ... [--repo PATH]
    uv run --no-project <graphkit>/kit.py uninstall --agent ... [--purge] [--repo PATH]
    uv run --no-project <graphkit>/kit.py measure   --agent ... (--project PATH | --file PATH) [--from HH:MM] [--to HH:MM] [--exclude-session ID]... [--model NAME] [--json]
    uv run --no-project <graphkit>/kit.py measure   --ab A.json B.json

--no-project keeps uv from syncing the target repo's own pyproject.toml; python3 <graphkit>/kit.py
is the equivalent fallback, since the kit is stdlib only.
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graphkit import AGENTS, __version__


def build_parser():
    p = argparse.ArgumentParser(prog="kit.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"graphkit {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--agent", required=True, choices=AGENTS)
        sp.add_argument("--repo", default=".", help="target repo root (default: cwd)")

    i = sub.add_parser("install", help="plug graphify into the repo for one agent, then verify")
    common(i)
    i.add_argument("--commit-graph", action="store_true", help="ignore only graph.html and cache/, keep graph.json reviewable")
    i.add_argument("--yes", action="store_true", help="do not wait for Enter after printing the plan")

    v = sub.add_parser("verify", help="pass/fail table for one agent")
    common(v)

    u = sub.add_parser("uninstall", help="remove exactly what install added")
    common(u)
    u.add_argument("--purge", action="store_true", help="also delete graphify-out/")

    m = sub.add_parser("measure", help="token rows from an agent log, optional A/B")
    m.add_argument("--agent", choices=AGENTS)
    m.add_argument("--project", help="claude-code: repo path whose transcripts to read")
    m.add_argument("--file", help="copilot: OTLP JSON export; cursor: usage CSV")
    m.add_argument("--since", help="claude-code: skip transcripts starting before this ISO date")
    m.add_argument("--from", dest="from_", help="window start, HH:MM or ISO datetime, local")
    m.add_argument("--to", help="window end, HH:MM or ISO datetime, local")
    m.add_argument("--exclude-session", action="append", default=[], metavar="ID",
                   help="drop rows from this session id (repeatable); applied after the window")
    m.add_argument("--model", help="keep only rows whose model contains NAME, case-insensitive; applied after the window")
    m.add_argument("--ab", nargs=2, metavar=("A_JSON", "B_JSON"), help="two measure --json outputs to compare")
    m.add_argument("--json", action="store_true")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.command == "install":
        from graphkit.install import cmd_install
        return cmd_install(Path(a.repo).resolve(), a.agent, commit_graph=a.commit_graph, yes=a.yes)
    if a.command == "verify":
        from graphkit.verify import cmd_verify
        return cmd_verify(Path(a.repo).resolve(), a.agent)
    if a.command == "uninstall":
        from graphkit.install import cmd_uninstall
        return cmd_uninstall(Path(a.repo).resolve(), a.agent, purge=a.purge)
    if a.command == "measure":
        from graphkit.measure import cmd_measure
        return cmd_measure(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())
