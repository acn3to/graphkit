# Known issues, parked at the 2026-09-13 final review

Real, deferred, none reachable in normal use. Fix after the first field validation run.

- `append_block` accepts a file that holds an orphan start marker (a start with no end, from a
  hand edit or a crash between two writes); the next `strip_block` then removes text between the
  orphan start and the new end. Fix: refuse to append when any start marker is present.
- `_restore` in the Claude Code plug-in (run when graphify's installer fails mid-way) restores the
  watched files but does not clear `*.graphify-bak` or an empty `.claude/` it created. A stray
  backup file shows in `git status`.
- A step-3 failure in `install` returns before step 4, so `graphify-out/` is built but not yet
  ignored. Re-run install or add the ignore line by hand.
- The Copilot reader counts a span whose name matches both `tool` and a model request twice. Not
  seen in the synthetic fixture; check against the first real VS Code export.
- `.gitignore` files created by a kit build before 0f03de7 carry no `created` note and are left
  empty on uninstall. No repo was installed with that build.

Found by the pilot-repo trial on 2026-09-13. These change the headline number, so they come
before a field validation run, not after.

- `graphify benchmark` reports a node count that disagrees with its own `graph.json` (8,827 vs
  8,549). Vendor bug; the kit should read the count from the file, not from the benchmark output.
- graphify indexes the skill it just installed: the build ran before the skill was written (8,549
  nodes); a rebuild after gives 8,612, with 60 nodes referencing `.claude/skills/graphify`. Fix:
  exclude `.claude/skills/graphify` (or write the skill first and exclude it) so the 41k SKILL.md
  is not graph content.
- graphify indexes its own stale output under any name but the exact `graphify-out/`: a renamed
  `graphify-out-old/` holding a 10M `graph.json` was walked on rebuild (9,113 nodes, about 500
  inflated). Fix: exclude `graphify-out*` or refuse to build with a sibling output dir present.
- The `.gitignore` rule the kit writes is branch-local, so `git checkout develop` after the trial
  leaves a 10M untracked `graphify-out/` visible and one `git add -A` from being committed. Fix:
  write the rule to `.git/info/exclude` as well, or say so in the uninstall and protocol docs.
