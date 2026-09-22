# Changelog

## 2026-09-22

- Migrated to official MCP SDK 2.2 and refreshed the dependency lockfile.
  The existing project MCP configuration still runs the local checkout.
- Serialized tool/serial transactions, waited for complete prompts, and made
  connection failures explicit. Fixed exact text-file writes and stream cleanup.
- Corrected task listing, GPIO commands, LED channels, universal IR syntax,
  saved IR byte order, and NEC/SIRC capture matching.
- Hardened raw command gates, saved SubGHz frequency checks, and protocol-cache
  path boundaries. Firmware failures now surface as MCP errors.
- Added observed-state checks for app closure and refused UI workflow launches
  while another app remains open.
- Exercised hardware and all 64 tool entries in the
  [coverage report](docs/hardware-validation.md). Some entries cover only safety
  gates or blocked/deferred hardware tests, not successful device operations.
- Clock-setting and NFC UI closure exposed USB/device instability on mntm-010.
  Firmware was intentionally unchanged; recovery and physical target tests remain.

## 2026-08-08

Forked from [Str1ck9/flipper-mcp](https://github.com/Str1ck9/flipper-mcp) at
v0.5.0 to harden it and grow the tool surface. See [`docs/`](docs/).

### 10 new tools (emulation, write, power, clock, bus)

- `nfc_emulate`, `rfid_write`, `rfid_emulate`, `ibutton_write`, `ibutton_emulate`
  (the write-half of the clone workflow), plus `power`, `power_info`,
  `datetime_get`/`datetime_set`, `i2c_scan`. All over the existing CLI, no new
  transport. Tool count 55 to 65.

### Safety gate on transmit

- New `flipper_mcp/safety.py`: transmit/emulate/destructive commands raise unless
  `FLIPPER_ENABLE_TX` is set, including via the `flipper_cli` escape hatch. SubGHz
  TX frequencies checked against an ISM allow-list. Off by default.

### Bridge fixes

- Command completion now waits for the CLI prompt to reappear, not just a
  300ms silence, so slow commands (`storage_md5`, `subghz tx_from_file`) no
  longer return truncated on their instant echo.
- A dead serial port (unplug/reset) is now detected and the singleton is torn
  down so the next call reconnects, instead of writing to a dead handle forever.

### `ir_tx` leading-zero fix

- `ir_tx` normalized hex with `lstrip("0x")`, which strips a charset not a
  prefix, so `0700` transmitted as `700` and `0x0A` as `A`. Silent wrong-code
  bug on every leading-zero byte. Now uses `removeprefix`, with a regression test.

### Opportunity report

- `docs/opportunities.md`: a workflow-generated roadmap (codebase fixes, the
  CLI-vs-protobuf-RPC transport plan, Momentum/Unleashed/RogueMaster firmware
  notes, features to import with exact CLI commands, and a safety model).

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
