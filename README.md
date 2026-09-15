# graphkit

Install, verify, and measure [graphify](https://pypi.org/project/graphifyy/), a local,
tree-sitter-based code graph, on a repo that already has GitHub Copilot, Cursor, or Claude Code
customizations. Additive, marked, undoable. No LLM, no key, nothing leaves the machine.

An agent that orients itself with the smallest useful graph command before opening files reads
fewer of them. graphify already ships a skill for these agents; graphkit verifies it landed where
the agent actually reads it, plugs into instructions you already have without overwriting them,
undoes itself cleanly, and measures what it saved.

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/). Installs graphify itself
  (`uv tool install graphifyy==0.9.59`) if it's missing.
- The target repo is a git repo; graphkit never touches its git state.

## Install

    cd <your repo>
    uv run --no-project <path-to-graphkit>/kit.py install --agent copilot   # or cursor, claude-code

Use `--no-project` (or `python3 kit.py ...`, stdlib only) so `uv` doesn't sync the target repo's
own `pyproject.toml` first. This prints a plan, waits for Enter (`--yes` skips), builds
`graphify-out/graph.json`, plugs into the agent, writes the `.gitignore` and `.graphifyignore`
rules, and prints a pass/fail table.

| agent | skill | always-on nudge |
|---|---|---|
| copilot | `.github/skills/graphify/` | `.github/copilot-instructions.md` |
| cursor | `.cursor/rules/graphify.mdc` | same file |
| claude-code | `.claude/skills/graphify/` (graphify's own installer, snapshotted for clean uninstall) | `CLAUDE.md` + `.claude/settings.json` hooks |

## Verify and undo

    uv run --no-project kit.py verify --agent copilot
    uv run --no-project kit.py uninstall --agent copilot [--purge]

Verify checks graphify is on PATH, the graph built, `graphify explain` answers on the top hub, the
agent's guidance landed, and both ignore rules are in place. Uninstall removes only what the kit
added; a file you edited after install is left alone with a message.

## Any other agent

graphkit only plugs into Copilot, Cursor, and Claude Code, but the graph itself works with any
agent that can run a shell command. Install graphify if you don't have it
(`uv tool install graphifyy==0.9.59`), build the graph once with `graphify . --no-viz`, then paste
this into whatever that agent reads as instructions (system prompt, project rules file, or the
first message of a session):

```text
This repo has a local code graph at graphify-out/graph.json, built by graphify from the AST.
Nothing in it is sent to an LLM.

Before opening files to answer a question about architecture, dependencies, or the blast radius
of a change, orient with the smallest graph command that fits:

- `graphify path "<A>" "<B>"` when two symbols or files are already known.
- `graphify explain "<symbol-or-file>"` when one is central.
- `graphify affected "<symbol-or-file>" --depth 2` for the blast radius of a change.
- `graphify query "<question>" --budget 700` only when none of the above apply yet.

If `graphify query` reports many nodes or `[!] TRUNCATED`, narrow the question or switch to
`path`/`explain` instead of raising the budget. Open only the files the graph names, then read
them normally for exact lines. If graphify-out/graph.json does not exist, skip all of this and
read the codebase directly.

After changing code, run `graphify update .` to keep the graph current.
```

## Measure

    uv run --no-project kit.py measure --agent claude-code --project <repo> --from 14:00 --to 14:20
    uv run --no-project kit.py measure --agent copilot --file export.json --from 14:00 --to 14:20
    uv run --no-project kit.py measure --agent cursor --file usage.csv --from 14:00 --to 14:20
    uv run --no-project kit.py measure --ab A.json B.json

Claude Code reads its own transcripts directly; Copilot and Cursor need an export first
(`docs/copilot-measurement.md`). Install and verify prove setup health, not token savings; see
`docs/protocol.md` for how to run and read an A/B.

## Development

    uv run --with pytest pytest        # unit tests, real graphify on scratch repos
    bash tests/e2e.sh <repo>           # install, verify, uninstall per agent on a clone

More: `docs/protocol.md` (the A/B method), `docs/wsl-and-windows.md`, `docs/copilot-measurement.md`,
`docs/known-issues.md`, `templates/when-not-to-use.md`.
