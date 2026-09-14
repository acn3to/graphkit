# The presentation, in the order a non-technical audience follows

1. The problem in one number: one Claude Code session on 2026-09-11 consumed 74.5M tokens, 98
   percent of them cache reads of context the model re-reads every turn.
2. What a code graph is: nodes are functions and files, edges are calls and imports; built
   locally, no data leaves the machine.
3. Install: `uv run --no-project <graphkit>/kit.py install --agent copilot`, and the pass/fail table it prints.
4. Use: one question answered from the graph, side by side with the same question answered by
   reading files.
5. The measurement table, A versus B, from `docs/protocol.md`:

| | A: no graph | B: with graph | B/A |
|---|---|---|---|
| total tokens | 2,485,896 | 6,184,603 | 2.49 |
| requests | 44 | 94 | 2.14 |
| tool calls | 21 | 53 | 2.52 |

   pilot-repo run (Claude Code, Sonnet 5), 2026-09-13: six runs per arm, fresh `claude -p` each,
   second run counts; win bar was B/A under 0.60. graphify lost: 2.5x the tokens and the tool
   calls, and on the one question with a hard known answer the graph arm gave the less complete
   answer. The vendor's own `graphify benchmark` claimed 18.1x fewer tokens per query on the same
   corpus; it measures one graph query in isolation, not what the agent does when told a graph
   exists (query it, then read the files anyway). Graph: 8,612 nodes, 17,447 edges, 9.77 s cold
   build. An unmerged trial branch in the pilot repo holds the config, review 2026-09-26. The
   numbers above are the Sonnet 5 rows filtered by hand; the raw `--ab` said 1.86 because the
   driving session shares the project slug (see `known-issues.md`). A Copilot run on a second
   pilot repo is added on 2026-09-14.
6. When not to use it: `templates/when-not-to-use.md`.
7. Where it stands: trial on one repo, review 2026-09-26, then the other repos if it wins.
