# graphkit

Install, plug in, verify and measure [graphify](https://pypi.org/project/graphifyy/) on a repo that
already has GitHub Copilot, Cursor or Claude Code customizations. Additive, marked, undoable.

graphify builds a local code graph (functions, files, calls, imports) with tree-sitter. No LLM, no
key, nothing leaves the machine. An agent that queries the graph before opening files reads far
fewer of them. graphify already ships a skill for many agents; what it does not do is verify the
skill landed where your agent reads it, plug into instructions you already have without
overwriting them, undo itself, or measure what it saved. That is this kit.

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/). The kit installs graphify itself with
  `uv tool install graphifyy==0.9.59` if it is missing.
- The target repo is a git repo. The kit never touches its git state.

## Install into a repo

    cd <your repo>
    uv run --no-project <path-to-graphkit>/kit.py install --agent copilot      # or cursor, claude-code

`--no-project` matters: without it, `uv run` first syncs the project it finds in the current
directory, so running the kit from inside a repo that has a `pyproject.toml` creates a `.venv/`
there and fails outright if that repo has a dependency uv cannot resolve. The kit itself needs
nothing installed. `python3 <path-to-graphkit>/kit.py ...` is the equivalent fallback: `kit.py`
and everything it imports are stdlib only.

The examples below write `kit.py` for short; it is always `<path-to-graphkit>/kit.py`, run from
the target repo's root.

It prints what it found and what it will add, waits for Enter (`--yes` skips), installs graphify
if needed, builds `graphify-out/` (code only; build time scales with corpus size, roughly linear
up to several thousand nodes), plugs into the agent, ignores the graph output,
and prints a pass/fail table. `--commit-graph` ignores only the HTML and cache so `graph.json`
stays reviewable in PRs.

What each agent gets, all additive. The copilot and cursor nudges and the `.gitignore` rule
are fenced with `graphkit:start` / `graphkit:end` markers; the claude-code plug is graphify's
own edit of `CLAUDE.md` and `.claude/settings.json`, unfenced, undone from the before/after
snapshot the kit stamps instead. Added folders carry a `.graphkit` stamp.

| agent | skill | always-on nudge |
|---|---|---|
| copilot | `.github/skills/graphify/` (graphify's skill, moved to where VS Code reads project skills) | a section appended to `.github/copilot-instructions.md` |
| cursor | `.cursor/rules/graphify.mdc`, always applied | same file |
| claude-code | `.claude/skills/graphify/` via graphify's installer; the installer leaves `.claude/settings.json.graphify-bak` which the kit removes if unchanged, otherwise reports it was kept | a section in `CLAUDE.md` plus PreToolUse hooks in `.claude/settings.json`; the diff is printed |

Why Copilot needs the move: `graphify install --platform copilot` writes `.copilot/skills/`, which
VS Code reads only at user level (`~/.copilot/skills/`). Project skills are read from
`.github/skills/`, `.claude/skills/` and `.agents/skills/` (VS Code docs, checked 2026-09-13).

## Verify and undo

    uv run --no-project kit.py verify --agent copilot
    uv run --no-project kit.py uninstall --agent copilot [--purge]

Verify checks: graphify on PATH, graph built, skill where the agent reads, nudge present, hubs
returned by `graphify god-nodes`, a smoke `graphify query`, the ignore rule. Uninstall removes
only what the kit added (marked blocks, stamped folders) and for Claude Code restores the files
graphify's installer edited from a snapshot taken before install. A file you edited after install
is left alone with a message.

## Measure

    uv run --no-project kit.py measure --agent claude-code --project <repo> [--since 2026-09-13] [--from 14:00 --to 14:20] [--exclude-session ID]... [--model sonnet]
    uv run --no-project kit.py measure --agent copilot --file export.json --from 14:00 --to 14:20
    uv run --no-project kit.py measure --agent cursor --file usage.csv --from 14:00 --to 14:20
    uv run --no-project kit.py measure --agent copilot --file a.json --json > A.json   # then B.json
    uv run --no-project kit.py measure --ab A.json B.json

| agent | source | per request | cache split | tool calls |
|---|---|---|---|---|
| claude-code | transcripts under `~/.claude/projects/<slug>/` | yes | yes | yes |
| copilot | Chat Debug View export (`Developer: Show Chat Debug View`, download icon) or `github.copilot.chat.agentDebugLog.fileLogging.enabled` | yes | no | yes |
| cursor | Settings, Usage, export CSV | yes | yes | no |

The table ends with a per-session breakdown (id, models, rows, total), so a session that does not
belong in the window shows up; `--exclude-session` and `--model` drop it, after the window, and the
`--json` output and `--ab` table say which filters were applied. A field an agent does not report prints as `-`. The Copilot reader matches OTLP attribute keys by
pattern; it was checked against the OTLP shape and a synthetic fixture. See `docs/protocol.md`
for the A/B, `docs/wsl-and-windows.md` for the WSL/Windows setup, `docs/presentation.md` for the
deck order, and `templates/when-not-to-use.md` before installing on a small or docs-heavy repo.

## Development

    uv run --with pytest pytest        # unit tests, real graphify on scratch repos
    bash tests/e2e.sh [repo]           # install, verify, uninstall per agent on a clone

Spec: `docs/spec.md`. Plan: `docs/plan.md`.
