"""
Self-update tests, against real git repositories rather than mocks.

This is the one feature that makes a deployment execute code it did not have a
moment ago, so its guards are the whole product. Mocking `git` would test the
mock; every test here builds an actual upstream repo and clone in tmp_path.

The invariant under all of them: the update either fast-forwards cleanly or does
nothing at all. It must never merge, rebase, discard a commit, or overwrite
someone's local edits.
"""
from __future__ import annotations

import os
import subprocess

import pytest

from src import paths, selfupdate


def git(cwd, *args, check=True):
    r = subprocess.run(
        ("git", "-c", "user.name=t", "-c", "user.email=t@e", "-c", "commit.gpgsign=false")
        + args,
        cwd=str(cwd), capture_output=True, text=True,
    )
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr or r.stdout}")
    return r.stdout.strip()


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """An upstream repo and a clone of it, with the clone as PROJECT_ROOT."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "--quiet", "--initial-branch=main")
    (upstream / "requirements.txt").write_text("httpx==0.27.0\n", encoding="utf-8")
    (upstream / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
    git(upstream, "add", "-A")
    git(upstream, "commit", "--quiet", "-m", "initial")

    clone = tmp_path / "clone"
    git(tmp_path, "clone", "--quiet", str(upstream), str(clone))

    monkeypatch.setattr(paths, "PROJECT_ROOT", str(clone))
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(tmp_path / "state"))
    monkeypatch.setenv("AUTO_UPDATE", "true")
    monkeypatch.setenv("AUTO_UPDATE_INTERVAL_S", "0")   # never rate-limited here
    monkeypatch.setenv("AUTO_UPDATE_BRANCH", "main")
    return upstream, clone


def push_upstream(upstream, text="VERSION = 2\n", also=None):
    (upstream / "app.py").write_text(text, encoding="utf-8")
    if also:
        for name, content in also.items():
            (upstream / name).write_text(content, encoding="utf-8")
    git(upstream, "add", "-A")
    git(upstream, "commit", "--quiet", "-m", "upstream change")


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------

def test_it_fast_forwards_to_upstream(repo):
    upstream, clone = repo
    push_upstream(upstream)
    updated, detail = selfupdate.check_and_update()
    assert updated is True, detail
    assert "updated" in detail
    assert (clone / "app.py").read_text(encoding="utf-8") == "VERSION = 2\n"


def test_already_current_is_a_silent_no_op(repo):
    updated, detail = selfupdate.check_and_update()
    assert updated is False
    assert detail == "", "a no-op must not add noise to every run's log"


# ---------------------------------------------------------------------------
# The guards
# ---------------------------------------------------------------------------

def test_disabled_by_config_does_nothing(repo, monkeypatch):
    upstream, clone = repo
    push_upstream(upstream)
    monkeypatch.setenv("AUTO_UPDATE", "false")
    updated, _ = selfupdate.check_and_update()
    assert updated is False
    assert (clone / "app.py").read_text(encoding="utf-8") == "VERSION = 1\n"


def test_local_modifications_are_never_clobbered(repo):
    """A developer's working tree outranks shipping a news bot."""
    upstream, clone = repo
    push_upstream(upstream)
    (clone / "app.py").write_text("VERSION = 'my local work'\n", encoding="utf-8")

    updated, detail = selfupdate.check_and_update()
    assert updated is False
    assert "local modification" in detail
    assert (clone / "app.py").read_text(encoding="utf-8") == "VERSION = 'my local work'\n"


def test_untracked_files_do_not_block_an_update(repo):
    """A stray log or .env must not freeze a deployment forever."""
    upstream, clone = repo
    push_upstream(upstream)
    (clone / "notes.txt").write_text("scratch\n", encoding="utf-8")
    updated, detail = selfupdate.check_and_update()
    assert updated is True, detail


def test_a_diverged_branch_is_left_alone(repo):
    """
    --ff-only is the entire policy. With a local commit that upstream does not
    have, the only ways "forward" are a merge or discarding work; both are
    refused.
    """
    upstream, clone = repo
    push_upstream(upstream)
    (clone / "app.py").write_text("VERSION = 'local commit'\n", encoding="utf-8")
    git(clone, "add", "-A")
    git(clone, "commit", "--quiet", "-m", "local")
    local_head = git(clone, "rev-parse", "HEAD")

    updated, detail = selfupdate.check_and_update()
    assert updated is False
    assert "fast-forward" in detail
    assert git(clone, "rev-parse", "HEAD") == local_head, "local history was rewritten"
    assert (clone / "app.py").read_text(encoding="utf-8") == "VERSION = 'local commit'\n"


def test_a_non_checkout_is_skipped_silently(tmp_path, monkeypatch):
    """Installed from a zip, or copied. Nothing to track, and no complaining."""
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setattr(paths, "PROJECT_ROOT", str(plain))
    monkeypatch.setenv("AUTO_UPDATE", "true")
    assert selfupdate.check_and_update() == (False, "")


