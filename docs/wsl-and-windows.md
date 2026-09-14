# WSL and native Windows

## WSL (primary path)

1. Keep the repo on the WSL filesystem (`~/...`), not under `/mnt/c`: tree-sitter over `/mnt/c` is
   many times slower and file watching is unreliable.
2. Install uv inside WSL: `curl -LsSf https://astral.sh/uv/install.sh | sh`, then open a new shell.
3. Open VS Code with the WSL remote (`code .` from the WSL shell, or Remote-WSL: Reopen Folder in
   WSL). Copilot's terminal then runs in WSL, where `graphify` is on PATH.
4. `uv run --no-project <graphkit>/kit.py install --agent copilot --yes` from the repo root.
   `--no-project` stops uv from syncing the target repo's own `pyproject.toml` (which would
   create a `.venv/` there, and fail on a dependency uv cannot resolve). `python3
   <graphkit>/kit.py ...` works the same way; the kit is stdlib only.
5. Reload the VS Code window so Copilot picks up `.github/skills/` and the instructions file.
6. Measure: `Developer: Show Chat Debug View`, turn on
   `github.copilot.chat.agentDebugLog.fileLogging.enabled` in settings, run arm A before step 4 and
   arm B after, export, then `uv run --no-project <graphkit>/kit.py measure --agent copilot --file <export> --from .. --to ..`.

## Native Windows (secondary)

Same commands in PowerShell after installing uv for Windows
(`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`). Paths the
kit writes are the same. graphify's `--platform windows` target is for Claude Code on native
Windows and is not needed for Copilot or Cursor. Checked on 2026-09-13 against `graphify install
--help`; not exercised on a native Windows machine yet, so treat the first native run as
the test and file what breaks.
