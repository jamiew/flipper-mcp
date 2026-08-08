from __future__ import annotations

from flipper_mcp.server import _hex_arg


def test_hex_arg_preserves_leading_zero_bytes():
    # regression: lstrip("0x") corrupted these
    assert _hex_arg("0700") == "0700"
    assert _hex_arg("00 EA C7") == "00EAC7"
    assert _hex_arg("0x0A") == "0A"
    assert _hex_arg("EA C7 00 00") == "EAC70000"
    assert _hex_arg("0X0700") == "0700"
