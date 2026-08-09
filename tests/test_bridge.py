from __future__ import annotations

from flipper_mcp.bridge import FlipperBridge

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
