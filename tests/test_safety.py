from __future__ import annotations

import pytest

from flipper_mcp.bridge import FlipperError
from flipper_mcp.safety import (
    check_tx_frequency,
    gate_raw_command,
    require_tx,
)


def test_require_tx_blocks_when_disabled(monkeypatch):
    monkeypatch.delenv("FLIPPER_ENABLE_TX", raising=False)
    with pytest.raises(FlipperError):
        require_tx("ir tx")


def test_require_tx_allows_when_enabled(monkeypatch):
    monkeypatch.setenv("FLIPPER_ENABLE_TX", "1")
    require_tx("ir tx")  # no raise


def test_check_tx_frequency(monkeypatch):
    check_tx_frequency(433_920_000)  # in band, no raise
    with pytest.raises(FlipperError):
        check_tx_frequency(121_500_000)  # aviation emergency, refused


@pytest.mark.parametrize(
    "command",
    [
        "subghz tx_from_file /ext/x.sub",
        "subghz tx_carrier 433920000",
        "  SubGHz   chat 433920000 0  ",
        "ir universal tv Power",
        "ir universal send tv Power",
        "ir universal_extra tv Power",
        "ir universal LIST Power",
        "rfid raw_emulate /ext/lfrfid/raw.ask.raw",
        "bt tx_carrier 0 0",
        "bt tx_packet 0 0 0",
        "js /ext/apps/Scripts/transmit.js",
        "power off",
        "power reboot2dfu",
        "power 5v 1",
        "power 3v3 0",
        "storage format /ext",
        "factory_reset",
        "update install /ext/update/update.fuf",
        "update restore /ext/backup.tar",
    ],
)
def test_gate_raw_command_gates_tx_and_destructive_commands(monkeypatch, command):
    monkeypatch.delenv("FLIPPER_ENABLE_TX", raising=False)
    with pytest.raises(FlipperError):
        gate_raw_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "help\rpower off",
        "help\npower off",
        "help\x03power off",
        "power on\bff",
        "power o\x00ff",
        "power o\x7fff",
        "power \x1b[A",
        "subghz\tchat 433920000 0",
        "subghz\vchat 433920000 0",
        "ir universal\u0085tv Power",
        "ir universal\u2028tv Power",
        "storage list /ext; power off",
        "help && power off",
        "help || power off",
        "help | power off",
        "help `power off`",
    ],
)
def test_gate_raw_command_rejects_serial_controls_and_chaining(monkeypatch, command):
    monkeypatch.delenv("FLIPPER_ENABLE_TX", raising=False)
    with pytest.raises(FlipperError):
        gate_raw_command(command)


def test_gate_raw_command_preserves_read_only_commands(monkeypatch):
    monkeypatch.delenv("FLIPPER_ENABLE_TX", raising=False)
    for command in (
        "help",
        "storage list /ext",
        "ir",
        "ir universal",
        "ir universal list tv",
        "subghz",
        "subghz rx 433920000 0",
        "power",
        "power info",
        "update",
        "update help",
        "update backup /ext/backup.tar",
        "rfid raw_read ask /ext/lfrfid/raw",
        "bt hci_info",
        "jsonsomething",
    ):
        gate_raw_command(command)