def test_an_unreachable_remote_reports_but_does_not_raise(repo, monkeypatch):
    upstream, clone = repo
    push_upstream(upstream)
    git(clone, "remote", "set-url", "origin", str(clone / "does-not-exist"))
    updated, detail = selfupdate.check_and_update()
    assert updated is False
    assert "fetch failed" in detail


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def test_requirements_change_is_detected(repo, monkeypatch):
    upstream, clone = repo
    push_upstream(upstream, also={"requirements.txt": "httpx==0.27.0\nnewdep==1.0\n"})

    calls = []
    monkeypatch.setattr(selfupdate, "_install_requirements",
                        lambda: (calls.append(1) or (True, "dependencies updated")))
    updated, detail = selfupdate.check_and_update()
    assert updated is True
    assert calls, "requirements.txt changed but pip was never run"
    assert "dependencies updated" in detail


def test_untouched_requirements_do_not_trigger_pip(repo, monkeypatch):
    upstream, clone = repo
    push_upstream(upstream)               # only app.py changes
    calls = []
    monkeypatch.setattr(selfupdate, "_install_requirements",
                        lambda: (calls.append(1) or (True, "x")))
    selfupdate.check_and_update()
    assert not calls, "pip ran for a change that did not touch requirements.txt"


def test_a_failed_dependency_install_is_reported_loudly(repo, monkeypatch):
    upstream, clone = repo
    push_upstream(upstream, also={"requirements.txt": "httpx==0.27.0\nbroken\n"})
    monkeypatch.setattr(selfupdate, "_install_requirements",
                        lambda: (False, "could not resolve broken"))
    updated, detail = selfupdate.check_and_update()
    assert updated is True, "the code did move, so say so"
    assert "DEPENDENCY INSTALL FAILED" in detail


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_the_interval_suppresses_a_second_check(repo, monkeypatch):
    upstream, clone = repo
    monkeypatch.setenv("AUTO_UPDATE_INTERVAL_S", "3600")
    selfupdate.check_and_update()                 # writes the stamp
    push_upstream(upstream)
    updated, detail = selfupdate.check_and_update()
    assert updated is False
    assert detail == ""
    assert (clone / "app.py").read_text(encoding="utf-8") == "VERSION = 1\n"


def test_an_unwritable_stamp_degrades_to_checking_every_run(repo, monkeypatch):
    """
    One deployment host silently loses scheduled writes. Failing OPEN here is
    the safe direction: a few extra cheap fetches, rather than a deployment
    that never updates again and never says why.
    """
    upstream, clone = repo
    monkeypatch.setenv("AUTO_UPDATE_INTERVAL_S", "3600")
    monkeypatch.setattr(paths, "app_data_dir",
                        lambda: os.path.join(str(clone), "no", "such", "dir"))
    push_upstream(upstream)
    updated, detail = selfupdate.check_and_update()
    assert updated is True, detail


# ---------------------------------------------------------------------------
# Pinning
#
# Verified experimentally before writing this: `git merge --ff-only origin/main`
# from a detached HEAD DOES fast-forward it. So without an explicit branch check,
# pinning a deployment to a known-good commit while main was broken would drag it
# straight back onto the broken commit — the exact opposite of pinning.
# ---------------------------------------------------------------------------

def test_a_detached_head_is_a_pin_and_is_respected(repo):
    upstream, clone = repo
    pinned = git(clone, "rev-parse", "HEAD")
    push_upstream(upstream)
    git(clone, "fetch", "--quiet", "origin", "main")
    git(clone, "checkout", "--quiet", pinned)

    updated, detail = selfupdate.check_and_update()
    assert updated is False
    assert "detached" in detail
    assert git(clone, "rev-parse", "HEAD") == pinned, "the pin was overridden"
    assert (clone / "app.py").read_text(encoding="utf-8") == "VERSION = 1\n"


def test_a_feature_branch_is_not_dragged_onto_main(repo):
    upstream, clone = repo
    push_upstream(upstream)
    git(clone, "checkout", "--quiet", "-b", "experiment")
    head = git(clone, "rev-parse", "HEAD")

    updated, detail = selfupdate.check_and_update()
    assert updated is False
    assert "experiment" in detail
    assert git(clone, "rev-parse", "HEAD") == head


def test_two_installs_on_one_machine_do_not_silence_each_other(tmp_path, monkeypatch):
    """
    The stamp used to be a single fixed filename in the shared state directory,
    so whichever checkout ran first suppressed the other's update check for an
    hour. Found by cloning the repo next to the working copy and watching the
    clone refuse to update.
    """
    state = tmp_path / "state"
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(state))

    monkeypatch.setattr(paths, "PROJECT_ROOT", str(tmp_path / "install-a"))
    a = selfupdate._stamp_path()
    monkeypatch.setattr(paths, "PROJECT_ROOT", str(tmp_path / "install-b"))
    b = selfupdate._stamp_path()

    assert a != b, "both installs share one stamp file"
    assert os.path.dirname(a) == str(state), "the stamp must stay out of the repo"


def test_the_same_install_keeps_the_same_stamp(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(tmp_path / "state"))
    monkeypatch.setattr(paths, "PROJECT_ROOT", str(tmp_path / "install"))
    first = selfupdate._stamp_path()
    monkeypatch.setattr(paths, "PROJECT_ROOT", str(tmp_path / "install") + os.sep)
    assert selfupdate._stamp_path() == first, (
        "a trailing separator produced a different stamp, so the interval reset")
