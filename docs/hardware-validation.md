# Hardware validation and capture readiness

Tested September 22, 2026, through the local MCP over USB. Firmware was Momentum mntm-010, built April 30, 2025. Firmware was not updated. No saved credentials were read, copied, written, or emulated. No SubGHz or IR transmission was performed.

## Result

The local MCP works, now uses MCP Python SDK 2.2.0, and exposes 64 tools plus the `rf_triage` prompt. All 64 tools were invoked at least once. That includes disabled-TX refusals and failed operations, not 64 successful hardware tests. The existing `.mcp.json` loads this editable checkout; no additional configuration file is needed.

Device status, storage operations, task listing, IR reception, LF-RFID reception, SubGHz reception/raw capture, registry operations, and basic UI input responded. This is not proof that a real remote or fob was decoded: no target was deliberately presented. Raw SubGHz reception returned pulse timings, which may include noise.

Two disruptive observations need human attention before longer sessions:

1. `datetime_set(iso="")` lost USB and subsequent device discovery failed. The device later reappeared with a shorter uptime, but its clock still read February 17, 2000. The command format matches the firmware source. A causal firmware diagnosis is not established; do not retry the setter blindly.
2. NFC UI launched, but `loader close` reported closure while `loader info` still reported NFC running. Launching the next app timed out; USB later disappeared again. After recovery, About also remained running after `loader close`. The repaired workflow now reports that failure, and the busy-app guard prevented navigation into the wrong app on hardware. Back-button exit worked.

The device recovered and the final USB checks succeeded. Firmware remains mntm-010, the radio reports alive, and no app is running. LED and vibration were turned off. PA7 was left configured as an input after its read test. Use Back to exit apps for now; avoid the clock setter and do not treat `loader close` acknowledgment as proof of closure.

## Local modernization and repairs

- Migrated from removed `mcp.server.fastmcp` to official `mcp.server.MCPServer`, with `mcp>=2.2,<3`. Updated the lockfile and installed development dependencies with `uv`.
- Serialized complete tool calls for SDK v2 worker threads and complete serial transactions for direct bridge callers.
- Fixed command completion: echo silence is not success. A settled trailing prompt is required; failures retire the connection. Streaming commands that finish early no longer receive a stray Ctrl-C.
- Fixed an observed response leak: universal IR button names were arriving in the next GPIO call before the transport repair.
- Fixed exact text writes. CRLF after `storage write` previously inserted an unwanted leading LF into the file. Writes now use CR and preserve the supplied content, including whether it ends with a newline.
- Corrected `ps` to bounded `top`, GPIO read to `gpio read`, GPIO mode to numeric input/output, and LED control to one command per channel.
- Corrected universal IR send syntax to `ir universal <category> <button>` and the firmware category/button names.
- Corrected saved IR little-endian byte conversion. `EA C7 00 00` represents numeric `C7EA`, not `EAC70000`. Numeric CLI hex remains numeric.
- Corrected NEC comma-delimited and SIRC15/SIRC20 capture matching, plus case-insensitive decoder-field extraction from saved IR files.
- Made known firmware failures and validation failures produce MCP errors instead of successful-looking error strings.
- Hardened raw command controls and TX/destructive gates, including universal IR, SubGHz chat, external power rails, and update restore. Saved SubGHz transmission now checks its Frequency field against hardware windows. These windows do not grant legal permission to transmit.
- Prevented protocol-cache path traversal and mutation through symlink entries. SHA-256 checking remains integrity checking, not publisher authentication.
- Made app-close workflow completion depend on observed idle state. Workflow launches refuse to navigate an already-running app.

## Verification evidence

- `uv run --no-sync ruff check flipper_mcp tests`: passed.
- `uv run --no-sync pytest`: 132 passed.
- Fresh real stdio MCP process negotiated protocol `2026-07-28`; enumerated 64 tools; returned registry data and the triage prompt; rejected disabled TX and cache traversal.
- Mounted Oh My Pi tools were restarted and exercised against the updated local server.
- Exact file round trip on hardware: `first\nsecond`, 12 bytes, device MD5 `c65ef77ac0ad3db528bdecb15da9f5a1`, matching the host checksum. Temporary files and directory were removed.
- Cache traversal, symlink overwrite, saved IR field extraction, and IR byte-order/capture-format regressions failed before their fixes and passed afterward.
- Receiver start/stop and subsequent commands were exercised. No deliberate remote/fob input or physical transmitter measurement was available.
- Coverage: 27 data results, 15 accepted command/control checks, 7 receiver checks, 10 default safety-gate checks, and 5 entries needing attention. These 64 rows exactly match the server's tool inventory.

