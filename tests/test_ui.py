"""Tests for the UI automation helpers in ``flipper_mcp.ui``.

All tests run offline — we never open a real serial port. A minimal fake
bridge records every command that would have been sent so we can assert on
the generated CLI traffic.
"""

from __future__ import annotations

import time

import pytest

from flipper_mcp import ui


class FakeBridge:
    """Records every ``send`` call instead of opening a serial port."""

    def __init__(self, reply: str = "") -> None:
        self.calls: list[str] = []
        self._reply = reply

    def send(self, cmd: str, timeout: float = 10.0, quiet_ms: int = 300) -> str:
        self.calls.append(cmd)
        return self._reply


# -- normalize_key ---------------------------------------------------------


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("up", "up"),
        ("down", "down"),
        ("left", "left"),
        ("right", "right"),
        ("ok", "ok"),
        ("back", "back"),
        ("u", "up"),
        ("d", "down"),
        ("l", "left"),
        ("r", "right"),
        ("center", "ok"),
        ("enter", "ok"),
        ("return", "ok"),
        ("b", "back"),
        ("esc", "back"),
        ("escape", "back"),
        ("  UP  ", "up"),
        ("Ok", "ok"),
    ],
)
def test_normalize_key_accepts_aliases(alias, expected):
    assert ui.normalize_key(alias) == expected


def test_normalize_key_rejects_unknown():
    with pytest.raises(ui.UIError):
        ui.normalize_key("power")


# -- press_key -------------------------------------------------------------


def test_press_key_default_type():
    b = FakeBridge()
    ui.press_key(b, "ok")
    assert b.calls == ["input send ok short"]


def test_press_key_long():
    b = FakeBridge()
    ui.press_key(b, "down", press_type="long")
    assert b.calls == ["input send down long"]


def test_press_key_rejects_bad_type():
    b = FakeBridge()
    with pytest.raises(ui.UIError):
        ui.press_key(b, "ok", press_type="smash")


def test_press_key_normalizes_alias():
    b = FakeBridge()
    ui.press_key(b, "enter")
    assert b.calls == ["input send ok short"]


# -- hold_key --------------------------------------------------------------


def test_hold_key_emits_press_and_release(monkeypatch):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    b = FakeBridge()
    ui.hold_key(b, "ok", duration_s=0.5)
    assert b.calls == ["input send ok press", "input send ok release"]
    assert slept == [0.5]


def test_hold_key_clamps_negative_duration(monkeypatch):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    b = FakeBridge()
    ui.hold_key(b, "ok", duration_s=-1.0)
    assert slept == [0.0]


# -- parse_sequence --------------------------------------------------------


def test_parse_sequence_simple_keys():
    parsed = ui.parse_sequence("ok,down,down")
    assert parsed == [
        ("key", ("ok", "short")),
        ("key", ("down", "short")),
        ("key", ("down", "short")),
    ]


def test_parse_sequence_with_types_and_wait():
    parsed = ui.parse_sequence("long:ok,wait:0.3,back")
    assert parsed == [
        ("key", ("ok", "long")),
        ("wait", 0.3),
        ("key", ("back", "short")),
    ]


def test_parse_sequence_skips_empty_tokens():
    parsed = ui.parse_sequence("ok, , down,")
    assert parsed == [
        ("key", ("ok", "short")),
        ("key", ("down", "short")),
    ]


def test_parse_sequence_rejects_unknown_prefix():
    with pytest.raises(ui.UIError):
        ui.parse_sequence("bounce:ok")


def test_parse_sequence_rejects_bad_wait():
    with pytest.raises(ui.UIError):
        ui.parse_sequence("wait:fast")


# -- run_sequence ----------------------------------------------------------


def test_run_sequence_drives_bridge(monkeypatch):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    b = FakeBridge(reply="")
    out = ui.run_sequence(b, "ok,wait:0.2,long:down", step_delay_s=0.01)
    assert b.calls == [
        "input send ok short",
        "input send down long",
    ]
    # wait:0.2 + two step_delay_s=0.01
    assert slept == [0.01, 0.2, 0.01]
    assert "waited 0.2s" in out


# -- workflow macros -------------------------------------------------------


def test_workflow_refuses_to_navigate_an_existing_app():
    bridge = FakeBridge('Application "NFC" is running')
    with pytest.raises(ui.UIError):
        ui.infrared_learn_start_ui(bridge)
    assert not any(cmd.startswith(("loader open", "input send")) for cmd in bridge.calls)


def test_close_waits_for_observed_app_exit(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    replies = iter(
        [
            'Application "NFC" is running',
            'Application "NFC" was closed',
            'Application "NFC" is running',
            "No application is running",
        ]
    )
    bridge = FakeBridge()
    bridge.send = lambda *args, **kwargs: next(replies)
    assert ui.close_any_running_app(bridge)["after"] == "No application is running"


def test_close_reports_app_that_does_not_exit(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    ticks = iter([0.0, 4.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    bridge = FakeBridge('Application "NFC" is running')
    with pytest.raises(ui.UIError):
        ui.close_any_running_app(bridge)
