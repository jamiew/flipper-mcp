# flipper-mcp

A local MCP server for controlling a Flipper Zero over USB-CDC. Forked from
[Str1ck9/flipper-mcp](https://github.com/Str1ck9/flipper-mcp), using the official
MCP Python SDK v2, serialized USB transactions, and guarded transmission.

**Resume work:** [PLAN.md](PLAN.md). **Evidence:** [hardware validation](docs/hardware-validation.md).

## Current status

Checked September 22, 2026, on **Momentum mntm-012**:

- 64 tools, one triage prompt, and 13 bundled protocol definitions.
- 132 automated tests and Ruff passed. Re-invoked 63 tools after the firmware
  update, including safety refusals, not 63 successful physical tests.
- Storage, device controls, IR/LF-RFID/iButton/SubGHz reception, and registry
  operations respond. Installed apps: 195.
- JVC Power and Volume Up were captured as RAW IR. One Volume Up replay was
  accepted by firmware; **the TV's response is unconfirmed**.
- NFC CLI detection times out. App closure may require Back. The clock setter
  remains untested on this firmware after an earlier USB disconnect.
- No general Bluetooth scanner or firmware-flashing tool is exposed.

## Setup

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and a USB data cable.

```bash
git clone https://github.com/jamiew/flipper-mcp.git
cd flipper-mcp
uv sync --locked --extra dev
```

The project `.mcp.json` runs the editable checkout in Oh My Pi or compatible
MCP clients. Approve it in your client if prompted, and restart the server
when dependencies or code change:

```json
{
  "mcpServers": {
    "flipper": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--no-sync", "flipper-mcp"]
    }
  }
}
```

Run the client from this checkout. For a desktop client launched elsewhere,
use the absolute path to `.venv/bin/flipper-mcp` as its stdio command.
Only one process should own the Flipper's serial port. Close qFlipper or
Flipper Lab before connecting. For a standalone hardware check, with the MCP
server disconnected:

```bash
uv run --no-sync flipper-smoke
```

## Safety and limits

Transmission, emulation, credential writes, and destructive commands are
**disabled by default**, including equivalent raw CLI commands. They require
`FLIPPER_ENABLE_TX=1` in the server process. Enable it only for a specific,
authorized operation, then end that process. Do not add it permanently to
`.mcp.json` or enable it merely to run a sweep.

SubGHz frequency checks enforce hardware windows, not legal permission.
Storage writes, GPIO changes, and app navigation still need operator care.
Reader modes may energize LF-RFID/NFC tags. A capture is not proof of a working
copy, and rolling codes should not be treated as replayable static commands.

## Tools

Use your MCP client's tool list for exact arguments. The
[coverage table](docs/hardware-validation.md#tool-coverage) names every tool
and distinguishes data, command acceptance, receiver checks, and failures.

| Area | Main operations |
|---|---|
| Device | Firmware, help, tasks, memory, battery, clock, raw CLI |
| Storage | List, read/write text, stat, checksum, rename, remove, inspect captures |
| SubGHz | Decoded/RAW reception, offline RAW decoding, registry identification; gated replay/chat |
| Infrared | Capture/identify, decoded transmission, universal database; gated RAW CLI replay |
| RFID/NFC/iButton | Receive/read where firmware supports it; gated writes/emulation |
| UI | Launch apps, inspect running app, button input, capture workflows |
| GPIO | Pin mode/read/write and I2C scan |
| Registry | Browse, describe, fetch, install, remove, validate |

UI workflows send navigation inputs; they cannot verify the selected screen.
Check `loader_info` and the physical display. Bluetooth `bt hci_info` returns
controller metadata, not nearby devices.

For an external CC1101, pass `device=1` to supported SubGHz receive tools or
set `FLIPPER_DEFAULT_DEVICE=1`. RAW reception uses the internal radio.

## Protocol registry

Definitions in [flipper_mcp/protocols](flipper_mcp/protocols) match decoded
text and classify saved files. They do not add firmware radio decoders.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the schema and capture requirements.

```bash
uv run --no-sync flipper-registry status
uv run --no-sync flipper-registry list --pack garage
uv run --no-sync flipper-registry describe princeton
uv run --no-sync flipper-registry validate path/to/protocol.json
```

Remote indexes contain `schema_version: 1`, a `name`, and a `protocols` list
with each entry's `id`, `name`, `category`, `url`, `version`, and optional
`sha256`/`packs`. A supplied SHA-256 is checked, but is not publisher
authentication. Cached entries override bundled entries with the same ID
under `$XDG_DATA_HOME/flipper-mcp/protocols` or
`~/.local/share/flipper-mcp/protocols`.

## Troubleshooting

- **Port busy:** close the other USB client; do not run two MCP processes.
- **No device:** check the data cable, unlock the device, and run
  `uv run --no-sync python -m serial.tools.list_ports`.
- **No decoded signal:** try a nearby known transmitter during the capture
  window. RAW pulses alone do not identify a protocol.
- **Plugin load failure:** check firmware/SD asset compatibility. An app
  working on-device does not prove its CLI command exists.
- **App stays open:** use Back or long Back, then check `loader_info`.
- **NFC timeout or wrong clock:** see the current limitations in
  [PLAN.md](PLAN.md); do not repeatedly retry disruptive operations.

## Development and reference

```bash
uv sync --locked --extra dev
uv run --no-sync ruff check flipper_mcp tests
uv run --no-sync pytest
```

- [IR capture and playback](docs/ir-tv-probing.md)
- [Transport and SDK notes](docs/dev-notes.md)
- [Changelog](CHANGELOG.md)
- Historical research: [landscape](docs/landscape.md),
  [feature ideas](docs/feature-ideas.md), [opportunities](docs/opportunities.md)

Thanks to the upstream project and the USB/UI/IR work documented in the
[landscape comparison](docs/landscape.md). MIT; see [LICENSE](LICENSE).
