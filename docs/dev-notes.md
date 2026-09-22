# Developer notes

Setup and commands live in [README.md](../README.md). Current work is in
[PLAN.md](../PLAN.md); device-specific results are in
[hardware validation](hardware-validation.md).

## Runtime

- Use official `mcp.server.MCPServer` from `mcp>=2.2,<3`, not standalone FastMCP.
- `uv sync --locked --extra dev` installs the tracked lockfile. `.mcp.json`
  launches `uv run --no-sync flipper-mcp`; restart after code/dependency changes.
- Connection is lazy. A fresh stdio client can enumerate 64 tools and the
  `rf_triage` prompt without opening USB.
- SDK v2 executes sync tools on worker threads. Serialize complete tool
  operations as well as serial transactions; the device has one CLI session.

## Transport invariants

- Wait for a settled trailing prompt. Echo silence does not mean completion.
  Timeouts/disconnects retire the connection; the next operation reconnects.
- Interrupt bounded streams on exit, but do not send a stale Ctrl-C after an
  already-completed command.
- Enter `storage write` with **CR only**. CRLF inserted its LF as the first file
  byte on hardware. Preserve supplied content without adding a trailing newline.
- Reject command/path control characters. A failed storage-open must never
  pass file content back to the command interpreter.
- Use `python -m serial.tools.list_ports` through `uv run --no-sync` for device
  discovery. Filesystem glob tools may omit `/dev` character devices.

## Safety and interpretation

- Keep TX disabled by default, including raw CLI paths. A temporary process
  may enable it for an explicitly authorized operation, then must exit.
- Hardware frequency windows are not legal transmission permission.
- Known firmware error strings must become MCP errors, not successful results.
- Confirm app closure through `loader_info`. A launch or accepted key sequence
  cannot establish which screen is visible.
- RAW IR capture does not measure carrier frequency. Preserve timings and
  assumptions separately from any claimed decoded protocol or target response.
- Registry hashes check integrity, not publisher identity. Cache IDs must not
  escape their directory or write through symlink entries.

The current suite has 132 passing tests, covering serial framing/concurrency,
cleanup, safety gates, registry boundaries, IR parsing, and app lifecycle errors.
Hardware effects still need the separate checks in the validation report.
