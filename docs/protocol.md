# The A/B protocol

Same repo, same three questions, fresh session per run, each question twice per arm; keep the
second run so first-turn context loading is equal in both arms.

| | A: no graph | B: with graph |
|---|---|---|
| repo | as is, kit not installed | after `kit.py install` |
| prompt | one question per session, answer only, no edits | identical |
| measure | `kit.py measure` on that agent's log, windowed to the run | identical |
| compare | `kit.py measure --ab A.json B.json` | |

Win: B under 60 percent of A on total tokens with the same or better answers.
Loss: B needs more tool calls than A saved reads, or a graph answer was wrong once.

## Writing the three questions for a repo

Each answer must be checkable against the code in under a minute. One of each:

1. Callers and coverage: "Which functions call X, and which test files cover them?"
2. A path: "Trace <an input> from <entry> to <effect>. Name every file on the path."
3. Blast radius: "If X changes its <behaviour>, what breaks?"

A worked example, on a mid-size TypeScript service:

1. "Which callers call `findActiveByUserId`, and which test files cover them?" (known: N call sites, M test files)
2. "Trace an inbound webhook request from the route handler to the reply being sent. Name every file on the path."
3. "If `resolveTemplate` in template-resolver.service.ts changes its fallback, what breaks?"

## Recording a run

Note the clock before and after each arm. For Copilot, enable file logging first or export the
Chat Debug View after each arm. For Cursor, export the usage CSV once at the end and window it.
For Claude Code, `--since` the day and `--from`/`--to` the arm.
For Claude Code, `measure` sums every session under the project in the window, including the
session that drives the `claude -p` runs: run the driver under a different model than the runs
(or note its session id, the transcript file stem) and pass `--exclude-session ID` or
`--model sonnet` so it lands in neither arm. Check the per-session breakdown at the end of the
output before trusting `--ab`; the `--json` file records which filters were applied.
