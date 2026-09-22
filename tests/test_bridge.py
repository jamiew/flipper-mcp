from __future__ import annotations

import queue
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from flipper_mcp import bridge as bridge_module
from flipper_mcp.bridge import FlipperBridge, FlipperError

# _clean is a pure @staticmethod, so it needs no serial port / hardware.


def test_clean_strips_echo_ansi_and_prompt():
    raw = b"device_info\r\n\x1b[0mhardware_model: Flipper\r\n>: "
    assert FlipperBridge._clean(raw, "device_info") == "hardware_model: Flipper"


def test_clean_preserves_body_without_cmd():
    raw = b"line one\r\nline two\r\n>:"
    assert FlipperBridge._clean(raw) == "line one\nline two"


def test_clean_only_strips_matching_echo():
    # first line is not the command, so it must survive
    raw = b"actual output\r\n>: "
    assert FlipperBridge._clean(raw, "storage list /ext") == "actual output"


class FakeSerial:
    def __init__(self):
        self.incoming = queue.Queue()
        self.writes = []
        self.closed = False
        self.on_write = lambda payload: None

    def read(self, size):
        try:
            return self.incoming.get(timeout=0.01)
        except queue.Empty:
            return b""

    def write(self, payload):
        if self.closed:
            raise OSError("closed")
        self.writes.append(payload)
        self.on_write(payload)
        return len(payload)

    def flush(self):
        pass

    def close(self):
        self.closed = True
        self.incoming.put(b"")


@pytest.fixture
def connected_bridge(monkeypatch):
    port = FakeSerial()
    monkeypatch.setattr(bridge_module.serial, "Serial", lambda *args, **kwargs: port)
    monkeypatch.setattr(FlipperBridge, "_handshake", lambda self: None)
    bridge = FlipperBridge(port="fake")
    try:
        yield bridge, port
    finally:
        bridge.close()


def test_send_waits_through_echo_silence_for_delayed_output(connected_bridge):
    bridge, port = connected_bridge
    delayed = threading.Timer(0.15, port.incoming.put, args=(b"complete\r\n>: ",))

    def respond(payload):
        port.incoming.put(payload)
        delayed.start()

    port.on_write = respond
    try:
        assert bridge.send("slow", timeout=1.0, quiet_ms=10) == "complete"
    finally:
        delayed.cancel()
        delayed.join()


def test_concurrent_commands_do_not_mix_responses(connected_bridge):
    bridge, port = connected_bridge
    first_written = threading.Event()
    second_started = threading.Event()

    def respond(payload):
        if payload == b"first\r\n":
            port.incoming.put(payload)
            first_written.set()
        else:
            port.incoming.put(payload + b"second result\r\n>: ")

    def second():
        second_started.set()
        return bridge.send("second", timeout=1.0, quiet_ms=10)

    port.on_write = respond
    with ThreadPoolExecutor(max_workers=2) as executor:
        first_result = executor.submit(bridge.send, "first", 1.0, 10)
        assert first_written.wait(1.0)
        second_result = executor.submit(second)
        assert second_started.wait(1.0)
        port.incoming.put(b"first result\r\n>: ")
        assert first_result.result(timeout=2.0) == "first result"
        assert second_result.result(timeout=2.0) == "second result"


def test_prompt_timeout_retires_link_and_rejects_reuse(connected_bridge):
    bridge, port = connected_bridge
    port.on_write = lambda payload: port.incoming.put(payload + b"partial\r\n")
    with pytest.raises(FlipperError):
        bridge.send("stuck", timeout=0.08, quiet_ms=10)
    assert not bridge.alive
    assert port.closed
    with pytest.raises(FlipperError):
        bridge.send("next")
    assert port.writes == [b"stuck\r\n"]


def test_busy_timeout_does_not_interrupt_active_command(connected_bridge):
    bridge, port = connected_bridge
    first_written = threading.Event()
    port.on_write = lambda payload: first_written.set()
    with ThreadPoolExecutor(max_workers=1) as executor:
        first_result = executor.submit(bridge.send, "first", 1.0, 10)
        assert first_written.wait(1.0)
        with pytest.raises(FlipperError):
            bridge.send("second", timeout=0.05, quiet_ms=10)
        assert bridge.alive
        port.incoming.put(b"first\r\ncomplete\r\n>: ")
        assert first_result.result(timeout=2.0) == "complete"
    assert port.writes == [b"first\r\n"]


