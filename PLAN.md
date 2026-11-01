# Resume plan

Paused September 22, 2026. No further hardware testing is scheduled until the user returns.

## Current state

- Local MCP modernization is committed in `3553ba7`. Official MCP SDK 2.2.0; 64 tools and the `rf_triage` prompt.
- User updated the Flipper to Momentum **mntm-012**, commit `e1784e74`, built December 31, 2025. This is the observed installed version, not a check of the latest release.
- **132 tests and Ruff passed.** All 64 tools were invoked on mntm-010; 63 were re-invoked on mntm-012, including ten safety-gate checks. The clock setter was deliberately skipped.
- JVC **Power and Volume Up** produced distinct, repeatable RAW IR captures. One 69-sample Volume Up burst was sent at an assumed 38 kHz and 33% duty cycle. Firmware accepted it; **the user has not confirmed any TV response**.
- TX was enabled only in an exited one-shot process. The normal MCP's disabled TX gate was verified afterward. `.mcp.json` was not changed.
- Last observed device state: connected, no app running, LED/vibration off, PA7 input. Temporary storage and registry fixtures were removed. No SubGHz replay, credential writing, or emulation occurred.

## Resume in this order

1. **Check connection and idle state.** Close competing USB clients, then call `flipper_info` and `loader_info`. Do not assume the saved hardware state still applies.
2. **Finish the TV test.** Ask whether the last Volume Up replay changed the TV volume. If unknown, arrange one observed retry. Use the saved [JVC timings and carrier caveat](docs/ir-tv-probing.md#jvc-session-september-22-2026), not a universal blast. Do not leave TX enabled afterward.
3. **Identify the fob before scanning.** Ask whether it is tap-only or has buttons, and get its model/FCC ID if applicable. Use LF-RFID for a compatible tap token; the NFC UI is the fallback for NFC. Select SubGHz frequency from evidence for a button remote. No rolling-code replay or credential writes.
4. **Test Bluetooth connectivity.** Pair through the official Flipper phone app with the user's screen confirmation. This MCP exposes controller info, not nearby-device scanning. Select a separately verified scanner only if discovery is still wanted; do not substitute BLE spam.

## Known blockers

- `nfc_detect` times out on mntm-012. The on-device NFC app launches; no actual tag has been read. Likely cause, from the Momentum source and not yet confirmed on hardware: `nfc` ignores its arguments and opens an interactive subshell with a `[nfc]>:` prompt. The bridge only accepts the top-level `>:` prompt, and Ctrl-C does not leave the subshell (`exit` does). `nfc_detect` and `nfc_emulate` need a subshell-aware rewrite (`nfc`, then `scanner` or `emulate`, then `exit`) tested on the device.
- `loader_close` says About must be closed manually. Use Back/long Back and confirm idle with `loader_info`; workflow launch does not prove the selected screen.
- RTC still reads February 2000. Setting it dropped USB on mntm-010. Do not retry blindly; investigate separately or use the device's clock settings with human confirmation.
- GPIO output, positive I2C detection, fob/iButton decoding, Bluetooth pairing, and the TV's response remain unverified.

[Hardware evidence](docs/hardware-validation.md) records coverage and limits. Historical roadmap documents are research, not the next-session checklist.
