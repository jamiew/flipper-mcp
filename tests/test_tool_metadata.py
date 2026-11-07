"""Clients auto-approve or confirm calls from tool hints, so the hints are a contract."""

from __future__ import annotations

import asyncio

import pytest
from mcp import Client

from flipper_mcp import server

# Every tool that transmits, emulates, writes tags or power-cycles, with valid arguments.
TX_CALLS = {
    "subghz_tx_from_file": {"sub_file_path": "/ext/subghz/garage.sub"},
    "subghz_chat": {"frequency_hz": 433920000, "duration_s": 0},
    "nfc_emulate": {"file_path": "/ext/nfc/card.nfc", "duration_s": 0},
    "ir_tx": {"protocol": "NEC", "address": "04", "command": "15"},
    "ir_universal_send": {"category": "tv", "button": "Power"},
    "rfid_write": {"key_type": "EM4100", "key_data": "0102030405"},
    "rfid_emulate": {"key_type": "EM4100", "key_data": "0102030405", "duration_s": 0},
    "ibutton_write": {"key_data": "0102030405060708"},
    "ibutton_emulate": {"key_type": "Dallas", "key_data": "0102030405060708", "duration_s": 0},
    "power": {"action": "otg_on"},
}
# Gated because it power-cycles the device, not because it radiates.
_GATED_CLOSED_WORLD = {"power"}
# Writes that reach the network, not the radio.
_NETWORK_WRITES = {"registry_install"}


@pytest.fixture(scope="module")
def tools():
    async def list_tools():
        async with Client(server.mcp) as client:
            return (await client.list_tools()).tools

    return {tool.name: tool for tool in asyncio.run(list_tools())}


def test_raw_cli_keeps_the_worst_case_defaults(tools):
    assert tools["flipper_cli"].annotations is None


def test_every_tool_declares_read_only(tools):
    unlabeled = [
        name
        for name, tool in tools.items()
        if name != "flipper_cli"
        and (tool.annotations is None or tool.annotations.read_only_hint is None)
    ]
    assert unlabeled == []


def test_writes_declare_destructive(tools):
    missing = [
        name
        for name, tool in tools.items()
        if tool.annotations is not None
        and not tool.annotations.read_only_hint
        and tool.annotations.destructive_hint is None
    ]
    assert missing == []


def test_tx_tools_are_writes_that_reach_the_outside_world(tools):
    # A transmit tool labeled read-only or closed-world drops out of this set and fails.
    outside_writes = {
        name
        for name, tool in tools.items()
        if tool.annotations is not None
        and tool.annotations.read_only_hint is False
        and tool.annotations.open_world_hint is True
    }
    assert outside_writes - _NETWORK_WRITES == set(TX_CALLS) - _GATED_CLOSED_WORLD
    for name in _GATED_CLOSED_WORLD:
        hints = tools[name].annotations
        assert hints is not None
        assert hints.read_only_hint is False
        assert hints.open_world_hint is False


@pytest.mark.parametrize(("name", "arguments"), TX_CALLS.items(), ids=list(TX_CALLS))
def test_tx_tools_refuse_without_enable_and_send_nothing(monkeypatch, name, arguments):
    sent = []

    class RecordingBridge:
        def __getattr__(self, method):
            return lambda *args, **kwargs: sent.append((method, args)) or ""

    monkeypatch.delenv("FLIPPER_ENABLE_TX", raising=False)
    monkeypatch.setattr(server, "_get_bridge", RecordingBridge)

    async def call():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    result = asyncio.run(call())
    assert result.is_error
    assert "FLIPPER_ENABLE_TX" in result.content[0].text
    assert sent == []
