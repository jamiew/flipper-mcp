from __future__ import annotations

import asyncio
import threading

import pytest
from mcp import Client

from flipper_mcp import bridge as bridge_module
from flipper_mcp import server
from flipper_mcp.bridge import FlipperBridge
from flipper_mcp.server import _hex_arg
from tests.test_bridge import FakeSerial


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
        ("subghz_rx", {"frequency_hz": 100_000_000}),
        ("nfc_detect", {"duration_s": 3600}),
        ("flipper_cli", {"command": "free", "timeout_s": 0}),
        ("gpio_write", {"pin": "PA7", "value": 2}),
    ],
)
def test_invalid_arguments_are_mcp_errors(device_calls, name, arguments):
    assert _call(name, arguments).is_error
    assert device_calls == []


def test_interrupt_runs_while_a_capture_holds_the_device(monkeypatch):
    capturing = threading.Event()
    interrupted = threading.Event()

    class Capture:
        def stream(self, cmd, duration):
            capturing.set()
            interrupted.wait(5.0)
            return "partial capture"

        def interrupt(self):
            interrupted.set()
            return ""

    fake = Capture()
    monkeypatch.setattr(server, "_get_bridge", lambda: fake)

    async def run():
        async with Client(server.mcp) as client:
            capture = asyncio.create_task(
                client.call_tool("subghz_rx", {"frequency_hz": 433920000, "duration_s": 600})
            )
            assert await asyncio.to_thread(capturing.wait, 2.0)
            stop = await asyncio.wait_for(client.call_tool("flipper_interrupt", {}), 2.0)
            return stop, await asyncio.wait_for(capture, 2.0)

    stop, captured = asyncio.run(run())
    assert not stop.is_error
    assert captured.content[0].text == "partial capture"


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("registry_list", {}),
        ("registry_describe", {"protocol_id": "princeton"}),
        ("registry_status", {}),
        # Non-http URLs and unknown ids fail locally, so these stay offline.
        ("registry_fetch_index", {"index_url": "file:///nope.json"}),
        ("registry_install", {"index_url": "file:///nope.json", "protocol_id": "x"}),
        ("registry_remove", {"protocol_id": "not-installed"}),
    ],
)
def test_registry_tools_do_not_wait_for_the_device(tmp_path, monkeypatch, name, arguments):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    async def call():
        async with Client(server.mcp) as client:
            return await asyncio.wait_for(client.call_tool(name, arguments), 2.0)

    assert server._device_lock.acquire(timeout=1.0)
    try:
        asyncio.run(call())
    finally:
        server._device_lock.release()


def test_cancelled_call_stops_capture_and_keeps_link(monkeypatch):
    port = FakeSerial()

    def respond(payload):
        if payload == b"\x03":
            port.incoming.put(b"stopped\r\n>: ")
        else:
            port.incoming.put(payload + b"sample\r\n")

    port.on_write = respond
    monkeypatch.setattr(bridge_module.serial, "Serial", lambda *args, **kwargs: port)
    monkeypatch.setattr(FlipperBridge, "_handshake", lambda self: None)
    monkeypatch.setattr(server, "_bridge", None)
    monkeypatch.setenv("FLIPPER_PORT", "fake")

    async def run():
        # Legacy mode speaks JSON-RPC, so cancelling the call sends notifications/cancelled.
        async with Client(server.mcp, mode="legacy") as client:
            capture = client.call_tool("subghz_rx", {"frequency_hz": 433920000, "duration_s": 5})
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(capture, 0.3)
            # The client stays connected; only the call was cancelled. The worker
            # frees the device once the stream has stopped and settled.
            freed = await asyncio.to_thread(server._device_lock.acquire, True, 2.0)
            if freed:
                server._device_lock.release()
            return freed

    try:
        assert asyncio.run(run())
        assert port.writes == [b"subghz rx 433920000 0\r\n", b"\x03"]
        assert server._bridge is not None and server._bridge.alive
    finally:
        server._close_bridge()
