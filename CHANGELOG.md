# Changelog

## 2026-11-07 — 0.7.2

- Removing a protocol while another registry call was loading the registry
  could bring the removed protocol back. Loading, installing and removing now
  share one registry lock, so a removed protocol stays gone. Downloads still
  run outside the lock.

## 2026-11-07 — 0.7.1

- `flipper_interrupt` no longer waits behind a running capture. It stops the
  capture early, and the capture returns what it heard so far. Cancelling a
  capture call from the client also stops it early. Both still end with Ctrl-C
  and a prompt, so the next command starts clean.
- Registry tools no longer wait for the device. Protocol installs write a
  temporary file and rename it, so a concurrent read never sees half a file.
- Registry tools, `list_installed_apps`, `flipper_file_inspect`,
  `scan_and_identify` and `ir_scan_and_identify` now publish output schemas.
  `flipper_file_inspect` lists every field, with null for fields the file
  lacks, and an empty `registry_matches` for unknown files.
- Argument schemas now carry limits, so bad values fail before reaching the
  device: captures 0 to 600 seconds, SubGHz 281 to 962 MHz, radio device 0 or
  1, LED channels 0 to 255, `flipper_cli` timeouts up to 120 seconds, holds up
  to 30 seconds, step delays up to 5 seconds, GPIO values 0 or 1, and fixed
  choices for `power` and `gpio_mode`. `gpio_write` no longer turns 2 into 1.
- Tests check the transmit gate by calling each transmit tool with TX off
  and confirming nothing reaches the device.

## 2026-11-07 — 0.7.0

- Every tool now tells MCP clients whether it only reads, changes device
  state, deletes or overwrites data, or reaches the outside world (radio,
  network). Clients can use this to auto-approve safe reads and confirm risky
  calls. `FLIPPER_ENABLE_TX` still gates transmit.
  Tests now fail if a tool that transmits is labeled read-only.
- The server reports its real version and sends short usage instructions to
  clients on connect. The registry User-Agent uses the same version.
- Moved to MCP SDK 2.3, the `uv_build` backend and a `dev` dependency group.
  `uv sync --locked` now installs dev tools; `--extra dev` is gone.
- Added `ty` type checking to CI and fixed the issues it found. CI now tests
  Python 3.11 through 3.15.
- Registry fetches report unreachable URLs, HTTP errors, and malformed or
  non-object index files as registry errors. `flipper-registry` printed a
  traceback for these before. `flipper-smoke` now prints an error instead of
  a traceback when its command fails.
- `list_installed_apps` reports a storage error, such as a missing SD card,
  instead of zero installed apps.
- `flipper-smoke --cmd` applies the same transmit gate as `flipper_cli`.
- `flipper_hold_key` and `wait:` steps accept 0 to 30 seconds. Longer waits
  held the device lock and blocked every other tool.

## 2026-11-01 — 0.6.0

First release of this fork. Thanks to [@Str1ck9](https://github.com/Str1ck9) (James Strickland) for the original [flipper-mcp](https://github.com/Str1ck9/flipper-mcp) it builds on.

- The raw CLI gate now also blocks `rfid raw_emulate`, `bt tx_carrier`,
  `bt tx_packet`, and `js` scripts unless `FLIPPER_ENABLE_TX` is set.
- `flipper_file_inspect` and `subghz_tx_from_file` now report a missing or
  unreadable file as a storage error instead of an "unknown" file or a
  misleading missing-frequency error.
- Recorded the likely cause of the `nfc_detect` timeout in [PLAN.md](PLAN.md).
- CI installs from `uv.lock` and uses current action versions.

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
- Exercised all 64 tools on mntm-010, then 63 after the user upgraded to mntm-012.
  Counts include safety refusals; see the [coverage report](docs/hardware-validation.md).
- Captured JVC Power/Volume Up RAW IR and sent one targeted Volume Up burst.
  Firmware accepted it; TV response is unconfirmed. Normal TX remains disabled.
- NFC CLI still fails; app closure needs Back. The clock setter was not retried
  after its earlier USB disconnect. Recorded resumption steps in [PLAN.md](PLAN.md)
  and condensed setup, hardware, and IR documentation.

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
