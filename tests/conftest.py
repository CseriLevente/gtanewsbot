"""
Test fixtures and safety rails.

Two protections mirror the tozsdeturbo-bot conftest:

  1. The developer's real .env is NEUTRALISED. `load_dotenv()` in src.main would
     otherwise leak a live DISCORD_BOT_TOKEN and POSTING_ENABLED=true into the
     test process, and a test that builds a payload could post to the real
     server. Every Discord credential is blanked and posting is forced off.
  2. The database is redirected to a tmp_path OUTSIDE the OneDrive-synced project
     directory. Without this, storage.connect() would (correctly) refuse to open
     a DB under OneDrive and every async test would fail on the guard.
"""
from __future__ import annotations

import asyncio
import os

import pytest

# Applied at import time, before any test module imports src.*
os.environ["DISCORD_BOT_TOKEN"] = ""
os.environ["DISCORD_NEWS_CHANNEL_ID"] = ""
os.environ["DISCORD_NEWS_ROLE_ID"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["POSTING_ENABLED"] = "false"
os.environ["DIGEST_HOUR"] = "18"


@pytest.fixture(autouse=True)
def _neutralise_env(monkeypatch):
    """Re-assert the safety env for every test, in case one mutated it."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "")
    monkeypatch.setenv("DISCORD_NEWS_CHANNEL_ID", "")
    monkeypatch.setenv("DISCORD_NEWS_ROLE_ID", "")
    monkeypatch.setenv("POSTING_ENABLED", "false")


@pytest.fixture()
def db_path(tmp_path, monkeypatch) -> str:
    """A throwaway database outside any cloud-synced folder."""
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("GTA6_DB_PATH", path)
    return path


@pytest.fixture()
def conn(db_path):
    """An initialised aiosqlite connection."""
    from src import storage

    async def _open():
        c = await storage.connect(db_path)
        await storage.init_schema(c)
        return c

    c = asyncio.run(_open())
    yield c
    asyncio.run(c.close())


@pytest.fixture()
def cfg():
    """The real config/sources.json — it is part of the product, so test against it."""
    from src import credibility

    return credibility.load_config()


def run(coro):
    """Run a coroutine in a test without depending on pytest-asyncio."""
    return asyncio.run(coro)
