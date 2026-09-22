# Hardware validation

## Session state

Tested September 22, 2026, over USB. The user upgraded from Momentum mntm-010
to **mntm-012**, commit `e1784e74`, built December 31, 2025, API 87.1. The radio
reports alive. This identifies installed firmware, not the newest available release.

**132 tests and Ruff passed.** The server exposes 64 tools and `rf_triage`.
All 64 tools were invoked on mntm-010; 63 were re-invoked on mntm-012. The
clock setter was deliberately skipped after its earlier disruptive result.
Counts include ten default safety refusals and failed operations.

The later JVC session captured distinct Power and Volume Up RAW signals.
One 69-sample Volume Up burst was sent using an assumed 38 kHz carrier and
33% duty cycle. The command returned successfully, but **TV response is
unconfirmed**. The one-shot TX-enabled process exited; the normal MCP then
rejected `ir tx`, confirming its gate remained disabled.

Last observed state: connected, no app running, LED/vibration off, PA7 input.
All temporary device files, registry entries, and fixture servers were removed.
No SubGHz replay, credential writing, or emulation occurred. No personal saved
credentials were read. Resume from [PLAN.md](../PLAN.md).

## Evidence and limitations

- **Storage:** `first\nsecond` round-tripped as exactly 12 bytes, MD5
  `c65ef77ac0ad3db528bdecb15da9f5a1`. Synthetic NEC inspection worked; synthetic
  RAW SubGHz decoding completed without a match. Neither proves a real fob decoder.
- **Registry:** local HTTP fetch/install/describe/remove passed with SHA-256
  verification. Final state: 13 bundled, zero user-installed definitions.
- **Receivers:** IR, LF-RFID, iButton, and SubGHz started/stopped. JVC is the only
  deliberate target captured. SubGHz pulse timings may be noise; no fob was identified.
- **NFC:** mntm-010 returned a missing external-command error; mntm-012 timed out
  waiting for the CLI prompt. The next radio call reconnected and uptime continued
  increasing. The on-device NFC app launches; tag reading is unverified.
- **App closure:** mntm-012 says About must be closed manually. The host workflow
  correctly reports it still running. Back exits About/IR; NFC needed long Back;
  SubGHz needed an additional Back. Workflow menu selection needs visual confirmation.
- **Clock:** still February 2000. Setting it on mntm-010 dropped USB; later uptime
  was shorter and the clock unchanged. Cause is unresolved. Do not retry blindly.
- **Bluetooth:** `bt hci_info` returns controller metadata; CLI help exposes no
  discovery command. The five installed Bluetooth apps are `ble_spam`, `bt_trigger`,
  `findmy`, `hid_ble`, and `pc_monitor`. None was launched. Pairing remains untested.
- **GPIO:** PA7 input read 0; output write correctly refused in input mode. I2C
  scan found no devices. Real output/sensor tests need an isolated circuit.
- **Inventory:** 195 installed FAPs, up from 159. Enumeration covers
  `/ext/apps/*/*.fap`, not arbitrary nested directories.

## Tool coverage

Latest result on mntm-012 unless marked otherwise. **Data** means useful output;
**Command** means accepted, not physically confirmed; **Receiver** means the
receive path ran; **Gate** means disabled behavior was checked; **Attention**
means failure or incomplete hardware validation. The clock setter is **Skipped**.

