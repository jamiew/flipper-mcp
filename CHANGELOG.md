# Changelog

## 2026-08-08

Forked from [Str1ck9/flipper-mcp](https://github.com/Str1ck9/flipper-mcp) at
v0.5.0 to harden it and grow the tool surface. See [`docs/`](docs/).

### Startup fix: pin `mcp<2`

- mcp 2.0 removed the `mcp.server.fastmcp` module the server imports, crashing it
  at import (the MCP client only saw "Connection closed"). Pinned `mcp>=1.2,<2`.

### Lint and format tooling

- Added an explicit ruff config (E/F/I/UP/B/SIM/S/RUF, py311, line-length 100)
  and `ruff` as a dev dep, then ran a format + fix pass. No behavior change.

### Registry URL hardening

- `fetch_index` and `install_from_entry` now reject non-http(s) URLs before
  fetching a remote index, closing the `file://` vector the code had suppressed
  with a bare `# noqa`.

### docs/

- `landscape.md` -- every Flipper Zero MCP compared, with a capability matrix.
- `feature-ideas.md` -- prioritized roadmap from the gap analysis.
- `ir-tv-probing.md` -- the capture → identify → replay IR workflow.
- `dev-notes.md` -- setup gotchas and this modernization pass.
