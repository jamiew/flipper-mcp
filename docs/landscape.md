# Flipper Zero MCP / AI-control landscape

Inventory of projects that let an AI drive a Flipper Zero, as of 2026-08-08.
Tool surfaces were read from source, not from READMEs. This fork's baseline is
[Str1ck9/flipper-mcp](https://github.com/Str1ck9/flipper-mcp).

## Name collisions (not Flipper-device projects)

- `flippercloud/flipper-mcp` -- feature-flag software (the Ruby "Flipper" lib).
- `ElectronicCats/flipper-MCP2515-CANBUS` -- a CAN-bus chip project.
- `RafaVS/flipper-mcp` -- Meta's *Flipper* Android debugger.
- `jaylane/momentum-mcp` -- README only, no code.

"Reverse direction" projects (Flipper acts as a remote/indicator *for* a coding
agent, not the other way round) are also a crowded, easy-to-confuse space:
`Wet-wr-Labs/claupper`, `w3t-wr3/claude-remote`, `xxond/flipper-buddy`, and more.

## The device-control field (10 projects)

| Project | Lang | ★ | Transport | Tools | Focus |
|---|---|---|---|---|---|
| **Str1ck9/flipper-mcp** (baseline) | Py | 2 | USB CLI text | ~54 | RF/IR + protocol registry + UI automation |
| busse/flipperzero-mcp | Py | 27 | USB protobuf RPC / WiFi | 15 | BadUSB (original) |
| millsymills-com/flipperzero-mcp | Py | 4 | USB RPC + CLI / WiFi | 28 | Hardened fork of busse; best-tested |
| roostercoopllc/flipper-mcp | Rust | 14 | **on-ESP32** HTTP/WiFi | ~45 | Runs on the devboard; full radios + BLE-HID + C2 |
| xunholy/promptzero | Go | 214 | USB / BLE | ~706 | NL operator; WiFi/Marauder; vision |
| jonastbrg/FlipperAgent | Py | 8 | USB + laptop BLE/net | 65 | Autonomous campaigns; Marauder; BLE GATT |
| mattyspangler/AgentFlipper | Py | 44 | USB (PyFlipper) | 1+RAG | Self-contained LangChain agent + RAG |
| yairhdz24/flipper-mcp | Py | 0 | USB protobuf RPC | ~40 | FAP build/deploy; screenshot |
| pogorelov-labs/flipper-ble-mcp | Py | 0 | **BLE** (macOS) | 38 | Cable-free; self-evolving KB; healthwatch |
| Realgagenichols/clipper | Py | 1 | USB RPC (Momentum) | 32 | MIFARE key cracking; runtime safety gate |

## Capability matrix

`full` = dedicated real coverage · `part` = read-only/single-op/app-driven ·
`cli` = only via a raw-CLI escape hatch · `—` = absent.

| Project | subghz | nfc | rfid | ir | ibutton | gpio | badusb | storage | screenshot | UI | firmware | ble | wifi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Str1ck9** | full | part | part | full+uni | part | full | — | full | — | **full** | — | — | — |
| busse | — | — | — | — | — | — | **full** | — | — | — | — | stub | — |
| millsymills | cli | cli | cli | cli | cli | part | — | full | — | — | **full** | — | — |
| roostercoop | full | full+em | full+em | full | full+em | full | via BLE | full | — | — | — | **full** | — |
| promptzero | full+ | full+ | full | full | full | full | full | full | — | — | flash | part | **full** |
| FlipperAgent | full | full | full+wr | full | — | full | **full** | full | — | — | — | **full** | **full** |
| AgentFlipper | cli | cli | cli | cli | cli | cli | cli | cli | — | — | — | — | — |
| yairhdz24 | part | cli | cli | full+uni | — | full | — | full+bin | **full** | part | — | — | — |
| pogorelov | part | — | — | part | — | full | **full** | full | **full** | **full** | — | (tport) | — |
| clipper | full | part | full+em | full | part | part | **full** | full | **full** | part | — | — | — |

## What's unique to each

- **Str1ck9 (our baseline):** the only one with an **RF protocol registry +
  fingerprinter** (`scan_and_identify`, `ir_scan_and_identify`,
  `flipper_file_inspect`, remote registry sync with SHA-256). No competitor
  identifies *what a captured signal is*; they capture and replay blindly. Also
  the richest UI-automation DSL (`flipper_input_sequence`, `workflow_*`).
- **clipper:** `flipper_mfkey_crack` (MIFARE Classic key recovery).
- **roostercoop:** MCP server running on the ESP32 itself; Flipper-to-Flipper
  SubGHz C2 channel.
- **yairhdz24:** `fap_scaffold`/`fap_build`/`fap_deploy` (write+compile+install a
  FAP from the agent).
- **pogorelov:** cable-free BLE transport; a self-evolving knowledge base the
  agent reads and writes back to; scheduled `healthwatch`.
- **promptzero:** vision (photo of a remote → IR protocol ID); ~85 WiFi/Marauder
  tools; by far the largest tool surface.
- **millsymills:** the most rigorous safety model (3 env flags + per-call
  `i_accept_responsibility` + a CLI risk classifier) and the best test suite
  (golden fixture replay, coverage gate, bandit/codeql/pip-audit).

## Takeaway for this fork

Str1ck9's moat is *identification* (registry + fingerprinting) plus UI
automation. The highest-leverage gaps to close without diluting that focus are
screenshot, device emulation (the write-half of clone workflows), BadUSB, binary
file upload, and reboot. Full analysis and priorities in
[`feature-ideas.md`](feature-ideas.md).