| Tool | Result | Evidence / remaining check |
|---|---|---|
| `datetime_get` | Data | RTC reads February 2000. |
| `datetime_set` | Skipped | Prior mntm-010 call dropped USB; cause unresolved. |
| `flipper_cli` | Data | Bluetooth/IR usage and controller info; later RAW IR send accepted, TV response unknown. |
| `flipper_file_inspect` | Data | Synthetic NEC file classified with address/command fields. |
| `flipper_help` | Data | Firmware command inventory returned. |
| `flipper_hold_key` | Command | Short Down hold/release in About. |
| `flipper_info` | Data | mntm-012, API 87.1, live radio stack. |
| `flipper_input_sequence` | Command | Up/wait/down accepted in About. |
| `flipper_interrupt` | Command | Ctrl-C returned; later commands worked. |
| `flipper_press_key` | Command | Back/long Back exited tested apps. |
| `free` | Data | Heap and pool statistics returned. |
| `gpio_mode` | Command | PA7 configured as input. |
| `gpio_read` | Data | PA7 returned 0; not a sensor test. |
| `gpio_write` | Attention | Correctly refused because PA7 remained an input. |
| `i2c_scan` | Data | PC0/PC1 scan completed; no responding addresses. |
| `ibutton_emulate` | Gate | Disabled; no reader/key test. |
| `ibutton_read` | Receiver | Started/stopped; no contact key presented. |
| `ibutton_write` | Gate | Disabled; no key written. |
| `ir_rx` | Receiver | JVC Power and Volume Up RAW captures received. |
| `ir_scan_and_identify` | Receiver | Zero registry matches in readiness checks. |
| `ir_tx` | Gate | Decoded-protocol tool disabled; RAW replay used the CLI path separately. |
| `ir_universal_list` | Data | TV: Ch_prev, Vol_up, Ch_next, Mute, Vol_dn, Power. |
| `ir_universal_send` | Gate | Disabled; no universal blast. |
| `led` | Command | Blue/off accepted; physical illumination unconfirmed. |
| `list_installed_apps` | Data | 195 FAPs enumerated. |
| `loader_close` | Attention | About reported it must be closed manually. |
| `loader_info` | Data | App launches/exits and final idle state verified. |
| `loader_list` | Data | Built-in apps/settings returned. |
| `loader_open` | Command | About launched; loader state confirmed. |
| `nfc_detect` | Attention | Timed out waiting for CLI prompt. |
| `nfc_emulate` | Gate | Disabled; firmware compatibility unverified. |
| `power` | Gate | OTG-off refused; no power action performed. |
| `power_info` | Data | Battery and health both 100%; other telemetry returned. |
| `ps` | Data | Bounded top returned tasks and memory. |
| `registry_describe` | Data | Temporary installed entry returned. |
| `registry_fetch_index` | Data | Real loopback HTTP fixture fetched. |
| `registry_install` | Data | Fixture installed with verified SHA-256. |
| `registry_list` | Data | BLE category empty; bundled registry has no BLE entry. |
| `registry_remove` | Data | Only our temporary entry removed. |
| `registry_status` | Data | Returned to 13 bundled, zero installed. |
| `rfid_emulate` | Gate | Disabled; no credential emulated. |
| `rfid_read` | Receiver | LF-RFID started/stopped; no tag presented. |
| `rfid_write` | Gate | Disabled; no tag written. |
| `scan_and_identify` | Receiver | 315 MHz: zero decoded packets/matches. |
| `storage_info` | Data | FAT32 storage capacity/free space returned. |
| `storage_list` | Data | Temporary directory contents verified. |
| `storage_md5` | Data | Device checksum matched the exact 12-byte fixture. |
| `storage_mkdir` | Command | Unique temporary directory created. |
| `storage_read` | Data | Fixture returned with CLI Size header. |
| `storage_remove` | Command | Our fixtures and directory removed. |
| `storage_rename` | Command | Rename confirmed by listing. |
| `storage_stat` | Data | Exact 12-byte fixture size confirmed. |
| `storage_write` | Command | Exact text round trip; not a binary-upload API. |
| `subghz_chat` | Gate | Disabled because chat emits join/leave messages. |
| `subghz_decode_raw` | Data | Synthetic file decoded offline; zero packets. |
| `subghz_rx` | Receiver | 433.92 MHz started/stopped; zero decoded packets. |
| `subghz_rx_raw` | Receiver | Signed pulse timings returned; no target identified. |
| `subghz_tx_from_file` | Gate | Disabled; no RF replay. |
| `uptime` | Data | Increased from 1h22m31s to 1h26m15s during retest. |
| `vibro` | Command | On/off accepted; physical vibration unconfirmed. |
| `workflow_close_app` | Attention | Correctly reported About still running. |
| `workflow_infrared_learn_start` | Command | IR launched; navigation accepted, screen unverified. |
| `workflow_nfc_read_start` | Command | NFC launched; no real tag read. |
| `workflow_subghz_read_start` | Command | SubGHz launched; exact screen/frequency unverified. |

The separate `rf_triage` prompt and 64-tool enumeration also passed through a
fresh stdio MCP connection during modernization. Protocol negotiation returned
`2026-07-28`. That check preceded the firmware update; it is host-side evidence.

## References

- [IR capture, replay limits, and retained JVC samples](ir-tv-probing.md)
- [Transport fixes and invariants](dev-notes.md)
- [Changes](../CHANGELOG.md)
- [Official MCP SDK migration guide](https://py.sdk.modelcontextprotocol.io/migration/)

Hardware observations above come from the connected device, not assumptions
about firmware source or advertised capabilities.
