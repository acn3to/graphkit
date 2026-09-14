"""GitHub Copilot in VS Code: skill at .github/skills/graphify/, nudge in .github/copilot-instructions.md.

graphify's own copilot target writes .copilot/skills/, which VS Code reads only at user level
(~/.copilot/skills/). Project-level Copilot reads .github/skills/, so the kit runs graphify's
installer in a temp dir and moves the skill folder to where VS Code looks.
"""
from __future__ import annotations
import shutil, tempfile
from pathlib import Path
from graphkit import markers
from graphkit.detect import Detected
from graphkit.graphify_cli import install_platform
from graphkit.verify import Check

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
SKILL_DIR = Path(".github") / "skills" / "graphify"
INSTRUCTIONS = Path(".github") / "copilot-instructions.md"

def _skill_state(repo: Path) -> str:
    """'ours' (stamped by the kit), 'foreign' (exists without a stamp), or 'absent'."""
    dest = repo / SKILL_DIR
    if (dest / markers.STAMP).exists():
        return "ours"
    return "foreign" if dest.exists() else "absent"

FOREIGN = f"{SKILL_DIR}: exists and is not ours, left alone (remove it to let the kit install)"

def PLAN(repo: Path, d: Detected) -> list[str]:
    out = []
    state = _skill_state(repo)
    out.append({"ours": f"{SKILL_DIR}: already installed",
                "foreign": FOREIGN,
                "absent": f"add {SKILL_DIR}/ (graphify's skill, moved to where VS Code reads)"}[state])
    out.append(f"{'append to' if d.copilot_instructions else 'create'} {INSTRUCTIONS}" if not markers.has_block(repo / INSTRUCTIONS) else f"{INSTRUCTIONS}: already installed")
    return out

def plug(repo: Path, meta: dict) -> list[str]:
    out = []
    dest = repo / SKILL_DIR
    state = _skill_state(repo)
    if state == "ours":
        out.append(f"{SKILL_DIR}: already installed")
    elif state == "foreign":
        out.append(FOREIGN)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            install_platform(Path(tmp), "copilot")
            src = Path(tmp) / ".copilot" / "skills" / "graphify"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest, dirs_exist_ok=True)
        markers.write_stamp(dest, meta)
        out.append(f"{SKILL_DIR}: added")
    text = (TEMPLATES / "copilot-instructions.md").read_text(encoding="utf-8")
    out.append(f"{INSTRUCTIONS}: " + ("appended" if markers.append_block(repo / INSTRUCTIONS, text) else "already installed"))
    return out

def unplug(repo: Path) -> list[str]:
    out = []
    dest = repo / SKILL_DIR
    if (dest / markers.STAMP).exists():
        shutil.rmtree(dest)
        out.append(f"{SKILL_DIR}: removed")
        skills = dest.parent
        if skills.exists() and not any(skills.iterdir()):
            skills.rmdir()
    else:
        out.append(f"{SKILL_DIR}: no graphkit stamp, left alone")
    ins = repo / INSTRUCTIONS
    if markers.strip_block(ins):
        out.append(f"{INSTRUCTIONS}: graphkit block removed")
        if ins.read_text(encoding="utf-8").strip() == "":
            ins.unlink()
            out.append(f"{INSTRUCTIONS}: was empty after removal, deleted")
    else:
        out.append(f"{INSTRUCTIONS}: no graphkit block")
    return out

def checks(repo: Path) -> list[Check]:
    skill = repo / SKILL_DIR / "SKILL.md"
    return [
        Check("skill where the agent reads", skill.exists(), str(SKILL_DIR / "SKILL.md")),
        Check("always-on nudge present", markers.has_block(repo / INSTRUCTIONS), str(INSTRUCTIONS)),
    ]
