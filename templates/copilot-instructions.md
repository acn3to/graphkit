## graphify code graph

This repo has a local code graph at `graphify-out/` (built by graphify, AST only, nothing leaves the machine).

Before opening files to answer a question about the codebase, its architecture or what depends on what, run in the terminal:

- `graphify query "<the question>"` for a scoped subgraph
- `graphify path "<A>" "<B>"` for how two symbols connect
- `graphify explain "<symbol>"` for one symbol and its neighbours
- `graphify affected "<symbol>" --depth 2` for the blast radius of a change

Then open only the files the graph named. Read files directly when the graph has oriented you and you need exact lines, or when `graphify-out/graph.json` does not exist.

After changing code, run `graphify update .` to keep the graph current. The `/graphify` skill in `.github/skills/graphify/` documents the full pipeline.
