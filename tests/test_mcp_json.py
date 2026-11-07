"""Launch every server in the tracked .mcp.json over stdio, as an agent would."""

from __future__ import annotations

import asyncio
import json
import os
from importlib.metadata import version
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parent.parent
SERVERS = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]
# The raw CLI escape hatch is gated per command, so it carries no static hints.
UNANNOTATED = {"flipper_cli"}


def _params(entry: dict) -> StdioServerParameters:
    def expand(arg: str) -> str:
        return arg.replace("${CLAUDE_PROJECT_DIR:-.}", str(ROOT))

    return StdioServerParameters(
        command=expand(entry["command"]),
        args=[expand(a) for a in entry.get("args", [])],
        env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "")},
        cwd="/",
    )


# "auto" probes server/discover, so the modern era reports serverInfo too.
@pytest.mark.parametrize(("mode", "era"), [("legacy", "2025-11-25"), ("auto", "2026-07-28")])
@pytest.mark.parametrize("name", sorted(SERVERS))
def test_mcp_json_server_starts(name, mode, era):
    async def run():
        async with Client(_params(SERVERS[name]), mode=mode) as client:
            assert client.protocol_version == era
            assert client.server_info is not None
            assert client.server_info.version == version("flipper-mcp")
            tools = (await client.list_tools()).tools
            await client.list_prompts()
            await client.list_resources()
            result = await client.call_tool("registry_status", {})
            return tools, result

    tools, result = asyncio.run(run())
    assert not result.is_error
    for tool in tools:
        if tool.name in UNANNOTATED:
            continue
        hints = tool.annotations
        assert hints is not None and hints.read_only_hint is not None, tool.name
        if not hints.read_only_hint:
            assert hints.destructive_hint is not None, tool.name
