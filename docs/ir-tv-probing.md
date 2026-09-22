# IR capture and playback

## Capture one button

1. Close competing USB clients. Confirm `loader_info` reports no running app.
2. Aim the remote at the Flipper's top IR window from 2–8 inches away.
3. Start `ir_rx(duration_s=15)` or `ir_scan_and_identify(duration_s=15)`, then
   press one named button three times. Announce the window before starting it.
4. Retain the received output and button label. A registry miss does not mean
   no signal: firmware may return a decoded protocol or RAW pulse timings.

## Replay only after review

- **Decoded:** use `ir_tx(protocol, address, command)`. Numeric CLI hex stays
  numeric; saved `.ir` byte arrays are little-endian (`EA C7 00 00` → `C7EA`).
- **RAW:** mntm-012 exposes `ir tx RAW F:<Hz> DC:<percent> <timings...>` through
  `flipper_cli`, with at most 512 samples. The receive output does not establish
  the carrier frequency or duty cycle. Record assumptions; do not invent a
  decoded protocol from the remote's brand.
- Enable `FLIPPER_ENABLE_TX=1` only in a temporary process for an authorized
  targeted replay. Close the existing USB owner first, send once, close that
  process, and verify the normal MCP still rejects TX. Do not persist the flag.
- A successful command is not proof of emission or TV response. Have a person
  observe the TV before labeling a button as working.

`ir_universal_list("tv")` lists database buttons. A universal send tries many
codes for that button, not just the captured TV's code; avoid it for this test.

## JVC session: September 22, 2026

An older JVC remote produced repeatable, distinct Power and Volume Up RAW
captures on mntm-012. The first Power window was empty; closer positioning
worked. Volume Up produced three bursts. The snippets below retain one complete
69-sample burst per button, in microseconds, copied from the receiver output.
They include the initial frame and a repeat; they are not decoded identifiers.

**Playback performed:** one Volume Up burst, 38,000 Hz **assumed**, 33% duty
cycle, 83.12 ms of captured timings. An isolated process called the gated
`flipper_cli` entrypoint with TX enabled; the command returned empty success
and the process exited with code 0. The normal MCP subsequently rejected
`ir tx`. **The user has not confirmed a volume change.** Power was not replayed.
No remote file was saved on the Flipper; these snippets preserve the selected
captures for resumption, not the entire capture transcript.

### Power

```text
8447 4193 548 1560 539 1569 540 513 541 511 543 509 546 507 547 505 539 514 540 1567 542 1565 544 1564 545 507 547 1560 539 514 540 512 542 510 544 23026 546 1563 546 1562 547 505 539 515 539 513 541 511 543 510 544 508 546 1561 548 1560 539 1569 540 512 542 1566 543 509 545 507 547 504 540
```

### Volume Up

```text
8455 4192 549 1559 540 1569 540 513 541 511 543 510 544 508 547 507 548 505 550 504 540 1569 540 1568 541 1567 542 1566 543 510 544 509 545 506 548 23028 545 1564 545 1563 546 506 548 505 539 514 540 512 542 511 543 509 545 508 546 1562 547 1560 539 1569 540 1568 541 512 542 511 543 508 546
```

Next: ask about the previous TV response or arrange one observed retry. Do
not assume it worked and do not send automatically when reopening the project.
