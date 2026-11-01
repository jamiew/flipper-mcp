"""Transmit / destructive-command gating.

Off by default. RF/IR transmit, device emulation, and destructive commands
raise unless ``FLIPPER_ENABLE_TX`` is set. The env var is read fresh on every
call so it can be toggled without restarting the server. Transmitting outside
legal frequencies or your region is the operator's responsibility.
"""

from __future__ import annotations

import os

from .bridge import FlipperError

# Sub-GHz hardware tuning windows (Hz), not legal ISM allocations or TX authorization.
TX_BANDS = (
    (300_000_000, 348_000_000),
    (387_000_000, 464_000_000),
    (779_000_000, 928_000_000),
)

# Raw CLI prefixes that transmit or destroy. Kept lowercase, space-normalized.
_GATED_PREFIXES = (
    "subghz tx",
    "ir tx",
    "subghz chat",
    "rfid write",
    "rfid emulate",
    "rfid raw_emulate",
    "bt tx",
    "ikey write",
    "ikey emulate",
    "nfc emulate",
    "power off",
    "power reboot",
    "power 5v",
    "power 3v3",
    "storage format",
    "factory_reset",
    "update install",
    "update restore",
)

# Whole commands gated regardless of arguments. `js` runs a script that can transmit.
_GATED_COMMANDS = ("js",)

_TRUTHY = {"1", "true", "yes", "on"}
_CHAIN_CHARS = (";", "&&", "||", "|", "`")


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
    """Refuse frequencies outside the hardware windows; this is not a legal-use check."""
    if not any(lo <= hz <= hi for lo, hi in TX_BANDS):
        raise FlipperError(
            f"{hz} Hz is outside the hardware TX windows {TX_BANDS}; refusing to transmit."
        )


def gate_raw_command(command: str) -> None:
    """Gate the raw-CLI escape hatch so it can't bypass the transmit checks."""
    # Serial CLI input interprets CR, tab, backspace and escapes before dispatch.
    # Reject them rather than normalizing a different command than the device sees.
    if not command.isprintable():
        raise FlipperError("Refusing CLI control characters; send one printable command per call.")
    if any(c in command for c in _CHAIN_CHARS):
        raise FlipperError("Refusing a chained/piped CLI command; send one command per call.")
    norm = " ".join(command.strip().lower().split())
    words = command.split()
    if words and words[0].lower() in _GATED_COMMANDS:
        require_tx(words[0].lower())
        return
    if (
        len(words) >= 3
        and words[0].lower() == "ir"
        and words[1].lower().startswith("universal")
        and words[2] != "list"
    ):
        # Firmware accepts `ir universal <remote> <signal>` and prefix-matches
        # "universal"; only the exact, case-sensitive "list" argument is read-only.
        require_tx("ir universal")
        return
    for prefix in _GATED_PREFIXES:
        if norm.startswith(prefix):
            require_tx(prefix)
            return
