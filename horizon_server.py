"""Prefect Horizon adapter for the existing stdio MCP server.

Horizon imports this module and looks for the exported ``mcp`` object. The
upstream server expects ``TWITTER_COOKIES`` to point at a JSON file, while
Horizon is better suited to storing credentials as environment variables.

This adapter converts ``TWITTER_CT0`` and ``TWITTER_AUTH_TOKEN`` into an
ephemeral cookies file before importing ``twitter_mcp.server``. The original
stdio entrypoint remains unchanged for local clients.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def _prepare_cookies_file() -> Path | None:
    ct0 = os.environ.get("TWITTER_CT0")
    auth_token = os.environ.get("TWITTER_AUTH_TOKEN")

    # Horizon runs `fastmcp inspect` while building the image, before runtime
    # environment variables/secrets are injected. With neither value present,
    # keep the module importable so build-time inspection can enumerate the
    # MCP surface. At runtime, either TWITTER_COOKIES may already point at a
    # file or both Horizon cookie variables can materialize one below.
    if not ct0 and not auth_token:
        return None

    if not ct0 or not auth_token:
        raise RuntimeError(
            "TWITTER_CT0 and TWITTER_AUTH_TOKEN must be configured together"
        )

    fd, raw_path = tempfile.mkstemp(prefix="twitter-mcp-", suffix=".json")
    os.close(fd)
    path = Path(raw_path)
    path.write_text(
        json.dumps({"ct0": ct0, "auth_token": auth_token}),
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


_cookies_path = _prepare_cookies_file()
if _cookies_path is not None:
    os.environ["TWITTER_COOKIES"] = str(_cookies_path)

# Import only after TWITTER_COOKIES is set because twitter_mcp.server resolves
# the cookie path at module import time.
from twitter_mcp.server import mcp  # noqa: E402,F401

