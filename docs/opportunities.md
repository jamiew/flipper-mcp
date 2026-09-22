# Flipper-MCP Opportunity Report

Historical research. Implementation details and firmware recommendations below
are not current validation results. See [hardware validation](hardware-validation.md)
and the changelog before acting on these proposals.

## Executive summary
Three moves lead. First, fix the `ir_tx` `lstrip("0x")` bug (server.py:216-217): it silently corrupts every IR code with a leading-zero byte and is the clearest correctness defect in the fork. Second, ship a `safety.py` with a single `FLIPPER_ENABLE_TX` gate plus a SubGHz frequency allow-list, wired into the two already-shipped ungated TX tools and the `flipper_execute` escape hatch. Third, add a `firmware_detect` probe (parse `firmware_origin_fork` from `device_info`) that unlocks firmware-aware behavior across every downstream tool and anchors version caveats for the user's out-of-date Momentum. Everything else worth doing over the existing CLI bridge is small and additive; only screenshot and binary file transfer need the protobuf RPC channel.

## Quick wins (high value, low effort)

| Title | Category | Source | Concrete step | Needs-RPC? |
|---|---|---|---|---|
| Fix `ir_tx` leading-zero corruption | Codebase fix | code-audit | server.py:216-217: replace `.lstrip("0x").lstrip("0X")` with `.removeprefix("0x").removeprefix("0X")` on both `addr` and `cmd` | No |
| `firmware_detect` probe | Firmware | momentum + unleashed | server.py near line 76: run `device_info`, parse `firmware_origin_fork`/`firmware_version`/`hardware_region`, cache on the bridge, expose as `flipper_firmware()` returning `{fork, version, region, is_cfw}` | No |
| `FLIPPER_ENABLE_TX` gate | Safety | safety | New flipper_mcp/safety.py with `require_tx(action)`; call as first line of `ir_tx` (server.py:203) and `subghz_tx_from_file` (server.py:161) | No |
| SubGHz frequency allow-list | Safety | safety | Add `TX_BANDS` + `check_tx_frequency(hz)` to safety.py; for `.sub` files parse `re.search(r'Frequency:\s*(\d+)', content)` and refuse if absent | No |
| Close `flipper_execute` bypass | Safety | safety | safety.py `_GATED_PREFIXES` + `gate_raw_command(command)`; call before `send()` in `flipper_execute` (server.py:~94) | No |
| `power` tool | Import | imports | server.py after `loader_close` (~393): map `{off,reboot,reboot2dfu,otg_on,otg_off}` to `power off`/`power reboot`/`power reboot2dfu`/`power 5v 1`/`power 5v 0`; wrap in try/except (link drops on reboot) | No |
| `rfid_write` + `rfid_emulate` | Import | imports | `bridge.send(f'rfid write {key_type} {key_data}')` and `bridge.stream(f'rfid emulate {key_type} {key_data}', duration_s)` (command is `rfid`, not `lfrfid`) | No |
| `extend_range.txt` writer | Firmware | unleashed | `subghz_enable_extended_range(enable)` writes `'true'`/`'false'` to `/ext/subghz/assets/extend_range.txt` via `write_file`; gate on `firmware_detect`, pair with `power reboot` | No |
| SubGHz extended-band docstrings | Firmware | momentum | Edit server.py:144-155 and 657-666 docstrings: note Momentum RX is unrestricted, extended bands (281-361/378-481/749-962 MHz) need Settings>Protocols>SubGHz Extend+Bypass, stock rejects out-of-range | No |
| `bridge.py` unit tests | Codebase fix | code-audit | Add tests/test_bridge.py exercising `FlipperBridge._clean(raw, cmd)`: ANSI strip, echo removal, `>:` prompt trim, CRLF->LF; plus `ir_tx` leading-zero survival | No |
| `power_info` (battery) | Import | imports | `power_info()` = `bridge.send('info power')`, fall back to `power info` on empty; parse `key: value` into a dict | No |
| `ibutton_emulate` + `ibutton_write` | Import | imports | `bridge.stream(f'ikey emulate {key_type} {key_data}', duration_s)` and `bridge.send(f'ikey write Dallas {key_data}')` (command is `ikey`, not `ibutton`) | No |