def test_close_marks_dead_and_stops_reader(connected_bridge):
    bridge, port = connected_bridge
    bridge.close()
    assert not bridge.alive
    assert not bridge._reader.is_alive()
    assert port.closed
    with pytest.raises(FlipperError):
        bridge.interrupt()
    assert port.writes == []


def test_failed_stream_interrupts_device_before_closing(connected_bridge, monkeypatch):
    bridge, port = connected_bridge

    def interrupted_sleep(duration):
        raise KeyboardInterrupt

    monkeypatch.setattr(bridge_module.time, "sleep", interrupted_sleep)
    with pytest.raises(KeyboardInterrupt):
        bridge.stream("listen", duration=1.0)
    assert port.writes == [b"listen\r\n", b"\x03"]
    assert not bridge.alive


def test_stream_timeout_does_not_return_partial_success(connected_bridge):
    bridge, port = connected_bridge
    port.on_write = lambda payload: port.incoming.put(b"sample\r\n")
    with pytest.raises(FlipperError):
        bridge.stream("listen", duration=0, post_timeout=0.08, quiet_ms=10)
    assert port.writes == [b"listen\r\n", b"\x03"]
    assert not bridge.alive


def test_failed_handshake_closes_serial_and_reader(monkeypatch):
    port = FakeSerial()
    instances = []

    def failed_handshake(bridge):
        instances.append(bridge)
        raise FlipperError("no prompt")

    monkeypatch.setattr(bridge_module.serial, "Serial", lambda *args, **kwargs: port)
    monkeypatch.setattr(FlipperBridge, "_handshake", failed_handshake)
    with pytest.raises(FlipperError):
        FlipperBridge(port="fake")
    assert port.closed
    assert not instances[0].alive
    assert not instances[0]._reader.is_alive()


def test_stream_that_exits_early_does_not_send_stale_interrupt(connected_bridge):
    bridge, port = connected_bridge
    port.on_write = lambda payload: port.incoming.put(payload + b"unavailable\r\n>: ")
    assert bridge.stream("listen", duration=1.0, quiet_ms=10) == "unavailable"
    assert bridge.send("next", quiet_ms=10) == "unavailable"
    assert port.writes == [b"listen\r\n", b"next\r\n"]


@pytest.mark.parametrize("cmd", ["free\r\npower off", "free\x03power off", "free\x1b[A"])
def test_command_control_characters_rejected_before_writing(connected_bridge, cmd):
    bridge, port = connected_bridge
    with pytest.raises(FlipperError):
        bridge.send(cmd)
    with pytest.raises(FlipperError):
        bridge.stream(cmd, duration=0)
    assert port.writes == []
    assert bridge.alive


def test_file_content_cannot_escape_write_session(connected_bridge):
    bridge, port = connected_bridge
    with pytest.raises(FlipperError):
        bridge.write_file("/ext/test.txt", "text\x03power off\r\n")
    with pytest.raises(FlipperError):
        bridge.write_file("/ext/test.txt\r\npower off", "text")
    assert port.writes == []
    assert bridge.alive


def test_failed_storage_open_does_not_execute_content_as_commands(connected_bridge):
    bridge, port = connected_bridge
    port.on_write = lambda payload: port.incoming.put(payload + b"cannot open file\r\n>: ")
    with pytest.raises(FlipperError):
        bridge.write_file("/ext/test.txt", "power off\r\n")
    assert not any(b"power off" in payload for payload in port.writes)
    assert not bridge.alive


def test_stream_collects_output_until_interrupt_prompt(connected_bridge):
    bridge, port = connected_bridge

    def respond(payload):
        if payload == b"\x03":
            port.incoming.put(b"stopped\r\n>: ")
        else:
            port.incoming.put(payload + b"sample\r\n")

    port.on_write = respond
    assert bridge.stream("listen", duration=0.05, quiet_ms=10) == "sample\nstopped"
    assert bridge.alive


@pytest.mark.parametrize("content", ["first\r\n\tsecond", "first\nsecond\n"])
def test_write_file_preserves_exact_text_and_terminates(connected_bridge, content):
    bridge, port = connected_bridge
    file_data = bytearray()
    writing = False
    command = bytearray()

    def respond(payload):
        nonlocal writing
        for byte in payload:
            if writing:
                if byte == 3:
                    writing = False
                    port.incoming.put(b"saved\r\n>: ")
                else:
                    file_data.append(byte)
            elif byte == 13:
                writing = True
            else:
                command.append(byte)

    port.on_write = respond
    assert bridge.write_file("/ext/test.txt", content) == "saved"
    assert file_data == content.encode()
    assert not writing
