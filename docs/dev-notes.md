# Dev notes and observations

Running log of setup gotchas, decisions, and things learned while working on
this fork.

## Current setup: official MCP SDK v2

The server uses `mcp.server.MCPServer` from `mcp>=2.2,<3`.
The earlier v1 pin is obsolete; the standalone FastMCP package is not needed.
Run `uv sync --locked --extra dev`, then restart the MCP process.
SDK v2 runs synchronous tools on worker threads, so complete tool calls and
serial transactions are serialized to protect the single USB CLI session.

The project `.mcp.json` was verified with Oh My Pi. It already launches the
local editable checkout. See [hardware validation](hardware-validation.md)
for actual coverage, firmware incompatibilities, and capture prerequisites.

## Install for Claude Code (project scope)

`.mcp.json` in the repo root registers the server for this directory only. It
launches via `uv run --no-sync` so it carries no absolute path and is safe to
commit:

```json
{
  "mcpServers": {
    "flipper": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--no-sync", "flipper-mcp"]
    }
  }
}
```

`--no-sync` reuses the existing `.venv` instead of reconciling deps on every
launch (plain `uv run` uninstalls/reinstalls to match `pyproject`, stripping dev
tools like ruff each time). Run `make install` once to create the venv. Claude
Code prompts once to approve a project-scoped server, then exposes the
`mcp__flipper__*` tools whenever you work in this dir.

## Smoke-testing without hardware

The server boots and lists all tools without a Flipper attached (it connects
lazily on first tool call). Drive a handshake over stdio:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | .venv/bin/flipper-mcp
```

Current tool count: 64, plus the `rf_triage` prompt.

## Modernization pass (2026-08-08)

- Pinned `mcp<2`, added `ruff` to dev deps.
- Added an explicit `[tool.ruff]` config (E, F, I, UP, B, SIM, S, RUF; py311;
  line-length 100). The code already carried `# noqa: S310` markers, so bandit
  rules were clearly intended but never configured.
- Applied `ruff format` + `--fix`: mostly `Optional[X]` to `X | None`, import
  sorting, quoted-annotation cleanup. No behavior change; 71 tests still pass.
- Security hardening: `registry.py` now rejects non-http(s) URLs before fetching
  a remote index (`_require_http_url`), closing the `file://` vector that the
  bare `# noqa: S310` had been papering over.
