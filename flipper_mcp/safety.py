"""Transmit / destructive-command gating.

Off by default. RF/IR transmit, device emulation, and destructive commands
raise unless ``FLIPPER_ENABLE_TX`` is set. The env var is read fresh on every
call so it can be toggled without restarting the server. Transmitting outside
legal frequencies or your region is the operator's responsibility.
"""

from __future__ import annotations

import os

from .bridge import FlipperError

# Wide ISM windows (Hz). Narrow these to your region for a tighter guard.
TX_BANDS = (
    (300_000_000, 348_000_000),
    (387_000_000, 464_000_000),
    (779_000_000, 928_000_000),
)

# Raw CLI prefixes that transmit or destroy. Kept lowercase, space-normalized.
_GATED_PREFIXES = (
    "subghz tx",
    "ir tx",
    "rfid write",
    "rfid emulate",
    "ikey write",
    "ikey emulate",
    "nfc emulate",
    "power off",
    "power reboot",
    "storage format",
    "factory_reset",
    "update install",
)

_TRUTHY = {"1", "true", "yes", "on"}
_CHAIN_CHARS = (";", "&&", "||", "|", "`", "\n")


def tx_enabled() -> bool:
    return os.environ.get("FLIPPER_ENABLE_TX", "").strip().lower() in _TRUTHY


def require_tx(action: str) -> None:
    """Raise unless transmit tools are enabled. ``action`` names the operation."""
    if not tx_enabled():
        raise FlipperError(
            f"{action} is gated: set FLIPPER_ENABLE_TX=1 to allow transmitting or "
            "destructive commands. You are responsible for legal, authorized use."
        )


def check_tx_frequency(hz: int) -> None:
    """Refuse a transmit frequency outside the allowed bands, before sending."""
    if not any(lo <= hz <= hi for lo, hi in TX_BANDS):
        raise FlipperError(
            f"{hz} Hz is outside the allowed TX bands {TX_BANDS}; refusing to transmit."
        )


def gate_raw_command(command: str) -> None:
    """Gate the raw-CLI escape hatch so it can't bypass the transmit checks."""
    if any(c in command for c in _CHAIN_CHARS):
        raise FlipperError("Refusing a chained/piped CLI command; send one command per call.")
    norm = " ".join(command.strip().lower().split())
    for prefix in _GATED_PREFIXES:
        if norm.startswith(prefix):
            require_tx(prefix)
            return
