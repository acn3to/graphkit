## When not to use graphify

- Repos under about 50 files: the graph costs more turns than it saves.
- Docs-heavy repos: semantic extraction of prose needs an LLM key; the code-only build sees files, not meaning.
- Repos where the agent already has a curated map (an architecture doc it reads first): measure before adding a second map.
- The MCP server adds six tool schemas to every request. Start with the CLI; add the MCP only if the CLI round-trips are clumsy.
