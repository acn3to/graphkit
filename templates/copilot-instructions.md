## graphify code graph

This repo has a local code graph at `graphify-out/` (built by graphify, AST only, nothing leaves the machine).

Before opening files to answer a question about the codebase, its architecture or what depends on what, run the smallest graph command that can orient you:

- `graphify path "<A>" "<B>"` for how two symbols connect
- `graphify explain "<symbol>"` for one symbol and its neighbours
- `graphify affected "<symbol>" --depth 2` for the blast radius of a change
- `graphify query "<the question>"` only when you do not yet have a concrete symbol/file pair

If `graphify query` reports many nodes or `[!] TRUNCATED`, narrow the question or switch to `path`/`explain` instead of raising the budget blindly. Then open only the files the graph named. Read files directly when the graph has oriented you and you need exact lines, or when `graphify-out/graph.json` does not exist.

After changing code, run `graphify update .` to keep the graph current. The `/graphify` skill in `.github/skills/graphify/` documents the full pipeline.
