"""Validates that every registered slash command meets Discord's API character limits."""

from types import SimpleNamespace

import discord
import pytest
from discord import app_commands

from commands import load_commands

# Build the command tree once at collection time using a minimal real client
# (MagicMock doesn't work here — CommandTree inspects client internals on init)
_GUILD_ID = 999999999999999999
_client = discord.Client(intents=discord.Intents.none())
_tree = app_commands.CommandTree(_client)
load_commands.load_commands(_client, _tree, SimpleNamespace(id=_GUILD_ID))

_ALL_COMMANDS = _tree.get_commands(guild=discord.Object(id=_GUILD_ID))
_ALL_PARAMS = [
    (cmd, param)
    for cmd in _ALL_COMMANDS
    if isinstance(cmd, app_commands.Command)
    for param in cmd._params.values()
]


# ── command-level constraints ─────────────────────────────────────────────────


@pytest.mark.parametrize("cmd", _ALL_COMMANDS, ids=[c.name for c in _ALL_COMMANDS])
def test_command_name_at_most_32_chars(cmd):
    assert len(cmd.name) <= 32, f"/{cmd.name}: name is {len(cmd.name)} chars (max 32)"


@pytest.mark.parametrize("cmd", _ALL_COMMANDS, ids=[c.name for c in _ALL_COMMANDS])
def test_command_has_description(cmd):
    desc = str(cmd.description).strip()
    assert desc and desc != "…", f"/{cmd.name}: missing description"


@pytest.mark.parametrize("cmd", _ALL_COMMANDS, ids=[c.name for c in _ALL_COMMANDS])
def test_command_description_at_most_100_chars(cmd):
    desc = str(cmd.description)
    assert len(desc) <= 100, f"/{cmd.name}: description is {len(desc)} chars (max 100)"


# ── parameter-level constraints ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "cmd,param",
    _ALL_PARAMS,
    ids=[f"{c.name}.{p.name}" for c, p in _ALL_PARAMS],
)
def test_param_name_at_most_32_chars(cmd, param):
    assert len(param.name) <= 32, (
        f"/{cmd.name}.{param.name}: param name is {len(param.name)} chars (max 32)"
    )


@pytest.mark.parametrize(
    "cmd,param",
    _ALL_PARAMS,
    ids=[f"{c.name}.{p.name}" for c, p in _ALL_PARAMS],
)
def test_param_has_description(cmd, param):
    desc = str(param.description).strip()
    assert desc and desc != "…", f"/{cmd.name}.{param.name}: missing description"


@pytest.mark.parametrize(
    "cmd,param",
    _ALL_PARAMS,
    ids=[f"{c.name}.{p.name}" for c, p in _ALL_PARAMS],
)
def test_param_description_at_most_100_chars(cmd, param):
    desc = str(param.description)
    assert len(desc) <= 100, (
        f"/{cmd.name}.{param.name}: param description is {len(desc)} chars (max 100)"
    )