## Codebase fixes & modernization

Ranked by value.

- **`ir_tx` leading-zero corruption (high).** `str.lstrip` strips a charset, not a prefix, so `"0012"->"12"`, `"00EAC7"->"EAC7"`, `"0x0A"->"A"`. Every transmit with a leading-zero byte sends the wrong code silently. Fix at server.py:216-217 with `.removeprefix(...)`; add a test asserting `ir_tx('NEC','00','0A')` passes both through unchanged.
- **Quiet-period truncation (medium).** `bridge.py:_wait_quiet` (137-153) declares a command done after `quiet_ms` (300ms) of no output. The CLI echoes the command instantly, then may pause >300ms before printing results for compute-heavy commands (`storage_md5` on a large file, `storage_read` of a big file, `subghz tx_from_file`), so the detector fires on the echo and returns truncated/empty output. Fix: make `send()` prompt-aware, treating a trailing `>:` as the real completion signal so short commands stay fast; or pass explicit `quiet_ms=800` to the slow one-shots (server.py:124, 167, 292).
- **Dead reader thread (medium, safety-adjacent).** `bridge.py:_read_loop` (103-113) exits silently on `SerialException`/`OSError` (unplug, port reset), but the `_bridge` singleton (server.py:51-59) is never cleared, so every later call writes to a dead port. Add `self._alive = threading.Event()`, clear it in the except branches, and have `_get_bridge()` null the singleton and re-run `_auto_detect` on a `FlipperError`, giving auto-reconnect.
- **`bridge.py` has zero tests (medium).** Registry, classifier, and UI are well covered, but the framing logic that holds the bugs above is untested. `_clean()` is a pure `@staticmethod` needing no hardware. Add tests/test_bridge.py (see quick-wins row).
- **Migrate off the `mcp<2` pin (medium).** pyproject pins `mcp>=1.2,<2` because mcp 2.0 dropped the bundled `mcp.server.fastmcp`. The maintained path is standalone `fastmcp` (jlowin/fastmcp v2). Our surface is tiny (`FastMCP(name)`, `@mcp.tool()`, `@mcp.prompt()`, `mcp.run()`), all present in standalone. Swap `"mcp>=1.2,<2"` -> `"fastmcp>=2"` and server.py:19 import; verify decorators and `run()` stdio default before committing. Keep separate from bug fixes. Likely also clears the pydantic warning below.
- **`pydantic_settings` startup warning (low).** mcp 1.29's Settings model declares `lifespan` with an unresolved forward reference; pydantic-settings 2.15 warns on import, polluting stderr (the stdio-MCP log channel). Add at the top of server.py before the FastMCP import: `import warnings; warnings.filterwarnings("ignore", message="Field 'lifespan' has an incomplete definition")`. The fastmcp migration removes the need entirely. Re-check after any mcp bump.
- **Fingerprint field-extraction flag mismatch (low, latent).** registry.py matches the fingerprint at line 177 with `IGNORECASE|MULTILINE` but extracts decoder fields at line 186 with no flags. Latent today (bundled regexes use explicit hex classes and no anchors), but a contributed protocol relying on case-insensitivity will match the fingerprint yet extract nothing. Change line 186 to pass `flags=re.IGNORECASE | re.MULTILINE`.

## Transport decision (CLI vs protobuf RPC)

Keep the synchronous USB-CLI-text bridge as the primary transport; nearly every feature maps to a real CLI verb it already handles. Add RPC only for what the CLI genuinely cannot do: screenshot capture and binary `.sub`/`.nfc`/`.fap` transfer. Do not adopt busse's async `FlipperTransport`/`USBTransport` stack (it forces rewriting all 54 sync tools), and explicitly rule out BLE (busse's `bluetooth.py` is a thin stub adding pairing state, a second fragmentation layer, and a heavyweight `bleak` dep for zero new capability over USB).

