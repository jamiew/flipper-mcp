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


def test_gate_raw_command_gates_tx(monkeypatch):
    monkeypatch.delenv("FLIPPER_ENABLE_TX", raising=False)
    gate_raw_command("storage list /ext")  # benign, no raise
    with pytest.raises(FlipperError):
        gate_raw_command("subghz tx_from_file /ext/x.sub")  # gated
    with pytest.raises(FlipperError):
        gate_raw_command("storage list /ext; power off")  # chaining refused
