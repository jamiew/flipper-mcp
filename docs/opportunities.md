# Flipper-MCP Opportunity Report

Historical research, not the active plan. Items since shipped (the `ir_tx`
fix, transport fixes, the TX safety gate, and the power, clock, emulation and
write tools) were removed. Resume from [PLAN.md](../PLAN.md); consult
[hardware validation](hardware-validation.md) for verified capabilities.

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

- **`badusb_open()`** — `loader open "Bad USB"` only drops the user into the app's file browser; mainline `loader open` takes an app name, no file arg (verified `loader_cli.c`). Auto-running a chosen script needs RPC (below). Surface FlipperAgent's warning: BadUSB switches USB to HID and can drop the serial/RPC session mid-run.
- **UI macro: launch SubGHz Bruteforcer (Unleashed/RM, low/medium).** `sub-brute` and Frequency Analyzer are FAP apps with no CLI entry point, reachable only through the existing UI-automation DSL (`flipper_input_sequence`, `workflow_*` in ui.py). Add a best-effort menu macro alongside ui.py:159; menu order shifts between firmware, so the macro must inspect the screen and is not guaranteed.

### Needs RPC (see Transport plan)

- **`flipper_screenshot`** — RPC step 3 above.
- **`flipper_upload` / `flipper_download`** — RPC step 4 above.
- **BadUSB auto-run a specific script** — `Application.AppStartRequest{name='BadUsb', args='/ext/badusb/foo.txt'}` (FlipperAgent `modules/badusb/module.py:608`). CLI can only open the app.
- **`desktop_is_locked` / `app_lock_status`** — protobuf-only (`Desktop.IsLockedRequest`), no CLI equivalent; leave out of the CLI fork unless RPC lands. `find_my_flipper` similarly has no CLI command (BLE-beacon behavior).

**Do not import:** the busse/FlipperAgent NL->DuckyScript generator (`generator.py`, templates) is naive keyword-to-template matching, low value. Its MIT dangerous-pattern validator is worth cribbing (below).

## Safety follow-ups

`safety.py` ships the `FLIPPER_ENABLE_TX` gate, SubGHz frequency windows, and the raw-CLI classifier. Still open:

- Detect out-of-band TX rejection: after a `subghz tx`/`tx_from_file`, scan the returned text for firmware rejection markers (`Frequency not supported`, `not in region`, `TX unsupported`; match substrings, not exact lines) and point at `hardware_region_provisioned`, rather than pretending the TX succeeded.
- Optionally crib the MIT DuckyScript validator (busse `modules/badusb/validator.py`, ~114 lines: `rm -rf /`, `format C:`, `curl|bash`, `invoke-expression`, `reg delete`) as an advisory pre-write check on any `storage write` to `/ext/badusb/*.txt`.
