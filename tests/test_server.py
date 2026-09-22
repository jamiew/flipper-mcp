from __future__ import annotations

import asyncio

from mcp import Client

from flipper_mcp import server
from flipper_mcp.server import _hex_arg


def test_hex_arg_preserves_numeric_and_saved_byte_values():
    assert int(_hex_arg("0000"), 16) == 0
    assert int(_hex_arg("0X0700"), 16) == 0x0700
    assert int(_hex_arg("EA C7 00 00"), 16) == 0xC7EA
    assert int(_hex_arg("07 00 00 00"), 16) == 7


def test_firmware_failure_is_an_mcp_error(monkeypatch):
    class UnavailableNfc:
        def stream(self, cmd, duration):
            return "failed to load external command"

    monkeypatch.setattr(server, "_get_bridge", lambda: UnavailableNfc())

    async def call():
        async with Client(server.mcp) as client:
            return await client.call_tool("nfc_detect", {"duration_s": 0})

    result = asyncio.run(call())
    assert result.is_error
    assert "failed to load external command" in result.content[0].text
