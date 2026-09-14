"""Cursor: one always-on rule at .cursor/rules/graphify.mdc, from the kit's template.

graphify's own cursor target writes a rule that names Claude Code tools (Read, Grep, Glob);
the kit never runs it and ships its own wording.
"""
from __future__ import annotations
import json
from pathlib import Path
from graphkit import markers
from graphkit.detect import Detected
from graphkit.verify import Check

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
RULE = Path(".cursor") / "rules" / "graphify.mdc"
STAMP = Path(".cursor") / "rules" / ".graphkit-graphify"

def PLAN(repo: Path, d: Detected) -> list[str]:
    if (repo / STAMP).exists():
        return [f"{RULE}: already installed"]
    if (repo / RULE).exists():
        return [f"{RULE}: exists and is not ours, left alone (remove it to let the kit write its rule)"]
    return [f"add {RULE}"]

def plug(repo: Path, meta: dict) -> list[str]:
    if (repo / STAMP).exists():
        return [f"{RULE}: already installed"]
    if (repo / RULE).exists():
        return [f"{RULE}: exists and is not ours, left alone"]
    (repo / RULE).parent.mkdir(parents=True, exist_ok=True)
    (repo / RULE).write_text((TEMPLATES / "cursor-rule.mdc").read_text(encoding="utf-8"), encoding="utf-8")
    (repo / STAMP).write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    return [f"{RULE}: added"]

def unplug(repo: Path) -> list[str]:
    if not (repo / STAMP).exists():
        return [f"{RULE}: no graphkit stamp, left alone"]
    (repo / STAMP).unlink()
    if (repo / RULE).exists():
        (repo / RULE).unlink()
    rules = repo / ".cursor" / "rules"
    out = [f"{RULE}: removed"]
    if rules.exists() and not any(rules.iterdir()):
        rules.rmdir()
        if rules.parent.exists() and not any(rules.parent.iterdir()):
            rules.parent.rmdir()
    return out

def checks(repo: Path) -> list[Check]:
    p = repo / RULE
    txt = p.read_text(encoding="utf-8") if p.exists() else ""
    return [
        Check("skill where the agent reads", p.exists() and markers.has_block(p), str(RULE)),
        Check("always-on nudge present", "alwaysApply: true" in txt, "alwaysApply: true" if txt else "no rule"),
    ]