Staged plan:

1. **Vendor the generated protobuf modules (prerequisite, high value, low effort).** Copy the 8 MIT-licensed `*_pb2.py` files from `busse_flipperzero-mcp/src/flipper_mcp/core/protobuf_gen/` (`flipper_pb2.py`, `system_pb2.py`, `storage_pb2.py`, `gui_pb2.py`, `application_pb2.py`, `property_pb2.py`, `desktop_pb2.py`, `gpio_pb2.py` + `__init__.py`) into `flipper_mcp/protobuf_gen/`. Add `protobuf>=4,<6` to pyproject; keep the MIT LICENSE note. Verify with `uv run python -c 'import flipper_mcp.protobuf_gen.flipper_pb2'`. Gate all RPC code behind a `PROTOBUF_AVAILABLE` try/import so CLI tools keep working without it.
2. **Add a synchronous RPC session that borrows the existing serial handle (high, medium).** The CLI and RPC share one exclusive USB-CDC port, so a mode switch is required. In bridge.py: (a) pause/join the reader thread so nothing else reads `self._ser`; (b) `reset_input_buffer()`, write `b'\x03\r'` then `b'start_rpc_session\r'` (CR only, not CRLF: a trailing `\n` gets eaten as the first frame's length byte and the session dies with `ERROR_DECODE`), sleep ~0.3s, drain; (c) exchange nanopb varint-delimited frames, porting busse `protobuf_rpc.py` `_encode_varint`/`_read_varint`/`_receive_main_message` (lines 60-116) to sync `self._ser.read()`; (d) on exit restart the reader and re-run `_handshake()`. Probe with `system_ping_request` before issuing real commands.
3. **`flipper_screenshot` (high, medium).** The flagship capability nobody in the comparison set actually shipped. Inside an RPC session, send `gui_start_screen_stream_request`, read one `gui_screen_frame` (1024 bytes = 128x64), send `gui_stop_screen_stream_request`. Decode per flipperdevices `cli_helpers._dump_screen`: for byte `i`, `page=i//128`, `x=i%128`, pixel `(x, page*8+b)` on where `(data[i]>>b)&1`. Return via FastMCP `Image(data=png_bytes, format='png')`; emit PNG via stdlib `zlib` to avoid a Pillow dep, or add Pillow behind an optional `[screenshot]` extra. Frame is 1024 bytes across all firmwares.
4. **Chunked `flipper_upload` / `flipper_download` (high, medium).** The CLI `storage write` is text-only and Ctrl-C terminated: it corrupts binary and cannot pull files at all. Use RPC `Storage.WriteRequest`/`ReadRequest` with `has_next` fragmentation. Write: 1024-byte chunks sharing one `command_id`, `has_next=True` on all but the last, paced to ~80 KB/s to avoid overrunning SD flush (port millsymills `protobuf_rpc.py` lines 1246-1300, `asyncio.sleep` -> `time.sleep`; timeout floor `max(15s, len/40000)`). Read: loop `_receive_main_message` while `resp.has_next`, accumulating `file.data`. 1024-byte chunk is safe on Momentum/Unleashed/RogueMaster (very old firmware caps ~512B).
5. **Deferred: WiFi (ESP32) TCP transport (low, high).** busse ships a complete `tcp_uart_bridge` ESP-IDF firmware exposing RPC over TCP. Same nanopb frames, no CLI mode switch (born in RPC mode), so it adds range not capability. Only worth it if the user gets and flashes a dev board; the RPC helper from step 2 already produces the needed byte stream, only the source changes (`socket` vs `self._ser`).

## Firmware notes

**Shared CLI surface.** Momentum, Unleashed, and RogueMaster all keep the byte-for-byte same `subghz`/`nfc`/`ir`/`rfid`/`storage`/`device_info` CLI as official firmware, so the text bridge works on all of them with no parser changes. The differences are region-lock removal, extra protocol decoders, and storage layout.

**Recommended target: Unleashed (Default build).** Best CLI-driven RF/IR target: removes the region TX lock, decodes rolling-code protocols official cannot, keeps the identical CLI surface, and is more stable than RogueMaster's kitchen-sink build. RogueMaster is Unleashed-base + apps (same CLI, heavier, bleeding-edge). Momentum is Unleashed-grade but its JS/asset stack adds nothing for a CLI bridge. State this in the README to save a wrong-firmware debugging loop.

**Firmware detection is the enabling primitive.** The fork has zero firmware awareness (grep for momentum/unleashed/roguemaster in `flipper_mcp/*.py` returns nothing). `device_info` prints `firmware_origin_fork` (`Momentum`/`Unleashed`/`RogueMaster`/`Official`), `firmware_version`, `hardware_region`, `hardware_region_provisioned`. Parse case-insensitively (the origin key name has shifted `firmware_origin` vs `origin` across versions; fall back to scanning for the four brand tokens), reuse `registry._extract_kv` (registry.py:238), cache on the bridge. Every downstream tool then decides whether TX is unlocked, whether `/int` is valid, and which decoders exist.

**SubGHz frequency validation.** Stock firmware accepts only 299999755-348000000, 386999938-464000000, 778999847-928000000 Hz. Momentum/Unleashed RX is unrestricted; TX is gated behind the extended bands (~281-361/378-481/749-962 MHz), which require the SD-card file `extend_range.txt` plus, on Momentum, Settings>Protocols>SubGHz Extend+Bypass. This is a per-device toggle, not something the MCP controls, and the user's out-of-date Momentum may or may not have it enabled. Correct the `subghz_rx`/`rf_scan_and_identify` docstrings to say so, and add 315/348/390/430.5 MHz to example sweeps.

**Unlock files the CLI can already write.** `extend_range.txt` (bare `true`/`false` at `/ext/subghz/assets/extend_range.txt`) and `setting_user.txt` (custom RX frequencies, hopper list, presets at `/ext/subghz/assets/setting_user.txt`) are both writable via the existing `write_file`, no transport change. Both are read at app/CLI start, so pair with `power reboot`. Gate on `firmware_detect` (Official ignores both).

**Momentum storage-layout caveat.** Recent Momentum removed LittleFS internal storage: config now lives on SD, the former internal namespace relocated to `/ext/.int/`. `storage info /int` and `storage list /int` may error or return a degraded mount. Edit server.py:116-117 to prefer `/ext` and note `/int` may be vestigial. Older Momentum/Xtreme and stock still expose a real `/int`, so let `firmware_detect` gate the warning.

**Version-sensitive parse risks (relevant to this user's older Momentum).**
- `info power` moved from the older `power info`: try `info power`, fall back to `power info`.
- `nfc emulate <file>` is 2024+ mainline / recent Momentum; older builds take bare `nfc emulate` (fixed UID). Try with a file, fall back to no-arg.
- The trailing `subghz rx <freq> <device>` device token is a CFW/newer addition; old CLI builds parse `subghz rx <freq>` and choke on the extra token. Only append `device` when explicitly set or when `firmware_detect` reports support; mirror `subghz_rx_raw`, which already takes no device arg.

**Decoder coverage to add (medium, firmware-flagged).** Momentum integrates weather-station/TPMS/POCSAG decoders; Unleashed/RM add rolling-code protocols official cannot: KeeLoq (extra manufacturer keys), Nice FloR-S, FAAC SLH, BFT Mitto, Somfy Telis, CAME Atomo, Star Line. Capture real `subghz rx` output first (exact wording drives registry.py:176), add protocol JSONs under `flipper_mcp/protocols/`, and add a `requires_cfw`/`min_firmware` field to the Protocol model (registry.py:42) so a non-hit on Official is explained rather than reported as unknown. Tag Momentum decoders `packs:["momentum"]`.

## Features to import

### Works today over the CLI bridge (no RPC)

Every command below is verified against firmware source; use `bridge.send()` for one-shots and `bridge.stream(cmd, duration_s)` for blocking emulate/rx.

- **`power(action)`** — `power off` / `power reboot` / `power reboot2dfu` / `power 5v 1` / `power 5v 0`. Verified against `power_cli.c` (registers exactly `off`, `reboot`, `reboot2dfu`, `5v <0|1>`, `3v3 <0|1>`; no `otg`/`info` subcommands, so use `power 5v`). off/reboot drop the link: wrap in try/except, return "device rebooting". Server.py after `loader_close` (~393).
- **`power_info()`** — `info power` (fall back `power info`), parse `key: value`. Verified `cli_command_info` dispatches `info <device|power|power_debug>`.
- **`datetime_get()` / `datetime_set(iso)`** — `date` reads, `date YYYY-MM-DD HH:MM:SS W` sets (W = ISO weekday 1-7, computed before send). Verified `cli_command_date` format `%.4d-%.2d-%.2d %.2d:%.2d:%.2d %d`. Useful for correct capture timestamps.
- **`i2c_scan()`** — `i2c`, scans GPIO PC0(SCL)/PC1(SDA). Lift the parser verbatim from millsymills `tools/cli_typed.py:208` `_parse_i2c`.
- **`rfid_write(key_type, key_data)` / `rfid_emulate(...)`** — `rfid write|emulate <key_type> <key_data>` (types EM4100/H10301/Indala26). Verified `lfrfid_cli.c`; crib arg shape from FlipperAgent `modules/rfid/module.py:118-138`.
- **`ibutton_emulate(...)` / `ibutton_write(key_data)`** — `ikey emulate <key_type> <key_data>`, `ikey write Dallas <key_data>` (Dallas 8B / Cyfral 2B / Metakom 4B; only Dallas writes). Verified `ibutton_cli.c` registers `ikey`. Do NOT copy FlipperAgent's `ibutton ...` string, it is wrong.
- **`nfc_emulate(file_path='', duration_s=15)`** — `nfc emulate <file>` on new firmware, bare `nfc emulate` fallback on older. Verified `nfc_cli_command_emulate.c`.
- **`badusb_open()`** — `loader open "Bad USB"` only drops the user into the app's file browser; mainline `loader open` takes an app name, no file arg (verified `loader_cli.c`). Auto-running a chosen script needs RPC (below). Surface FlipperAgent's warning: BadUSB switches USB to HID and can drop the serial/RPC session mid-run.
- **UI macro: launch SubGHz Bruteforcer (Unleashed/RM, low/medium).** `sub-brute` and Frequency Analyzer are FAP apps with no CLI entry point, reachable only through the existing UI-automation DSL (`flipper_input_sequence`, `workflow_*` in ui.py). Add a best-effort menu macro alongside ui.py:159; menu order shifts between firmware, so the macro must inspect the screen and is not guaranteed.

### Needs RPC (see Transport plan)

- **`flipper_screenshot`** — RPC step 3 above.
- **`flipper_upload` / `flipper_download`** — RPC step 4 above.
- **BadUSB auto-run a specific script** — `Application.AppStartRequest{name='BadUsb', args='/ext/badusb/foo.txt'}` (FlipperAgent `modules/badusb/module.py:608`). CLI can only open the app.
- **`desktop_is_locked` / `app_lock_status`** — protobuf-only (`Desktop.IsLockedRequest`), no CLI equivalent; leave out of the CLI fork unless RPC lands. `find_my_flipper` similarly has no CLI command (BLE-beacon behavior).

**Do not import:** the busse/FlipperAgent NL->DuckyScript generator (`generator.py`, templates) is naive keyword-to-template matching, low value. Its MIT dangerous-pattern validator is worth cribbing (next section).

## Safety model

One recommended design: a single ~40-line `flipper_mcp/safety.py`, matching the existing `FLIPPER_DEFAULT_DEVICE`/`FLIPPER_PORT` env-var style, with no per-call flags (the invented-option pattern the house style strips). The fork already ships two ungated TX tools plus a raw-CLI escape hatch, so this is overdue, not pre-emptive.

Three pieces, all in `safety.py`:

1. **`require_tx(action)` env gate.** Reads `FLIPPER_ENABLE_TX` fresh each call (not a module constant, so it toggles without a server restart); raises `FlipperError` with a legality/responsibility message unless set to `1`/`true`/`yes`. Call as the first line of `ir_tx` (server.py:203), `subghz_tx_from_file` (server.py:161), and any future `subghz_tx`/`nfc_emulate`/`rfid_emulate`/`rfid_write`/`badusb_run`.
2. **`check_tx_frequency(hz)` allow-list.** `TX_BANDS` of `(lo, hi)` Hz windows, defaulting to the three wide ISM bands (300-348 / 387-464 / 779-928 MHz) but documented as narrowable to the user's region. Refuses aviation/cellular/emergency frequencies before the command is sent, giving a clear error instead of a cryptic device rejection. For `subghz_tx_from_file` the frequency lives in the `.sub`: read the file, `re.search(r'Frequency:\s*(\d+)', content)`, refuse if absent.
3. **`gate_raw_command(command)` for `flipper_execute`.** An ordered-prefix classifier (`_GATED_PREFIXES`: `subghz tx`, `ir tx`, `rfid write`, `ikey write`, `nfc emulate`, `factory_reset`, `storage format`, `update install`, `power off`, `power reboot`) that normalizes whitespace/case and routes matches through `require_tx`. Without this the escape hatch defeats every other gate. Verify prefix spellings against the target firmware CLI before shipping. Destructive commands ride the same `FLIPPER_ENABLE_TX` flag for simplicity (a second env var is possible but not recommended). Optionally also reject shell-chaining chars (`;`, `&&`, `|`, backticks, newlines) since the Flipper CLI is one-command-per-line.

Also detect out-of-band TX rejection: after a `subghz tx`/`tx_from_file`, scan the returned text for firmware rejection markers (`Frequency not supported`, `not in region`, `TX unsupported`; match substrings, not exact lines) and return a structured note pointing at the extended-range tool and `hardware_region_provisioned`, rather than pretending the TX succeeded.

Optionally crib the MIT DuckyScript validator (busse `modules/badusb/validator.py`, ~114 lines: `rm -rf /`, `format C:`, `curl|bash`, `invoke-expression`, `reg delete`) as an advisory pre-write check on any `storage write` to `/ext/badusb/*.txt`. Skip the full audit-log machinery; a single stderr line per gated TX is the right size if any record is wanted.

## Recommended next 3 PRs

1. **Correctness + tests:** fix the `ir_tx` `lstrip` bug (server.py:216-217), make `send()` prompt-aware to stop quiet-period truncation, add the dead-reader-thread reconnect, and add tests/test_bridge.py covering `_clean()` and `ir_tx` arg normalization.
2. **Safety module:** add `flipper_mcp/safety.py` with `require_tx`, the `TX_BANDS` frequency allow-list, and `gate_raw_command` wired into `ir_tx`, `subghz_tx_from_file`, and `flipper_execute`, documented in the README.
3. **Firmware awareness + CLI feature batch:** add the cached `firmware_detect` probe and gate the new CLI tools on it, shipping `power`, `power_info`, `datetime`, `rfid_write`/`emulate`, `ibutton` (`ikey`) emulate/write, `subghz_enable_extended_range`, and the corrected SubGHz/`/int` docstrings.
