"""Tests for the Prefect Horizon adapter."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest
from fastmcp.utilities.mcp_server_config.v1.sources.filesystem import FileSystemSource
from mcp.server.mcpserver import MCPServer


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "horizon_server.py"


def _load_adapter(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ADAPTER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(module_name, None)


def test_horizon_adapter_requires_cookie_env(monkeypatch):
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_COOKIES", raising=False)

    with pytest.raises(RuntimeError, match="TWITTER_CT0"):
        _load_adapter("_twitter_mcp_horizon_missing_env")


def test_horizon_adapter_materializes_cookie_file(monkeypatch):
    monkeypatch.setenv("TWITTER_CT0", "test-ct0")
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "test-auth-token")
    monkeypatch.delenv("TWITTER_COOKIES", raising=False)
    fake_server = types.ModuleType("twitter_mcp.server")
    fake_server.mcp = object()
    monkeypatch.setitem(sys.modules, "twitter_mcp.server", fake_server)

    module = _load_adapter("_twitter_mcp_horizon_env")

    cookie_path = Path(os.environ["TWITTER_COOKIES"])
    try:
        assert cookie_path.exists()
        assert cookie_path.stat().st_mode & 0o777 == 0o600
        assert json.loads(cookie_path.read_text(encoding="utf-8")) == {
            "ct0": "test-ct0",
            "auth_token": "test-auth-token",
        }
        assert module.mcp is not None
    finally:
        cookie_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_fastmcp_loader_accepts_horizon_entrypoint(monkeypatch):
    """Exercise the same file.py:mcp loading seam used by Horizon/FastMCP."""
    monkeypatch.setenv("TWITTER_CT0", "test-ct0")
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "test-auth-token")
    monkeypatch.delenv("TWITTER_COOKIES", raising=False)

    source = FileSystemSource(path=f"{ADAPTER}:mcp")
    server = await source.load_server()

    cookie_path = Path(os.environ["TWITTER_COOKIES"])
    try:
        assert isinstance(server, MCPServer)
        assert server.name == "twitter"
    finally:
        cookie_path.unlink(missing_ok=True)

