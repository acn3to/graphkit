"""Claude Code: graphify's own installer, wrapped in a before/after snapshot so uninstall is exact.

graphify install --project --platform claude edits CLAUDE.md and .claude/settings.json in place
and writes .claude/CLAUDE.md and .claude/skills/graphify/. graphify uninstall leaves the skill
folder and .claude/CLAUDE.md behind, so the kit restores from its own snapshot instead.
"""
from __future__ import annotations
import difflib, json, shutil
from pathlib import Path
from graphkit import markers
from graphkit.detect import Detected
from graphkit.graphify_cli import GraphifyError, install_platform
from graphkit.verify import Check

SKILL_DIR = Path(".claude") / "skills" / "graphify"
WATCHED = ("CLAUDE.md", ".claude/CLAUDE.md", ".claude/settings.json")

def _snap(repo: Path) -> dict:
    out = {}
    for rel in WATCHED:
        p = repo / rel
        out[rel] = p.read_text(encoding="utf-8") if p.exists() else None
    return out

def _restore(repo: Path, before: dict) -> None:
    """Undo a half-finished graphify install: watched files back to `before`, skill folder gone."""
    for rel in WATCHED:
        p = repo / rel
        if before[rel] is None:
            if p.exists():
                p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(before[rel], encoding="utf-8")
    if (repo / SKILL_DIR).exists():
        shutil.rmtree(repo / SKILL_DIR)

def _skill_state(repo: Path) -> str:
    """'ours' (stamped by the kit), 'foreign' (exists without a stamp), or 'absent'."""
    dest = repo / SKILL_DIR
    if (dest / markers.STAMP).exists():
        return "ours"
    return "foreign" if dest.exists() else "absent"

FOREIGN = f"{SKILL_DIR}: exists and is not ours, left alone (remove it to let the kit install)"

def PLAN(repo: Path, d: Detected) -> list[str]:
    state = _skill_state(repo)
    if state == "ours":
        return [f"{SKILL_DIR}: already installed"]
    if state == "foreign":
        return [FOREIGN]
    return ["run graphify install --project --platform claude, which:",
            f"  {'appends a graphify section to' if d.claude_md else 'creates'} CLAUDE.md",
            f"  {'adds PreToolUse hooks to' if d.claude_settings else 'creates'} .claude/settings.json",
            f"  adds {SKILL_DIR}/ and .claude/CLAUDE.md",
            "  (the diff is printed; a snapshot makes uninstall exact)"]

def plug(repo: Path, meta: dict) -> list[str]:
    state = _skill_state(repo)
    if state == "ours":
        return [f"{SKILL_DIR}: already installed"]
    if state == "foreign":
        # graphify's installer would write into the folder and the kit would stamp it, so a
        # later uninstall would delete a folder that was never ours. Refuse before running it.
        return [FOREIGN]
    before = _snap(repo)
    try:
        install_platform(repo, "claude")
    except GraphifyError:
        # graphify may have edited CLAUDE.md or settings.json before it failed, and no stamp
        # exists yet to undo it. Put the watched files back, then let the caller report.
        _restore(repo, before)
        raise
    bak_removed = []
    bak_lines = []
    for rel in WATCHED:
        bak = repo / f"{rel}.graphify-bak"
        if bak.exists():
            if before[rel] is not None and bak.read_text(encoding="utf-8") == before[rel]:
                bak.unlink()
                bak_removed.append(rel)
            else:
                bak_lines.append(f"{rel}.graphify-bak: kept, differs from the pre-install snapshot")
    after = _snap(repo)
    out = []
    for rel in WATCHED:
        a = (before[rel] or "").splitlines(keepends=True); b = (after[rel] or "").splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(a, b, fromfile=rel, tofile=rel))
        if diff:
            out.append(f"diff {rel}:\n" + diff.rstrip())
    stamp_meta = {**meta, "before": before, "after": after}
    if bak_removed:
        stamp_meta["graphify_bak_removed"] = bak_removed
    markers.write_stamp(repo / SKILL_DIR, stamp_meta)
    out.extend(bak_lines)
    out.append(f"{SKILL_DIR}: added")
    return out

def unplug(repo: Path) -> list[str]:
    stamp = markers.read_stamp(repo / SKILL_DIR)
    if not stamp:
        return [f"{SKILL_DIR}: no graphkit stamp, left alone"]
    out = []
    for rel in WATCHED:
        p = repo / rel
        cur = p.read_text(encoding="utf-8") if p.exists() else None
        if cur == stamp["after"].get(rel):
            if stamp["before"].get(rel) is None:
                if p.exists():
                    p.unlink()
                out.append(f"{rel}: removed (did not exist before install)")
            else:
                p.write_text(stamp["before"][rel], encoding="utf-8")
                out.append(f"{rel}: restored")
        elif cur != stamp["before"].get(rel):
            out.append(f"{rel}: edited since install, remove the graphify section by hand")
    shutil.rmtree(repo / SKILL_DIR)
    out.append(f"{SKILL_DIR}: removed")
    for d in (repo / ".claude" / "skills", repo / ".claude"):
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
    return out

def checks(repo: Path) -> list[Check]:
    skill = repo / SKILL_DIR / "SKILL.md"
    md = repo / "CLAUDE.md"
    settings = repo / ".claude" / "settings.json"
    hooks = False
    if settings.exists():
        try:
            hooks = "PreToolUse" in (json.loads(settings.read_text(encoding="utf-8")).get("hooks") or {})
        except json.JSONDecodeError:
            hooks = False
    nudge = md.exists() and "graphify" in md.read_text(encoding="utf-8") and hooks
    return [
        Check("skill where the agent reads", skill.exists(), str(SKILL_DIR / "SKILL.md")),
        Check("always-on nudge present", nudge, "CLAUDE.md section and PreToolUse hooks" if nudge else "section or hooks missing"),
    ]