## Complete tool coverage

Status meanings:

- **Data**: returned useful device or local data.
- **Command**: firmware accepted the operation; physical effect or target behavior needs human confirmation.
- **Receiver**: entered and exited reception; target decoding is not established.
- **Gate**: default-disabled behavior verified, not physical transmission/write behavior.
- **Attention**: failed, incomplete, or incompatible on this device.
- **Deferred**: no safe meaningful hardware test completed.

| Tool | Result | Evidence and remaining check |
|---|---|---|
| `datetime_get` | Data | Read RTC; date remains in 2000 after the failed setter. |
| `datetime_set` | Attention | USB disappeared during the call; later shorter uptime and unchanged date. Do not repeat without investigating the screen/firmware. |
| `flipper_cli` | Data | Read `bt`, GPIO, IR usage and bounded `top`; after recovery, `bt hci_info` returned HCI version and controller metadata. |
| `flipper_file_inspect` | Data | Classified our temporary NEC `.ir` file. Field extraction defect was repaired and covered locally. |
| `flipper_help` | Data | Returned installed firmware command names. |
| `flipper_hold_key` | Command | Sent a short hold/release in About. Physical selection movement not observed. |
| `flipper_info` | Data | Identified Momentum mntm-010, target 7, US provisioning, live radio stack. |
| `flipper_input_sequence` | Command | Executed up/wait/down in About. No screen capture available. |
| `flipper_interrupt` | Command | Ctrl-C returned and subsequent status calls worked before the later UI failure. |
| `flipper_press_key` | Command | Back exited About; `loader_info` confirmed no running app. |
| `free` | Data | Returned heap/pool statistics. |
| `gpio_mode` | Command | Configured PA7 as input; firmware confirmed the mode. Output mode was not enabled. |
| `gpio_read` | Data | After input configuration, PA7 returned 0. This is not a calibrated external-sensor test. |
| `gpio_write` | Attention | Safely rejected because PA7 remained an input. Tool reached firmware; actual output driving still needs an isolated circuit and meter/loopback. |
| `i2c_scan` | Data | Completed 100 kHz external-bus scan on PC0/PC1; no addresses responded. |
| `ibutton_emulate` | Gate | Rejected with TX disabled. Needs an owned compatible reader/key. |
| `ibutton_read` | Receiver | Entered iButton read and stopped; no contact key presented. |
| `ibutton_write` | Gate | Rejected with TX disabled. Needs a disposable writable key; never test on the only working credential. |
| `ir_rx` | Receiver | Entered and exited IR receive without a target signal. |
| `ir_scan_and_identify` | Receiver | Returned raw receiver status and zero matches. Real-remote capture still needed. |
| `ir_tx` | Gate | Rejected with TX disabled. Correct byte-order behavior verified locally; actual TV response not tested. |
| `ir_universal_list` | Data | Complete TV list: Ch_prev, Vol_up, Ch_next, Mute, Vol_dn, Power. No response leakage after transport fix. |
| `ir_universal_send` | Gate | Rejected with TX disabled. Corrected firmware syntax; no universal blast sent. |
| `led` | Command | Updated per-channel blue/off commands accepted. Physical illumination not independently observed. |
| `list_installed_apps` | Data | Enumerated 159 FAPs in the supported one-level category layout. Does not recursively enumerate deeper directories. |
| `loader_close` | Attention | Idle invocation returned no running app. For live apps, closure acknowledgment did not establish actual exit; use Back and verify `loader_info`. |
| `loader_info` | Data | Confirmed About launch/exit, NFC launch, and the failed NFC closure state. |
| `loader_list` | Data | Returned built-in app and settings names. |
| `loader_open` | Command | About launched and was confirmed by `loader_info`. |
| `nfc_detect` | Attention | Firmware returned `failed to load external command`; now surfaced as an MCP error. Firmware source for mntm-010 also does not expose `nfc detect`. |
| `nfc_emulate` | Gate | Rejected with TX disabled. Command compatibility and actual emulation are not verified. |
| `power` | Gate | Reboot rejected with TX disabled. Did not intentionally reboot, shut down, enter DFU, or enable external power. |
| `power_info` | Data | Battery 100%, health 100%; returned voltage/current/temperature data. |
| `ps` | Data | Corrected bounded `top` returned thread/task and heap information. |
| `registry_describe` | Data | Returned NEC metadata and the temporary installed protocol. |
| `registry_fetch_index` | Data | Fetched a real local HTTP fixture index, not a mocked network response. Public-registry availability not tested. |
| `registry_install` | Data | Downloaded fixture, verified SHA-256, installed, then exposed it through describe. |
| `registry_list` | Data | Listed bundled IR protocols; registry contains 13 bundled entries. |
| `registry_remove` | Data | Removed only our temporary installed protocol. Invalid path ID rejected by final mounted runtime. |
| `registry_status` | Data | Confirmed 13 bundled and zero user-installed entries after cleanup. |
| `rfid_emulate` | Gate | Rejected with TX disabled. No building credential emulated. |
| `rfid_read` | Receiver | Entered LF-RFID read, stopped cleanly; no tag presented. |
| `rfid_write` | Gate | Rejected with TX disabled. No physical card write attempted. |
| `scan_and_identify` | Receiver | 315 MHz scan returned zero decoded packets and zero registry matches. |
| `storage_info` | Data | FAT32 SD card, approximately 29.6 GiB free. |
| `storage_list` | Data | Listed root/app/test directories without reading personal saved credentials. |
| `storage_md5` | Data | Device checksum matched host after the file-framing fix. |
| `storage_mkdir` | Command | Created a unique temporary directory, later removed. |
| `storage_read` | Data | Returned the temporary file contents. CLI includes a `Size:` line; this is not a binary-download API. |
| `storage_remove` | Command | Removed only files/directory created by this sweep; missing-file check confirmed removal. |
| `storage_rename` | Command | Renamed the temporary `.ir` file; directory listing confirmed it. |
| `storage_stat` | Data | Reported temporary-file sizes and missing paths. Missing-file errors now use MCP error status. |
| `storage_write` | Command | Exact multiline text round trip and checksum verified after the CRLF fix. Not a binary-upload API. |
| `subghz_chat` | Gate | Rejected with TX disabled. Chat emits join/leave messages, so it is not passive reception. |
| `subghz_decode_raw` | Data | Read our synthetic RAW fixture offline and reported zero packets. This verifies the decoder path, not successful protocol decoding. |
| `subghz_rx` | Receiver | 433.92 MHz receiver started/stopped; zero decoded packets in the short window. |
| `subghz_rx_raw` | Receiver | Returned signed pulse timings at 433.92 MHz. Timings alone do not identify a transmitter. |
| `subghz_tx_from_file` | Gate | Rejected with TX disabled. No RF replay; saved-file frequency check added. |
| `uptime` | Data | Returned before and after recovery; shorter uptimes established intervening reboots. Final status calls succeeded. |
| `vibro` | Command | On/off accepted; physical vibration needs human confirmation. |
| `workflow_close_app` | Attention | Final code correctly reported About still running after close; idle no-op returned verified idle state. Back exited the app. |
| `workflow_infrared_learn_start` | Command | Final busy-app guard rejected launch over About. From idle, Infrared launched and accepted navigation; Back returned idle. Selected screen still needs physical confirmation. |
| `workflow_nfc_read_start` | Command | NFC app launched and received the read-navigation input. Actual selected screen/tag reading needs human confirmation; avoid the unreliable CLI-close path. |
| `workflow_subghz_read_start` | Command | After recovery, Sub-GHz launched and accepted Read navigation. Back returned idle; exact screen/frequency needs physical confirmation. |

