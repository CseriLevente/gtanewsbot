"""
Tests for the GitHub Pages deploy helper.

Only the pure logic is covered here. The rest of the script is git plumbing
whose failure modes are network- and credential-shaped, and a test that pushed
to a real remote would be worse than no test at all.

public_url() is worth pinning because it is derived rather than configured:
a fork must publish to its own URL, and the digest embeds whatever this returns.
"""
from __future__ import annotations

import pytest

deploy_pages = pytest.importorskip("tools.deploy_pages")


@pytest.mark.parametrize(("remote", "expected"), [
    ("https://github.com/CseriLevente/gtanewsbot.git",
     "https://cserilevente.github.io/gtanewsbot/"),
    ("https://github.com/CseriLevente/gtanewsbot",
     "https://cserilevente.github.io/gtanewsbot/"),
    ("git@github.com:CseriLevente/gtanewsbot.git",
     "https://cserilevente.github.io/gtanewsbot/"),
    # The owner is lowercased (github.io hosts are case-insensitive and GitHub
    # serves the lowercase form) but the repo path keeps its case, because the
    # path after the host IS case-sensitive.
    ("https://github.com/SomeOwner/MixedCase.git",
     "https://someowner.github.io/MixedCase/"),
])
def test_public_url_is_derived_from_the_remote(monkeypatch, remote, expected):
    monkeypatch.setattr(deploy_pages, "git", lambda *a, **k: remote)
    assert deploy_pages.public_url() == expected


def test_public_url_is_none_for_a_non_github_remote(monkeypatch):
    monkeypatch.setattr(deploy_pages, "git", lambda *a, **k: "https://gitlab.com/x/y.git")
    assert deploy_pages.public_url() is None


def test_public_url_survives_a_missing_remote(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no such remote")
    monkeypatch.setattr(deploy_pages, "git", boom)
    assert deploy_pages.public_url() is None
