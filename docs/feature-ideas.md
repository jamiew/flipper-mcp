# Feature ideas / roadmap

Prioritized additions drawn from the [landscape](landscape.md) gap analysis.
Principle: extend Str1ck9's moat (signal *identification* + UI automation), don't
just chase tool count. Grouped by leverage vs effort.

## The transport question (blocks tier 1a)

Str1ck9 is a **pure USB-CLI-text** bridge. Several high-value features
(screenshot, binary file push) need the **protobuf RPC** framebuffer/storage
channel, which the CLI can't reach. Options:

1. Add an optional protobuf-RPC path alongside the CLI bridge (what busse /
   millsymills / yairhdz24 do). Biggest architectural change; unlocks the most.
2. Stay CLI-only and accept those features are out of scope.

Decision needed before tier 1a. Everything in tier 1b and below works over the
existing CLI transport.

## Tier 1 — highest leverage

**1a. Needs protobuf RPC:**
- **Screenshot** (`GuiScreenFrame` → image). Lets the agent *see* the screen.
  Have it: yairhdz24, pogorelov, clipper. Biggest single capability gap.
- **Binary file upload** (push .sub/.nfc/.ir/.fap). Str1ck9's `storage_write` is
  text-only (reads to Ctrl-C). Needed to install captures and apps. Have it:
  yairhdz24 (`upload_file`, base64), millsymills (`fs_push`/`fs_pull`).

**1b. Works over existing CLI transport:**
- **Device emulation** — `nfc_emulate`, `rfid_emulate`, `ibutton_emulate`, and
  `rfid_write`. This is the write-half of the clone workflow that pairs directly
  with Str1ck9's read/identify tools. Have it: roostercoop, clipper, FlipperAgent.
- **Reboot** (`reboot`, DFU mode). Trivial CLI command; currently absent.
- **BadUSB run** — execute a DuckyScript already on the device. Str1ck9 can write
  the file but not launch it.

## Tier 2 — solid wins, moderate effort

- **BadUSB generate + validate** — NL → DuckyScript with a safety validator.
  busse has a full 10-tool module (reusable, MIT).
- **Power / battery / OTG info and control.** clipper, yairhdz24, millsymills.
- **Housekeeping reads** — datetime get/set, `desktop_is_locked`,
  `app_lock_status`, `app_get_error`, `i2c_scan`. Cheap, useful. millsymills.
- **`find_my_flipper`** — one-shot buzz+LED locate. yairhdz24, pogorelov.
- **Vision → IR/RF identification** — photograph a remote, identify the protocol.
  Pairs naturally with the fingerprint registry. promptzero has it.

## Tier 3 — bigger bets / niche

- **MIFARE Classic key recovery** (`mfkey_crack`). Strong differentiator; only
  clipper has it. Non-trivial to port.
- **FAP scaffold/build/deploy** (ufbt). Needs a host toolchain. yairhdz24.
- **Firmware flashing.** millsymills has a gated multi-flavor installer.
- **Wireless transport** (WiFi bridge or BLE). Convenience, large effort.
- **WiFi/Marauder, BLE recon/HID.** Whole domains; promptzero/FlipperAgent. Big
  scope, arguably a different product.

## Cross-cutting: adopt a safety model before adding TX/emulation

Str1ck9 currently executes every tool immediately. Before shipping emulation,
BadUSB-run, or more TX, add gating. Best references:
- **millsymills** — env flags (`ENABLE_TX_TOOLS` etc.) + per-call
  `i_accept_responsibility` + a CLI risk classifier.
- **clipper** — a single runtime `CLIPPER_SAFETY` toggle + a SubGHz frequency
  allow-list. Simplest to adopt.

## Worth stealing regardless

- **pogorelov's self-evolving knowledge base** — the agent reads docs before
  acting and writes lessons back. Philosophically close to our protocol registry;
  could extend the registry from "protocols" to "learned device maps" (e.g. the
  TV button map from [`ir-tv-probing.md`](ir-tv-probing.md)).
