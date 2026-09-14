# Measuring Copilot with graphkit

Copilot has no standing telemetry file graphkit can tail. Every measurement starts from an
export you take by hand in VS Code, for one arm of an A/B run at a time. This is the exact
sequence; `docs/protocol.md` covers how to design the A/B itself (what questions to ask, how many
runs per arm, what counts as a win).

## 1. Enable Chat Debug logging (once per machine)

1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Run **Preferences: Open User Settings (JSON)**.
3. Add: `"github.copilot.chat.agentDebugLog.fileLogging.enabled": true`.
4. Reload the window so Copilot picks up the setting.

This makes every session's debug output land on disk instead of only in the in-memory debug
view, so an arm you forgot to export before closing VS Code is not lost.

## 2. Run arm A (no graph guidance)

Before installing graphkit, or on a branch/clone without it: run the arm's sessions as designed
in `docs/protocol.md`, noting the wall-clock start and end time.

## 3. Export arm A

1. Command Palette → **Developer: Show Chat Debug View**.
2. Use the download icon in that view to export the session data as JSON.
3. Save it somewhere graphkit can read, e.g. `~/exports/arm-a.json`.

If `agentDebugLog.fileLogging.enabled` is on, the same data also accumulates in the logged file
under VS Code's log folder; either source works as `--file` below.

## 4. Install graphkit, run arm B, export arm B

Install (`kit.py install --agent copilot --yes`), run the same three questions again fresh, note
the clock, then repeat step 3 for arm B (e.g. `~/exports/arm-b.json`).

## 5. Measure each arm

    uv run --no-project kit.py measure --agent copilot --file ~/exports/arm-a.json --from 14:00 --to 14:20 --json > A.json
    uv run --no-project kit.py measure --agent copilot --file ~/exports/arm-b.json --from 14:35 --to 14:55 --json > B.json

Read the printed per-session breakdown before trusting the totals: a session outside the arm's
window, or one you meant to exclude, shows up there by id, model and row count.

## 6. Compare

    uv run --no-project kit.py measure --ab A.json B.json

The table reports B/A on total tokens, requests and tool calls, and states which filters (window,
`--exclude-session`, `--model`) were applied to each side, exactly like the Claude Code A/B in
`docs/presentation.md`.

## Notes

- If the OTLP attribute keys in a real export do not match what `graphkit/readers/copilot.py`
  expects, `measure` reports what it could parse and the field it could not becomes `-` in the
  row rather than a hard failure; file the mismatched key names.
- This procedure has not yet been run start-to-finish and compared with `--ab` in this repo's own
  validation. Do not read graphkit's Copilot support as having proven token savings until it has.
