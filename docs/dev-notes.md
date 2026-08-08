# Dev notes and observations

Running log of setup gotchas, decisions, and things learned while working on
this fork.

## Setup gotcha: mcp must be `<2`

The server imports `mcp.server.fastmcp.FastMCP`. **mcp 2.0.0 removed that
module** (FastMCP moved to a standalone `fastmcp` package). With an unpinned
`mcp>=1.2`, a fresh install resolves to 2.x and the server dies at import with:

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

To the MCP client this looks like "Connection closed" with no detail, because
the crash happens before the stdio handshake. Fixed by pinning `mcp>=1.2,<2` in
`pyproject.toml`. If you hit the error, run `uv pip install "mcp>=1.2,<2"`.

Longer-term option: migrate to the standalone `fastmcp` package and drop the pin.
Not done yet -- the 1.x API works and the import is the only coupling.

## Install for Claude Code (project scope)

`.mcp.json` in the repo root registers the server for this directory only:

```json
{
  "mcpServers": {
    "flipper": {
      "type": "stdio",
      "command": "/absolute/path/to/.venv/bin/flipper-mcp"
    }
  }
}
```

Claude Code prompts once to approve a project-scoped server, then exposes the
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

Current tool count: 55.

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