The separate `rf_triage` MCP prompt returned successfully over a fresh stdio connection.

## Capture setup

### TV remote: preferred first target

1. Return the Flipper to its main screen. Confirm `loader_info` says no application is running.
2. Place the remote near the top of the Flipper. Start `ir_scan_and_identify(duration_s=10)` and press one harmless button, such as Volume Down, two or three times.
3. Preserve the raw line, for example `Samsung32, A:0x0707, C:0x07`. These are examples, not an assumed mapping for this TV.
4. If the registry finds nothing but firmware decoded a named protocol, use the raw protocol/address/command. If output is RAW, a timing-based replay workflow is needed; do not invent a protocol.
5. Enable TX only for the targeted session after reviewing the captured command. `ir_tx` can replay numeric A:/C: hex unchanged. Aim at the owned TV and have a person confirm its response.
6. Leave TX disabled again afterward. A universal database send tries many codes for the selected button and may affect more than the intended TV.

The current `.mcp.json` deliberately has no persistent TX enablement. A temporary server session can set `FLIPPER_ENABLE_TX=1` when a specific transmission is ready; close the other USB-owning MCP first. Do not run two serial clients at once.

### Building fob: identify, then choose the receiver

For the reported rolling-code fob, start with its physical form and technology, not a replay attempt:

