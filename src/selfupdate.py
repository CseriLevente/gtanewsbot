"""
Keep a deployed copy in step with the GitHub repo.

An install is a `git clone`, so upstream fixes reach every deployment without
anyone logging into a server. Each run fast-forwards to origin/main before doing
any work; the new code takes effect on the NEXT cycle, which on a 15-minute
schedule means at most a quarter-hour behind.

Why not re-exec into the new code immediately: a bot that restarts itself the
moment it pulls can loop if the new commit fails at import, and it would do so
unattended on a machine nobody is watching. Waiting one cycle costs nothing and
cannot spin.

WHAT IT REFUSES TO DO
---------------------
Every guard here exists to make the update a no-op rather than a surprise:

  * not a git checkout (a zip download, or a copied folder) -- skip silently;
  * the working tree has local modifications -- skip. That is a developer's
    machine, and clobbering their edits to ship a news bot is indefensible;
  * the branch has diverged from upstream -- skip. `--ff-only` is the whole
    policy: this can only ever move forward along the published history, never
    merge, never rebase, never discard a commit;
  * a different remote than the one configured -- skip.

`.env` is gitignored and the database lives outside the repo, so neither is ever
touched by a pull.

THE TRUST MODEL, STATED PLAINLY
-------------------------------
Auto-update means every deployment executes whatever is on origin/main. That is
the normal bargain for self-hosted software, and it is the point of the feature
-- but it does mean the repo owner's GitHub account is now a production
credential for every install. Protect it accordingly, and set AUTO_UPDATE=false
on any deployment that should not follow head.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time

from src import paths

logger = logging.getLogger(__name__)

STAMP_NAME = "last_update_check"


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_bool(name: str, default: bool) -> bool:
    v = _env(name).casefold()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name) or default)
    except ValueError:
        return default


def _git(*args: str, timeout: int = 60) -> tuple[int, str]:
    env = dict(os.environ)
    # No prompting, ever. Under a scheduler there is no console, so a
    # credential prompt is an invisible hang rather than a visible question.
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        r = subprocess.run(
            ("git",) + args, cwd=paths.PROJECT_ROOT, capture_output=True,
            text=True, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        return 124, f"git {' '.join(args)} timed out after {timeout}s"
    except FileNotFoundError:
        return 127, "git is not installed"
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def _stamp_path() -> str:
    """
    Per-INSTALL, not per-machine.

    The stamp lived at a single fixed name under the shared state directory,
    which meant two checkouts on one machine silenced each other's update
    checks: whichever ran first wrote the stamp, and the second saw a fresh
    timestamp and skipped for an hour. Caught by actually cloning the repo
    alongside the working copy and watching the clone refuse to update.

    Keying on the checkout path keeps the state out of the repo (so it can never
    dirty the working tree) while making installs independent.
    """
    import hashlib
    key = hashlib.blake2b(
        os.path.abspath(paths.PROJECT_ROOT).casefold().encode("utf-8"),
        digest_size=6,
    ).hexdigest()
    return os.path.join(paths.app_data_dir(), f"{STAMP_NAME}-{key}")


def _due(interval_s: int) -> bool:
    """
    Rate-limit the upstream check.

    If the stamp cannot be read or written we check anyway: the failure mode of
    checking too often is a few extra cheap fetches, and this project already
    has one host where scheduled writes do not persist. Degrading to "check
    every run" is the safe direction.
    """
    if interval_s <= 0:
        return True
    try:
        age = time.time() - os.path.getmtime(_stamp_path())
    except OSError:
        return True
    return age >= interval_s


def _touch_stamp() -> None:
    try:
        os.makedirs(paths.app_data_dir(), exist_ok=True)
        with open(_stamp_path(), "w", encoding="utf-8") as fh:
            fh.write(str(int(time.time())))
    except OSError as exc:
        logger.debug("could not write the update stamp: %s", exc)


def current_revision() -> str:
    """Short commit of the running code, or "" if this is not a checkout."""
    code, out = _git("rev-parse", "--short", "HEAD")
    return out if code == 0 else ""


def _requirements_changed(old: str, new: str) -> bool:
    code, out = _git("diff", "--name-only", old, new)
    if code != 0:
        # Unknown, so assume yes: a needless pip install is cheap, a missing
        # dependency stops the bot.
        return True
    return any(line.strip() == "requirements.txt" for line in out.splitlines())


def _install_requirements() -> tuple[bool, str]:
    import sys
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            cwd=paths.PROJECT_ROOT, capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "pip install timed out after 600s"
    if r.returncode != 0:
        return False, ((r.stderr or r.stdout) or "").strip()[-300:]
    return True, "dependencies updated"


def check_and_update() -> tuple[bool, str]:
    """
    Fast-forward the checkout to upstream if it is behind.

    Returns (updated, detail). Never raises: an update problem must not stop the
    bot from doing the job it is already able to do with the code it has.
    """
    if not _env_bool("AUTO_UPDATE", True):
        return False, ""

    if not os.path.isdir(os.path.join(paths.PROJECT_ROOT, ".git")):
        return False, ""          # installed from a zip; nothing to track

    interval = _env_int("AUTO_UPDATE_INTERVAL_S", 3600)
    if not _due(interval):
        return False, ""

    remote = _env("AUTO_UPDATE_REMOTE", "origin")
    branch = _env("AUTO_UPDATE_BRANCH", "main")

    # Must be ON the tracked branch. Verified experimentally: `git merge
    # --ff-only origin/main` from a DETACHED HEAD happily fast-forwards it, so
    # without this an operator who pinned a deployment to a known-good commit
    # while main was broken would be dragged back onto the broken commit on the
    # next run -- the exact opposite of what pinning is for. The same applies to
    # sitting on a feature branch and being fast-forwarded onto main's content.
    code, current = _git("symbolic-ref", "--quiet", "--short", "HEAD")
    if code != 0 or not current:
        return False, "skipped: detached HEAD (pinned to a specific commit)"
    if current != branch:
        return False, f"skipped: on branch {current}, not {branch}"

    code, out = _git("status", "--porcelain", "--untracked-files=no")
    if code != 0:
        return False, f"skipped: {out[:120]}"
    if out:
        # Someone is working in here. Never clobber that to ship a news bot.
        n = len(out.splitlines())
        return False, f"skipped: {n} local modification(s)"

    _touch_stamp()

    code, out = _git("fetch", "--quiet", remote, branch, timeout=120)
    if code != 0:
        return False, f"fetch failed: {out[:160]}"

    before = current_revision()
    code, target = _git("rev-parse", "--short", f"{remote}/{branch}")
    if code != 0:
        return False, f"cannot resolve {remote}/{branch}: {target[:120]}"
    if before and before == target:
        return False, ""          # already current, and the common case

    code, out = _git("merge", "--ff-only", f"{remote}/{branch}", timeout=120)
    if code != 0:
        # Diverged. Refusing is correct: the alternative is discarding whatever
        # is here, and nothing about a news bot justifies that.
        return False, f"not fast-forwardable, left alone: {out[:160]}"

    after = current_revision()
    detail = f"updated {before or '?'} -> {after}"

    if _requirements_changed(before, after):
        ok, msg = _install_requirements()
        detail += f"; {msg}"
        if not ok:
            logger.error("dependency install failed after update: %s", msg)
            return True, detail + " (DEPENDENCY INSTALL FAILED)"

    logger.info("self-update: %s", detail)
    return True, detail


def preflight() -> tuple[list[str], list[str]]:
    """
    Can this install actually keep itself up to date? Returns (problems, notes).

    Called by `check-ready`, because every failure mode here is silent at
    runtime: the bot keeps polling and posting perfectly on whatever code it has
    while the update quietly fails on every run. The one that motivated this is
    a hardened systemd unit -- ProtectSystem=strict with the project directory
    left out of ReadWritePaths makes the checkout read-only, so `git merge`
    fails forever and nothing about the digest looks wrong.
    """
    problems: list[str] = []
    notes: list[str] = []

    if not _env_bool("AUTO_UPDATE", True):
        return [], ["auto-update is disabled (AUTO_UPDATE=false)"]

    if not os.path.isdir(os.path.join(paths.PROJECT_ROOT, ".git")):
        return [], ["not a git checkout, so auto-update is inactive; "
                    "install with `git clone` if you want upstream fixes"]

    code, out = _git("--version")
    if code != 0:
        problems.append(f"AUTO_UPDATE is on but git is unusable: {out[:120]}")
        return problems, notes

    # Writable checkout. os.access is unreliable for this on Windows, and a
    # real write is what git will attempt anyway.
    probe = os.path.join(paths.PROJECT_ROOT, ".selfupdate-write-probe")
    try:
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("probe")
        os.remove(probe)
    except OSError as exc:
        problems.append(
            f"the project directory is not writable ({exc.__class__.__name__}), so "
            f"auto-update will fail on every run while the bot otherwise looks "
            f"healthy. On systemd, add {paths.PROJECT_ROOT} to ReadWritePaths."
        )

    remote = _env("AUTO_UPDATE_REMOTE", "origin")
    branch = _env("AUTO_UPDATE_BRANCH", "main")
    code, out = _git("symbolic-ref", "--quiet", "--short", "HEAD")
    if code != 0 or not out:
        notes.append("detached HEAD: pinned to a commit, auto-update will not move it")
    elif out != branch:
        notes.append(f"on branch {out}, tracking {branch}: auto-update will not run")

    code, out = _git("ls-remote", "--exit-code", remote, f"refs/heads/{branch}", timeout=45)
    if code != 0:
        problems.append(f"cannot reach {remote}/{branch}: {out[:140]}")
    else:
        notes.append(f"tracking {remote}/{branch}, currently at {current_revision()}")

    return problems, notes
