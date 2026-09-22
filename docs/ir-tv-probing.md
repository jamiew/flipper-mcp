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

Prefer `ir_scan_and_identify`, but retain the raw output. The bundled registry
does not cover every protocol the firmware decodes.

Example: press Volume-Up on a Samsung remote, get back roughly:

```
Samsung32, A:0x0707, C:0x07
```

## 2. Build a button map

Repeat step 1 once per button, recording the decoded `command` for each. Most
TVs keep a fixed `address` and vary only `command`, so the map is just
`button -> command`. Common Samsung example bytes: Power `02`, Vol+ `07`,
Vol- `0B`, Ch+ `12`, Ch- `10`, Mute `0F` (verify against your capture, brands
and models differ).

## 3. Replay a specific command

- `ir_tx(protocol, address, command)` requires `FLIPPER_ENABLE_TX=1`.
  Pass numeric CLI hex unchanged. Space-separated bytes from saved `.ir`
  files are little-endian: `"07 00 00 00"` becomes numeric `"7"`.

```
ir_tx("Samsung32", "0707", "07")   # only if this matches your captured button
```

Watch the TV to confirm the mapping, then label that command in your map.

## Universal database (the "blast" path, button by button)

The firmware ships a universal remote DB. Unlike a blind power blast, you can
enumerate and send individual buttons:

- `ir_universal_list(category)` lists exact button names. Categories include
  `tv`, `audio`, `projectors`, `ac`, and `fans`, depending on installed assets.
- `ir_universal_send("tv", "Vol_dn")` sends every database entry for that button,
  not one TV-specific code. It is gated and needs physical confirmation.

## Gotchas

- All IR CLI operations depend on the firmware's IR CLI support and assets.
  A plugin-load error is a failure, not an empty successful capture. Keep
  firmware and SD assets matched; changing host Python code cannot repair
  missing firmware plugins.
- Only one host can hold the serial port. Close qFlipper and any
  lab.flipper.net browser tab before running captures.
- IR is line-of-sight and short-range. Aim the emitter (top edge of the Flipper)
  at the device and stay close.
