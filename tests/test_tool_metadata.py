"""Clients auto-approve or confirm calls from tool hints, so the hints are a contract."""

from __future__ import annotations

import asyncio

import pytest
from mcp import Client

from flipper_mcp import server

# Gated because it power-cycles the device, not because it radiates.
_GATED_CLOSED_WORLD = {"power"}


@pytest.fixture(scope="module")
def tools():
    async def list_tools():
        async with Client(server.mcp) as client:
            return (await client.list_tools()).tools

    return {tool.name: tool for tool in asyncio.run(list_tools())}


@pytest.fixture(scope="module")
def tx_gated(tools):
    # A tool is TX-gated when its own body calls require_tx; the raw CLI gates by command.
    return {
        name
        for name in tools
        if "require_tx" in getattr(server, name).__wrapped__.__code__.co_names
    }


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


def test_tx_gated_tools_are_writes_that_reach_the_outside_world(tools, tx_gated):
    assert {"ir_tx", "subghz_tx_from_file", "rfid_write", "power"} <= tx_gated
    for name in tx_gated:
        hints = tools[name].annotations
        assert hints is not None, name
        assert hints.read_only_hint is False, name
        assert hints.open_world_hint is (name not in _GATED_CLOSED_WORLD), name
