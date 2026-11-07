from __future__ import annotations

import asyncio

import pytest
from mcp import Client

from flipper_mcp import server
from flipper_mcp.server import _hex_arg


def _call(name: str, arguments: dict):
    async def call():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(call())


@pytest.fixture
def device_calls(monkeypatch):
    """Record any bridge use so a test can prove a tool never reached the device."""
    calls = []

    class RecordingBridge:
        def __getattr__(self, method):
            return lambda *args, **kwargs: calls.append(method) or ""

    monkeypatch.setattr(server, "_get_bridge", RecordingBridge)
    return calls


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
    result = _call("nfc_detect", {"duration_s": 0})
    assert result.is_error
    assert "failed to load external command" in result.content[0].text


@pytest.mark.parametrize(
    ("name", "arguments"),
    [("flipper_file_inspect", {"path": "/ext/nope.sub"}), ("list_installed_apps", {})],
)
def test_storage_errors_are_mcp_errors(monkeypatch, name, arguments):
    class MissingFile:
        def send(self, cmd, timeout=10.0):
            return "Storage error: file/dir not exist"

    monkeypatch.setattr(server, "_get_bridge", lambda: MissingFile())
    result = _call(name, arguments)
    assert result.is_error
    assert "file/dir not exist" in result.content[0].text


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("power", {"action": "explode"}),
        ("ir_universal_list", {"category": "toaster"}),
        ("registry_describe", {"protocol_id": "no-such-protocol"}),
    ],
)
def test_invalid_arguments_are_mcp_errors(device_calls, name, arguments):
    assert _call(name, arguments).is_error
    assert device_calls == []
