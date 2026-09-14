"""What the target repo already has. Read-only."""
from __future__ import annotations
from dataclasses import dataclass, fields
from pathlib import Path

@dataclass(frozen=True)
class Detected:
    copilot_instructions: Path | None
    copilot_skills: Path | None
    cursor_rules: Path | None
    claude_md: Path | None
    claude_settings: Path | None
    claude_skills: Path | None
    gitignore: Path | None
    graph: Path | None

    def describe(self) -> str:
        names = {"copilot_instructions": ".github/copilot-instructions.md", "copilot_skills": ".github/skills",
                 "cursor_rules": ".cursor/rules", "claude_md": "CLAUDE.md", "claude_settings": ".claude/settings.json",
                 "claude_skills": ".claude/skills", "gitignore": ".gitignore", "graph": "graph"}
        return "\n".join(f"  {names[f.name]}: {'present' if getattr(self, f.name) else 'absent'}" for f in fields(self))

def _p(path: Path) -> Path | None:
    return path if path.exists() else None

def detect(repo: Path) -> Detected:
    r = Path(repo)
    return Detected(
        copilot_instructions=_p(r / ".github" / "copilot-instructions.md"),
        copilot_skills=_p(r / ".github" / "skills"),
        cursor_rules=_p(r / ".cursor" / "rules"),
        claude_md=_p(r / "CLAUDE.md"),
        claude_settings=_p(r / ".claude" / "settings.json"),
        claude_skills=_p(r / ".claude" / "skills"),
        gitignore=_p(r / ".gitignore"),
        graph=_p(r / "graphify-out" / "graph.json"),
    )