- A tap-only fob may use LF-RFID or NFC. LF-RFID reception works here; place an owned fob at the back of the Flipper during `rfid_read(duration_s=10)`.
- NFC CLI detection is incompatible on this setup. The NFC UI launched, but its close path needs recovery testing before using it for a real read. Do not promise an automatic host-side NFC dump from these tools.
- A button-operated RF fob needs its actual frequency, ideally from labeling or an FCC ID. Then use a short `scan_and_identify` or `subghz_rx_raw` window on that frequency.
- Detection is not key recovery or a working copy. Rolling-code captures generally cannot be reused as static replays; unsynchronized presses/replays can affect receiver synchronization. Avoid repeated presses away from the reader, jamming, counter manipulation, credential writes, or access-system changes. Building-system administration needs the operator's authorization.

No fob data was captured during this sweep.

### Bluetooth

There is no Bluetooth discovery tool in this MCP. The installed firmware's `bt` usage exposed `hci_info`, not a general nearby-device scan. Installed Bluetooth apps are not proof of scanner support; advertising/spam apps are not substitutes for scanning. A separate host BLE scanner or a specifically compatible Flipper app/firmware would need its own setup and validation. Nothing was installed or broadcast for Bluetooth.

### GPIO and I2C

Before any output test, confirm what is attached to the GPIO header. Use a known free pin and meter/loopback. A digital value from an unconnected floating input is not proof of a sensor. I2C scanning should use a known 3.3V-compatible peripheral if a positive result is required. External-power toggles remain disabled.

## Remaining human checks

- Device is connected and idle now. If it drops again, inspect the screen and record any crash message before reconnecting.
- Investigate the clock-setting failure and leave the setter alone meanwhile.
- Use Back to exit apps and verify idle state. The new close verification catches the failure; it does not repair firmware app shutdown.
- Present an owned IR remote, LF-RFID/NFC fob, or iButton key for positive-input tests.
- Confirm LED and vibration physically, and confirm a targeted TV command only after capturing it.
- Firmware and SD asset repair may be necessary for NFC CLI support. This session intentionally did not flash firmware or install device apps.

## Sources

- [Official MCP SDK v2 migration guide](https://py.sdk.modelcontextprotocol.io/migration/)
- [Momentum mntm-010 CLI date implementation](https://github.com/Next-Flip/Momentum-Firmware/blob/mntm-010/applications/services/cli/cli_main_commands.c)
- [Momentum mntm-010 IR command syntax and receive format](https://github.com/Next-Flip/Momentum-Firmware/blob/mntm-010/applications/main/infrared/infrared_cli.c)
- [Momentum saved IR signal representation](https://github.com/Next-Flip/Momentum-Firmware/blob/mntm-010/applications/main/infrared/infrared_signal.c)
- [Momentum mntm-010 NFC CLI surface](https://github.com/Next-Flip/Momentum-Firmware/blob/mntm-010/applications/main/nfc/nfc_cli.c)
