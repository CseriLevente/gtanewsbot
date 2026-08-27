"""
Central path resolver.

Code paths are anchored to the project root so the bot works regardless of the
directory it is invoked from (Windows Task Scheduler's "Start in" field is easy
to get wrong, and a relative path that works in a terminal will break there).

The DATABASE is deliberately NOT under the project root. This project lives in a
OneDrive-synced folder, and OneDrive syncs `bot.db`, `bot.db-wal` and
`bot.db-shm` as three independent files. A restored `bot.db` sitting next to a
five-minutes-newer `-wal` is corrupt by definition — this is stated in SQLite's
own documentation, not folklore. There is also no supported way to exclude an
arbitrary subfolder from OneDrive sync ("Choose folders" only deselects
top-level folders), so relocating the file is the only real mitigation.
"""
from __future__ import annotations

import os

# __file__ = .../gta6-news-bot/src/paths.py
# dirname once  → .../gta6-news-bot/src/
# dirname twice → .../gta6-news-bot/          ← project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _abs(*parts: str) -> str:
    return os.path.join(PROJECT_ROOT, *parts)


CONFIG_DIR = _abs("config")
LOGS_DIR = _abs("logs")
RESEARCH_DIR = _abs("research")
SOURCES_JSON = _abs("config", "sources.json")

# Names of cloud-sync roots we refuse to host a live SQLite file under.
_SYNC_MARKERS = ("onedrive", "dropbox", "google drive", "googledrive", "icloud", "box sync")


def app_data_dir() -> str:
    """
    Return the per-user writable directory for bot state.

    %LOCALAPPDATA% is used because OneDrive's Known Folder Move covers
    Desktop/Documents/Pictures but never AppData\\Local.
    """
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        # Non-Windows or a stripped environment (CI). Fall back to the XDG-ish
        # location so tests and Linux runs still work.
        base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "gta6-news-bot")


def db_path() -> str:
    """Absolute path to the SQLite database. Override with GTA6_DB_PATH."""
    override = os.environ.get("GTA6_DB_PATH")
    if override:
        return override
    return os.path.join(app_data_dir(), "bot.db")


def is_cloud_synced(path: str) -> bool:
    """True if *path* looks like it sits inside a cloud-sync root."""
    low = os.path.abspath(path).replace("\\", "/").casefold()
    return any(f"/{m}" in low or low.startswith(m) for m in _SYNC_MARKERS)


def assert_not_synced(path: str) -> None:
    """
    Refuse to open a database inside a cloud-synced folder.

    Raises RuntimeError rather than warning, because the failure mode is silent
    corruption discovered days later. Set GTA6_ALLOW_SYNCED_DB=true to override
    (only sensible for a throwaway test DB).
    """
    if os.environ.get("GTA6_ALLOW_SYNCED_DB", "").strip().casefold() in ("1", "true", "yes"):
        return
    if is_cloud_synced(path):
        raise RuntimeError(
            f"Refusing to open a SQLite database inside a cloud-synced folder:\n"
            f"    {path}\n"
            f"OneDrive/Dropbox sync the .db, -wal and -shm files independently, which\n"
            f"corrupts the database. Use the default location instead:\n"
            f"    {db_path()}\n"
            f"or set GTA6_ALLOW_SYNCED_DB=true if you accept the risk."
        )


def ensure_dirs() -> None:
    """Create the directories the bot writes to."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(app_data_dir(), exist_ok=True)
