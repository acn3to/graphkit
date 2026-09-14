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

GRAPHKIT_DEFAULT_HEADING = "## GraphKit default"

GRAPHKIT_DEFAULT_SECTION = f"""{GRAPHKIT_DEFAULT_HEADING}

When `graphify-out/graph.json` already exists, prefer the smallest graph command that can orient you:

- Use `graphify path "<A>" "<B>"` when the user gives, or you already know, two symbols/files.
- Use `graphify explain "<symbol-or-node-id>"` when one symbol or file is central.
- Use `graphify affected "<symbol>" --depth 2` for blast-radius questions.
- Use `graphify query "<question>"` only when you do not yet have a concrete symbol/file pair. If it reports many nodes or `[!] TRUNCATED`, narrow the question or switch to `path`/`explain` instead of raising the budget blindly.

After the graph orients you, open only the files it named."""

# graphify's upstream SKILL.md (as shipped in graphify 0.9.59) tells the agent to treat
# any question as a `graphify query` first. Field validation on real repos found precise
# `graphify path`/`graphify explain` far cheaper and more accurate than that broad query,
# so the copied skill is patched below in addition to the nudge above: the nudge alone
# does not override the skill's own frontmatter and fast-path section.
_DESC_QUERY_FIRST = "where the question should be treated as a graphify query first"
_DESC_SMALLEST_FIRST = "where the agent should start with the smallest useful graph command"

_FASTPATH_QUERY_FIRST = (
    "**skip Steps 1–5 entirely and jump straight to `## For /graphify query`.** "
    "Run `graphify query \"<question>\"` immediately. Do not run detect. Do not check "
    "corpus size. Do not ask the user to narrow. The graph is already built — use it."
)
_FASTPATH_SMALLEST_FIRST = (
    "**skip Steps 1–5 entirely and orient with the smallest graph command that "
    "fits: `graphify path \"<A>\" \"<B>\"` for two known symbols, `graphify explain "
    "\"<symbol>\"` for one, `graphify affected \"<symbol>\" --depth 2` for blast "
    "radius, or `graphify query \"<question>\"` only when none of those apply.** Do "
    "not run detect. Do not check corpus size. Do not ask the user to narrow. The "
    "graph is already built — use it."
)

def _insert_after_frontmatter(text: str, section: str) -> str:
    if text.startswith("---\n"):
        close = text.find("\n---", 4)
        if close != -1:
            insert_at = text.index("\n", close + 1) + 1
            return text[:insert_at] + "\n" + section + "\n\n" + text[insert_at:]
    return section + "\n\n" + text

def patch_skill(skill_md: Path) -> bool:
    """Rewrite graphify's upstream SKILL.md from query-first to smallest-command-first.

    Idempotent: a re-run on an already-patched file makes no further change and returns False.
    """
    if not skill_md.exists():
        return False
    text = skill_md.read_text(encoding="utf-8")
    patched = text.replace(_DESC_QUERY_FIRST, _DESC_SMALLEST_FIRST).replace(_FASTPATH_QUERY_FIRST, _FASTPATH_SMALLEST_FIRST)
    if GRAPHKIT_DEFAULT_HEADING not in patched:
        patched = _insert_after_frontmatter(patched, GRAPHKIT_DEFAULT_SECTION)
    if patched == text:
        return False
    skill_md.write_text(patched, encoding="utf-8")
    return True

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
        patch_skill(dest / "SKILL.md")
    elif state == "foreign":
        out.append(FOREIGN)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            install_platform(Path(tmp), "copilot")
            src = Path(tmp) / ".copilot" / "skills" / "graphify"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest, dirs_exist_ok=True)
        markers.write_stamp(dest, meta)
        patch_skill(dest / "SKILL.md")
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
