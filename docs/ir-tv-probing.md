# Probing an IR device (e.g. a TV) with the MCP

Goal: figure out what each button on an unknown remote does, then reproduce
individual commands, not just the universal "blast power" sweep.

The loop is **capture → identify → replay**, using three tools.

## 1. Capture what a real remote sends

Point the target remote at the top of the Flipper and press one button while
`ir_rx` listens.

- `ir_rx(duration_s=10)` -- raw listen. Returns the CLI decode lines.
- `ir_scan_and_identify(duration_s=10)` -- same capture, then fingerprints the
  output against the bundled protocol registry and returns structured matches
  (protocol id, decoded address/command, typical devices, references).

Prefer `ir_scan_and_identify`: it tells you the protocol name and the exact
`address` / `command` bytes in one step.

Example: press Volume-Up on a Samsung remote, get back roughly:

```
protocol: Samsung32   address: 07 07   command: 07 00
```

## 2. Build a button map

Repeat step 1 once per button, recording the decoded `command` for each. Most
TVs keep a fixed `address` and vary only `command`, so the map is just
`button -> command`. Common Samsung example bytes: Power `02`, Vol+ `07`,
Vol- `0B`, Ch+ `12`, Ch- `10`, Mute `0F` (verify against your capture, brands
and models differ).

## 3. Replay a specific command

- `ir_tx(protocol, address, command)` -- transmit one decoded signal. Accepts
  space-separated bytes (`"07 07"`) or concatenated hex (`"0707"`); spaces are
  stripped for you.

```
ir_tx("Samsung32", "0707", "0700")   # volume up
```

Watch the TV to confirm the mapping, then label that command in your map.

## Universal database (the "blast" path, button by button)

The firmware ships a universal remote DB. Unlike a blind power blast, you can
enumerate and send individual buttons:

- `ir_universal_list(category)` -- list buttons for a category (`tv`, `audio`,
  `projector`, `ac`).
- `ir_universal_send(category, button)` -- send one, e.g.
  `ir_universal_send("tv", "Power")`. Good for control before you've decoded the
  real remote.

## Gotchas

- `ir_tx` needs the firmware's external `cli_ir.fal` plugin loaded. If it
  returns "failed to load external command", update firmware via qFlipper to
  refresh external CLI plugins. `ir_rx`, `ir_scan_and_identify`, and
  `ir_universal_*` do not need it, so start there.
- Only one host can hold the serial port. Close qFlipper and any
  lab.flipper.net browser tab before running captures.
- IR is line-of-sight and short-range. Aim the emitter (top edge of the Flipper)
  at the device and stay close.
